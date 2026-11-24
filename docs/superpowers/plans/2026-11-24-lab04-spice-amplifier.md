# Lab 04 — SPICE Amplifier Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมดที่ 4 "CE Amplifier (SPICE)" ให้เว็บ Flask เดิม รัน ngspice จริง 3 analysis (`.op`, `.ac`, `.tran`) และแสดงผล DC, Bode และ Transient พร้อมกราฟที่สร้างจากผลจริง

**Architecture:** `spice_engine.py` สร้าง netlist, รัน ngspice ใน temp dir แยกต่อ analysis แล้ว parse ตาราง `wrdata` เป็น dataclass หน่วย SI; `spice_plots.py` วาด PNG ด้วย matplotlib (Agg); `app.py` ตรวจฟอร์มและ dispatch ระหว่าง analytical (เดิม) กับ SPICE (ใหม่); template ฝัง PNG เป็น base64 ไม่ใช้ JavaScript

**Tech Stack:** Python 3.15, Flask 3.1, unittest, ngspice 47 (console build), matplotlib 3.11 (Agg)

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-spice-amplifier-design.md`

## Global Constraints

- Python 3.15.2, Flask `>=3.1,<4`, unittest เท่านั้น (ไม่มี pytest), รันด้วย `.\.venv\Scripts\python.exe`
- ngspice 47 console build อยู่บน PATH; override ได้ด้วย env `NGSPICE_BIN`
- model เริ่มต้น `spice/models/2n3904.lib`; override ได้ด้วย env `SPICE_MODEL_PATH`
- หน่วย SI ภายใน engine ทั้งหมด; แปลง V/mA/µA/µF/mV ที่ `to_display()` เท่านั้น
- netlist เป็น ASCII ล้วน; ห้าม `shell=True`; timeout 20 วินาทีต่อ analysis
- ทุก error คืน HTTP 200 + error box + คงค่าฟอร์ม + ไม่มีผลลัพธ์/กราฟค้าง
- ไม่ใช้ JavaScript; ค่า default ของฟอร์มอยู่ใน `DEFAULT_FORMS` (`app.py`) เท่านั้น
- ห้ามแก้ `dc_bias.py` และห้ามเปลี่ยนพฤติกรรม 3 โหมดเดิม (A1–A5 ต้องคงเดิม)
- โมเดลเป็น placeholder: ห้ามนำผลไปอ้างเป็นค่าของแล็บในรายงาน

## Review Focus

- ผู้ใช้กรอกค่าสุดขั้ว (RE ≈ 0, Vs สูงผิดปกติ) → ต้องได้ `SpiceError` ที่อ่านรู้เรื่อง หรือผลที่ถูกต้อง ไม่ใช่ traceback/HTTP 500
- ngspice หายจาก PATH ระหว่างรัน → error box "ไม่พบ ngspice" และฟอร์มยังคงค่าเดิม
- ฟอร์มมี comma / ช่องว่าง / เลขยกกำลัง (`1e3`) → แปลงถูกหรือ error ชัด โดยไม่มีอะไรหลุดเข้า netlist
- path ของ model มีช่องว่างหรืออักษรไทย → ยังรันได้ (แก้ด้วยการคัดลอก model เข้า temp dir)
- ผลลัพธ์มีจุดเดียวหรือศูนย์จุด → parser/plot ต้องไม่ crash และไม่สร้างกราฟเปล่าโดยไม่แจ้ง

---

### Task 1: Model file และ netlist builders

**Files:**
- Create: `spice/models/2n3904.lib`
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `AmpInputs` (frozen dataclass: `vcc, r1, r2, rc, re, rl, cin, cout, vs_peak, freq, beta_ref, vbe_ref` — SI ทั้งหมด)
- Produces: `MODEL_PATH: pathlib.Path`, `build_op_netlist(inputs) -> str`, `build_ac_netlist(inputs) -> str`, `build_tran_netlist(inputs) -> str`
- Netlist อ้าง model ด้วย `.include model.lib` เสมอ (ไฟล์จริงถูกคัดลอกเข้า temp dir ใน Task 2)

- [ ] **Step 1: เขียนเทสต์ netlist ที่ยังไม่ผ่าน**

```python
class NetlistTests(unittest.TestCase):
    def setUp(self):
        self.inputs = AmpInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3,
                                rl=10e3, cin=10e-6, cout=10e-6,
                                vs_peak=10e-3, freq=1e3,
                                beta_ref=100.0, vbe_ref=0.70)

    def test_op_deck_has_components_and_wrdata(self):
        deck = build_op_netlist(self.inputs)
        self.assertIn(".include model.lib", deck)
        self.assertIn("VCC vcc 0 DC 12", deck)
        self.assertIn("R1 vcc vb 100000", deck)
        self.assertIn("RC vcc vc 2200", deck)
        self.assertIn("RE ve 0 1000", deck)
        self.assertIn("Q1 vc vb ve Q2N3904", deck)
        self.assertIn("set wr_singlescale", deck)
        self.assertIn("wrdata out.txt", deck)
        self.assertTrue(deck.isascii())
        self.assertTrue(deck.rstrip().endswith(".end"))

    def test_ac_deck_sweeps_and_saves_both_nodes(self):
        deck = build_ac_netlist(self.inputs)
        self.assertIn("ac dec 20 10 1meg", deck)
        self.assertIn("wrdata out.txt v(out) v(in)", deck)

    def test_tran_deck_uses_five_periods(self):
        deck = build_tran_netlist(self.inputs)
        self.assertIn("tran 2.5e-06 0.005", deck)
        self.assertIn("wrdata out.txt v(in) v(out)", deck)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL — `ImportError: cannot import name 'AmpInputs'`

- [ ] **Step 3: สร้าง model file และ implement**

`spice/models/2n3904.lib` — หัวไฟล์ต้องมีบรรทัดเตือนว่าเป็น placeholder (ASCII):

```
* 2N3904 placeholder model card (ON Semiconductor style)
* NOT the Lab 04 fixture: replace this file with the instructor's model.
.model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)
```

`spice_engine.py` — ตัวเลขทุกตัวจัดรูปแบบด้วย `f"{value:.12g}"`; ชุดเวกเตอร์ต่อ analysis:

- op: `v(vb) v(ve) v(vc) v(vcc) @q1[ic] @q1[ib]`
- ac: `v(out) v(in)`
- tran: `v(in) v(out)`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS 3 tests

- [ ] **Step 5: Commit**

```bash
git add spice/models/2n3904.lib spice_engine.py tests/test_spice_engine.py
git commit -m "feat: build ngspice netlists for CE amplifier"
```

---

### Task 2: Runner, timeout และ error mapping

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `SpiceError(message: str)` มี attribute `.message`
- Produces: `run_netlist(netlist: str, tag: str, timeout_s: float = 20.0) -> tuple[str, str]` คืน `(table_text, engine_version)`; `engine_version` คือเลขรุ่น เช่น `"47"` ที่อ่านจากบรรทัด `** ngspice-47 : ...` ใน stdout
- ใช้ `NGSPICE_BIN` (default `"ngspice"`), `SPICE_MODEL_PATH` (default `MODEL_PATH`), คัดลอก model เป็น `model.lib` ใน temp dir, ไฟล์ผลคือ `out.txt`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class RunnerTests(unittest.TestCase):
    def test_missing_binary_reports_thai_error(self):
        with mock.patch.dict(os.environ, {"NGSPICE_BIN": "no-such-ngspice-xyz"}):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่พบ ngspice", ctx.exception.message)

    def test_timeout_reports_thai_error(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("ngspice", 20)):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("นานเกินกำหนด", ctx.exception.message)

    def test_nonzero_exit_includes_stderr_tail(self):
        fake = mock.Mock(returncode=1, stdout="", stderr="Error: singular matrix")
        with mock.patch("spice_engine.subprocess.run", return_value=fake):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่สำเร็จ", ctx.exception.message)
        self.assertIn("singular matrix", ctx.exception.message)

    def test_missing_output_file_is_empty_error(self):
        fake = mock.Mock(returncode=0, stdout="** ngspice-47 : Circuit level simulation program", stderr="")
        with mock.patch("spice_engine.subprocess.run", return_value=fake):
            with self.assertRaises(SpiceError) as ctx:
                run_netlist("* t\n.end\n", "op")
        self.assertIn("ไม่คืนผลลัพธ์", ctx.exception.message)

    def test_success_returns_table_and_version(self):
        def fake_run(cmd, **kwargs):
            Path(kwargs["cwd"], "out.txt").write_text("time v(in)\n0 0\n", encoding="ascii")
            return mock.Mock(returncode=0,
                             stdout="** ngspice-47 : Circuit level simulation program",
                             stderr="")
        with mock.patch("spice_engine.subprocess.run", side_effect=fake_run):
            table, version = run_netlist("* t\n.end\n", "op")
        self.assertIn("time v(in)", table)
        self.assertEqual(version, "47")
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL — `NameError: name 'run_netlist' is not defined`

- [ ] **Step 3: Implement `run_netlist`**

ใช้ `tempfile.TemporaryDirectory()`, เขียน `deck.cir` (ASCII), คัดลอก model เป็น `model.lib`, เรียก
`subprocess.run([bin, "-b", "deck.cir", "-o", "run.log"], cwd=tmp, capture_output=True, text=True, timeout=timeout_s)`
แล้ว map `FileNotFoundError` / `TimeoutExpired` / `returncode != 0` / ไฟล์ `out.txt` ว่างหรือไม่มี เป็น `SpiceError` ตามตาราง §8 ของ spec

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS 8 tests

- [ ] **Step 5: Commit**

```bash
git add spice_engine.py tests/test_spice_engine.py
git commit -m "feat: run ngspice in isolated temp dir with error mapping"
```

---

### Task 3: Parsers ของทั้งสาม analysis

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `OpPoint(vb, ve, vc, vce, ic, ib, region)` — `region` มาจาก `dc_bias.classify_region(vc - ve)`
- Produces: `AcSweep(freq, gain_db, phase_deg, midband_gain_db, gain_at_1khz_db)` — tuple ของ float, `phase_deg` ถูก unwrap ให้ต่อเนื่อง, gain อ้าง `v(in)` (โหนดก่อน Cin)
- Produces: `Transient(time, vin, vout, vin_pp, vout_pp, inverted)` — `*_pp` คำนวณจากช่วง 1 คาบสุดท้าย, `inverted` = สหสัมพันธ์ของ `vin`/`vout` (หลังลบค่าเฉลี่ย) เป็นลบ
- Produces: `parse_op(table) -> OpPoint`, `parse_ac(table) -> AcSweep`, `parse_tran(table, freq) -> Transient` (`freq` ใช้กำหนดความยาว 1 คาบสุดท้าย)
- รูปแบบจริงของ `wrdata` (ยืนยันด้วย spike แล้ว): บรรทัดแรกเป็นชื่อคอลัมน์, op มีคอลัมน์ scale เกินมา 1 คอลัมน์, AC เขียนเวกเตอร์เชิงซ้อนเป็น 2 คอลัมน์ชื่อซ้ำ (real, imag)

- [ ] **Step 1: เขียนเทสต์ด้วยตารางจริงจาก spike**

```python
OP_TABLE = """ vcc             v(vb)           v(ve)           v(vc)           v(vcc)          @q1[ic]         @q1[ib]
 1.20000000e+01  2.00367450e+00  1.33287974e+00  9.08721626e+00  1.20000000e+01  1.32403477e-03  8.88736584e-06
"""

AC_TABLE = """ frequency       v(out)          v(out)          v(in)           v(in)
 1.00000000e+01 -1.68825586e+00 -3.90396170e-01  1.00000000e+00  0.00000000e+00
 1.00000000e+03 -1.75560000e+00 -2.00000000e-02  1.00000000e+00  0.00000000e+00
"""

TRAN_TABLE = """ time            v(in)           v(out)
 0.00000000e+00  0.00000000e+00  0.00000000e+00
 2.50000000e-07  1.57079632e-03 -4.66643146e-03
"""

class ParserTests(unittest.TestCase):
    def test_op_reads_node_voltages_and_device_currents(self):
        op = parse_op(OP_TABLE)
        self.assertAlmostEqual(op.vb, 2.00367450, places=6)
        self.assertAlmostEqual(op.vc, 9.08721626, places=6)
        self.assertAlmostEqual(op.vce, 9.08721626 - 1.33287974, places=6)
        self.assertAlmostEqual(op.ic, 1.32403477e-03, places=9)
        self.assertEqual(op.region, "Forward Active")

    def test_ac_pairs_real_and_imag_columns(self):
        ac = parse_ac(AC_TABLE)
        self.assertEqual(len(ac.freq), 2)
        self.assertAlmostEqual(ac.freq[0], 10.0)
        self.assertAlmostEqual(ac.gain_db[0], 4.7747, places=3)
        self.assertAlmostEqual(abs(ac.phase_deg[0]), 166.98, places=1)

    def test_tran_computes_peak_to_peak_and_inversion(self):
        tr = parse_tran(TRAN_TABLE, 1e3)
        self.assertEqual(len(tr.time), 2)
        self.assertAlmostEqual(tr.vin_pp, 1.57079632e-03, places=9)
        self.assertTrue(tr.inverted)

    def test_malformed_table_raises_spice_error(self):
        with self.assertRaises(SpiceError) as ctx:
            parse_ac("garbage\n")
        self.assertIn("อ่านผลลัพธ์", ctx.exception.message)

    def test_header_only_table_is_rejected(self):
        with self.assertRaises(SpiceError):
            parse_tran(" time v(in) v(out)\n")
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL — `NameError: name 'parse_op' is not defined`

- [ ] **Step 3: Implement parsers**

- ตรวจหัวตารางให้ตรงกับที่ netlist ขอ; ไม่ตรง → `SpiceError("อ่านผลลัพธ์จาก ngspice ไม่ได้")`
- op: ข้ามคอลัมน์แรก (scale), จับคู่ชื่อที่เหลือกับค่าตามลำดับ; `vce = vc - ve`
- ac: ชื่อที่ซ้ำติดกัน = (real, imag); `gain_db = 20*log10(hypot(re, im))` หลังหารด้วยขนาด `v(in)`; unwrap phase ด้วยการบวก/ลบ 360 เมื่อกระโดดเกิน 180°
- tran: อ่าน 3 คอลัมน์; หาช่วง 1 คาบสุดท้าย (`t >= t[-1] - 1/freq`) โดยใช้ `freq` จาก `AmpInputs` ที่ส่งเข้ามา — ถ้า parser ไม่รับ `freq` ให้ใช้ `Transient` จากตารางเต็มและคำนวณ pp จาก 20% สุดท้ายของช่วงเวลาแทน (เลือกวิธีใดวิธีหนึ่งแล้วใช้ให้สอดคล้องกับเทสต์ Task 4)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS 13 tests

- [ ] **Step 5: Commit**

```bash
git add spice_engine.py tests/test_spice_engine.py
git commit -m "feat: parse ngspice op, ac and tran tables"
```

---

### Task 4: `analyze()` และ integration tests กับ ngspice จริง

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `analyze(inputs: AmpInputs) -> SpiceRun` (ยังไม่มี PNG; `ac_png`/`tran_png` เติมใน Task 5)
- Produces: `SpiceRun(op, ac, tran, ac_png, tran_png, engine_version)`
- ใช้ `SPICE_MODEL_PATH` ถ้าตั้งไว้ (คัดลอกเข้า temp dir เป็น `model.lib`)

- [ ] **Step 1: เขียน integration tests (ข้ามถ้าไม่มี ngspice)**

```python
HAS_NGSPICE = shutil.which(os.environ.get("NGSPICE_BIN", "ngspice")) is not None

@unittest.skipUnless(HAS_NGSPICE, "ngspice not installed")
class AnalyzeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = AmpInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3,
                                rl=10e3, cin=10e-6, cout=10e-6,
                                vs_peak=10e-3, freq=1e3,
                                beta_ref=100.0, vbe_ref=0.70)

    def test_baseline_matches_measured_values(self):
        run = analyze(self.inputs)
        self.assertAlmostEqual(run.op.vb, 2.0037, delta=0.01)
        self.assertAlmostEqual(run.op.ve, 1.3329, delta=0.01)
        self.assertAlmostEqual(run.op.vc, 9.0872, delta=0.02)
        self.assertAlmostEqual(run.op.ic, 1.3240e-3, delta=1e-5)
        self.assertEqual(run.op.region, "Forward Active")
        self.assertEqual(len(run.ac.freq), 101)
        self.assertAlmostEqual(run.ac.midband_gain_db, 4.890, delta=0.05)
        self.assertLess(abs(abs(run.ac.phase_deg[-1]) - 180.0), 5.0)
        self.assertEqual(len(run.tran.time), 2008)
        self.assertAlmostEqual(run.tran.vin_pp, 0.0200, delta=1e-4)
        self.assertAlmostEqual(run.tran.vout_pp, 0.0351, delta=5e-4)
        self.assertTrue(run.tran.inverted)
        self.assertEqual(run.engine_version, "47")

    def test_larger_re_lowers_collector_current(self):
        higher = analyze(replace(self.inputs, re=2e3))
        self.assertLess(higher.op.ic, 1.3240e-3)

    def test_doubling_source_doubles_output_swing(self):
        louder = analyze(replace(self.inputs, vs_peak=20e-3))
        self.assertAlmostEqual(louder.tran.vout_pp, 0.0702, delta=2e-3)

    def test_model_path_with_thai_and_space_still_runs(self):
        with tempfile.TemporaryDirectory(prefix="โมเดล ทดสอบ ") as tmp:
            target = Path(tmp, "โมเดล 2n3904.lib")
            shutil.copy(MODEL_PATH, target)
            with mock.patch.dict(os.environ, {"SPICE_MODEL_PATH": str(target)}):
                run = analyze(self.inputs)
        self.assertEqual(run.op.region, "Forward Active")

    def test_extreme_values_never_raise_unexpected_exception(self):
        for bad in (replace(self.inputs, re=1e-3), replace(self.inputs, vs_peak=50.0)):
            try:
                analyze(bad)
            except SpiceError:
                pass
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL — `NameError: name 'analyze' is not defined`

- [ ] **Step 3: Implement `analyze`**

สร้าง deck ทั้งสาม, เรียก `run_netlist` ตามลำดับ op → ac → tran, parse, รวมเป็น `SpiceRun` โดย `ac_png`/`tran_png` ยังเป็น `b""`; ถ้า analysis ใดล้ม ให้ปล่อย `SpiceError` ของตัวนั้นขึ้นไป (all-or-nothing)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS 18 tests (integration 5 ตัวรันจริงกับ ngspice 47)

- [ ] **Step 5: Commit**

```bash
git add spice_engine.py tests/test_spice_engine.py
git commit -m "feat: orchestrate three ngspice analyses for the CE amplifier"
```

---

### Task 5: กราฟ PNG ด้วย matplotlib

**Files:**
- Create: `spice_plots.py`
- Modify: `spice_engine.py` (เติม `ac_png`/`tran_png` ใน `analyze`)
- Modify: `requirements.txt`
- Test: `tests/test_spice_plots.py`

**Interfaces:**
- Produces: `ac_png(ac: AcSweep) -> bytes` (2 แผง: magnitude dB, phase °, แกน x log)
- Produces: `tran_png(tran: Transient) -> bytes` (Vin/Vout เทียบเวลา)
- ใช้ backend `Agg` เท่านั้น ห้ามเปิดหน้าต่าง

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class PlotTests(unittest.TestCase):
    def test_ac_plot_returns_png_bytes(self):
        ac = AcSweep(freq=(10.0, 100.0, 1000.0), gain_db=(4.7, 4.8, 4.9),
                     phase_deg=(-167.0, -179.0, -179.9),
                     midband_gain_db=4.9, gain_at_1khz_db=4.9)
        png = ac_png(ac)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertGreater(len(png), 3000)

    def test_single_point_still_renders(self):
        ac = AcSweep(freq=(1000.0,), gain_db=(4.9,), phase_deg=(-180.0,),
                     midband_gain_db=4.9, gain_at_1khz_db=4.9)
        self.assertTrue(ac_png(ac).startswith(b"\x89PNG"))

    def test_tran_plot_returns_png_bytes(self):
        tr = Transient(time=(0.0, 1e-3, 2e-3), vin=(0.0, 0.01, 0.0),
                       vout=(0.0, -0.0176, 0.0),
                       vin_pp=0.02, vout_pp=0.0351, inverted=True)
        png = tran_png(tr)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertGreater(len(png), 3000)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_plots.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spice_plots'`

- [ ] **Step 3: เพิ่ม dependency และ implement**

`requirements.txt` เพิ่มบรรทัด `matplotlib>=3.11,<4` แล้วติดตั้ง:
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

`spice_plots.py` ใช้ `matplotlib.figure.Figure` + `FigureCanvasAgg` + `BytesIO`; ตั้ง `figure.dpi = 110`, `tight_layout()`; ข้อความในกราฟเป็นอังกฤษ (กันปัญหาฟอนต์ไทย)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_plots.py" -v`
Expected: PASS 3 tests

- [ ] **Step 5: Commit**

```bash
git add requirements.txt spice_plots.py spice_engine.py tests/test_spice_plots.py
git commit -m "feat: render Bode and transient plots as PNG"
```

---

### Task 6: ต่อโหมด amp เข้า `app.py`

**Files:**
- Modify: `app.py`
- Modify: `spice_engine.py` (เพิ่ม `to_display`)
- Test: `tests/test_web.py`

**Interfaces:**
- Produces: `MODE_LABELS["amp"] = "CE Amplifier (SPICE)"`
- Produces: `DEFAULT_FORMS["amp"]` (string ทั้งหมด):
  `{"vcc": "12", "vbe": "0.70", "rc": "2.2", "r1": "100", "r2": "22", "re": "1", "rl": "10", "cin": "10", "cout": "10", "vs_mv": "10", "freq": "1000", "beta": "100", "r_unit": "k"}`
- Produces: `to_display(run: SpiceRun) -> dict` คืน key `engine_version`, `op`, `ac`, `tran` (ยังไม่มี analytical/deltas)
  - `op`: `vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ua, region`
  - `ac`: `midband_gain_db, gain_1khz_db, points, png_uri`
  - `tran`: `vin_pp_mv, vout_pp_mv, inverted, points, png_uri`
  - `png_uri` = `"data:image/png;base64," + base64.b64encode(png).decode("ascii")`
- `app.py` import แบบ `import spice_engine` (เพื่อให้เทสต์ monkeypatch ได้) และเพิ่ม `_parse_amp_form(form) -> spice_engine.AmpInputs`
- ข้อความ validation ที่ต้องตรงเป๊ะ: `"ค่า CIN ต้องมากกว่า 0 µF"`, `"ค่า COUT ต้องมากกว่า 0 µF"`, `"ค่า f ต้องมากกว่า 0 Hz"`, `"ค่า Vs ต้องมากกว่า 0 V"`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

ไฟล์เทสต์ต้อง `import app as app_module`, `import spice_engine` และ `from dataclasses import replace`; ใส่โค้ดทั้งหมดนี้ใน `tests/test_web.py` (ต่อจาก class เดิม) — `VALID_AMP_FORM` มาจาก `dict(app_module.DEFAULT_FORMS["amp"], mode="amp")` และ `FAKE_RUN` คือ fixture จำลองที่สร้างจาก dataclass จริง (PNG เป็น bytes ปลอมเพื่อไม่ให้รัน ngspice ในเทสต์ web):

```python
FAKE_RUN = spice_engine.SpiceRun(
    op=spice_engine.OpPoint(vb=2.0, ve=1.3, vc=9.1, vce=7.8, ic=1.3e-3,
                            ib=9e-6, region="Forward Active"),
    ac=spice_engine.AcSweep(freq=(1000.0,), gain_db=(4.89,), phase_deg=(-179.9,),
                            midband_gain_db=4.89, gain_at_1khz_db=4.89),
    tran=spice_engine.Transient(time=(0.0,), vin=(0.01,), vout=(-0.0176,),
                                vin_pp=0.02, vout_pp=0.035, inverted=True),
    ac_png=b"\x89PNG-fake", tran_png=b"\x89PNG-fake", engine_version="47")

VALID_AMP_FORM = dict(app_module.DEFAULT_FORMS["amp"], mode="amp")


class AmpModeTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.create_app().test_client()

    def test_get_amp_shows_spice_form_with_lab_defaults(self):
        html = self.client.get("/?mode=amp").get_data(as_text=True)
        self.assertIn('name="rl"', html)
        self.assertIn('name="vs_mv"', html)
        self.assertIn('value="10"', html)
        self.assertIn("CE Amplifier (SPICE)", html)

    def test_missing_value_keeps_form_and_reports_error(self):
        resp = self.client.post("/calculate", data={"mode": "amp", "vcc": "12", "r_unit": "k"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ไม่สามารถคำนวณได้", html)
        self.assertNotIn("data:image/png", html)

    def test_zero_capacitance_is_rejected(self):
        data = dict(VALID_AMP_FORM, cin="0")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("ค่า CIN ต้องมากกว่า 0 µF", html)

    def test_comma_and_exponent_inputs_are_accepted(self):
        inputs = app_module._parse_amp_form(dict(VALID_AMP_FORM, vcc="1,2", freq="1e3"))
        self.assertAlmostEqual(inputs.vcc, 12.0)
        self.assertAlmostEqual(inputs.freq, 1000.0)

    def test_engine_failure_shows_error_and_no_plots(self):
        with mock.patch("spice_engine.analyze",
                        side_effect=spice_engine.SpiceError("ไม่พบ ngspice ในเครื่องนี้")):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ไม่พบ ngspice", html)
        self.assertNotIn("data:image/png", html)

    def test_success_renders_both_labels_and_plots(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ngspice 47", html)
        self.assertIn("Analytical", html)
        self.assertEqual(html.count("data:image/png"), 2)

    def test_large_gap_emits_soft_warning(self):
        far = replace(FAKE_RUN, op=replace(FAKE_RUN.op, ic=2.5e-3))
        with mock.patch("spice_engine.analyze", return_value=far):
            html = self.client.post("/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("ต่างจากการคำนวณมือเกิน 15%", html)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `KeyError: 'amp'` / `AttributeError: module 'app' has no attribute '_parse_amp_form'`

- [ ] **Step 3: Implement**

- เพิ่ม `MODE_LABELS["amp"]`, `DEFAULT_FORMS["amp"]`
- `_parse_amp_form`: แปลง `r_unit` เป็น scale 1000/1 สำหรับ `r1, r2, rc, re, rl`; `cin`/`cout` ×1e-6; `vs_mv` ×1e-3; `freq`, `beta`, `vbe` ตรงตัว
- ตรวจด้วย `validate_common(vcc, beta, vbe)` + `validate_resistors(R1=..., R2=..., RC=..., RE=..., RL=...)` + เงื่อนไข cap/freq/vs ข้างต้น
- ใน `POST /calculate` เพิ่มสาขา `elif mode == "amp"`: parse → `spice_engine.analyze` → `to_display` → คำนวณ analytical ด้วย `calculate_divider(vcc, r1, r2, rc, re, beta, vbe)` → เติม `analytical` และ `deltas` (`delta_pct` ของ vb, ve, vc, vce, ic; ถ้าค่าอ้างอิงเป็น 0 ให้ใช้ `None`)
- จับ `spice_engine.SpiceError` แล้ว `render_page(mode, form, errors=[exc.message])` (ไม่ส่ง `result`)
- เก็บ `warnings` จาก analytical เหมือนโหมด divider; เพิ่มข้อความ `"ต่างจากการคำนวณมือเกิน 15% (model BF ≠ β ในฟอร์ม)"` ลงใน `warnings` เมื่อ `deltas` ใดมี `abs(delta_pct) > 15` (soft warning — ไม่ใช่ error และยังแสดงผลครบ)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: PASS ทุกตัว (เดิม 23 + ใหม่ 7)

- [ ] **Step 5: Commit**

```bash
git add app.py spice_engine.py tests/test_web.py
git commit -m "feat: add CE amplifier SPICE mode to the web app"
```

---

### Task 7: ฟอร์มและหน้าผลลัพธ์ใน template

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Test: `tests/test_web.py`

**Interfaces:**
- ฟอร์ม amp ใช้ชื่อ field ตาม `DEFAULT_FORMS["amp"]`; ไม่มี literal ค่า default ใน template (อ่านจาก `form`)
- ผลลัพธ์อ่านจาก `result.op`, `result.ac`, `result.tran`, `result.analytical`, `result.deltas`, `result.engine_version`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class AmpTemplateTests(unittest.TestCase):
    def test_amp_page_has_all_fields_and_no_script(self):
        html = app_module.create_app().test_client().get("/?mode=amp").get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "vs_mv", "freq"):
            self.assertIn(f'name="{name}"', html)
        self.assertNotIn("<script", html)

    def test_result_page_shows_three_cards_with_badges(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertIn("DC Operating Point", html)
        self.assertIn("AC Bode", html)
        self.assertIn("Transient", html)
        self.assertIn("ngspice 47", html)
        self.assertIn("dc_bias.py", html)
        self.assertEqual(html.count("<img"), 2)

    def test_result_shows_region_for_both_sources(self):
        with mock.patch("spice_engine.analyze", return_value=FAKE_RUN):
            html = app_module.create_app().test_client().post(
                "/calculate", data=VALID_AMP_FORM).get_data(as_text=True)
        self.assertGreaterEqual(html.count("Forward Active"), 2)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — ไม่พบ `name="rl"` / ไม่พบ "AC Bode"

- [ ] **Step 3: Implement template + CSS**

- เพิ่มสาขา `{% if mode == 'amp' %}` ในฟอร์ม พร้อมช่องและหน่วยตาม §11 ของ spec
- เพิ่มการ์ดผล 3 ใบ (DC + ตารางเทียบ + AC + Transient) และป้าย "ngspice {{ result.engine_version }}" / "dc_bias.py (คำนวณมือ)"
- `static/style.css`: `.plots img { width: 100%; height: auto; }`, `.compare table` แบบอ่านง่าย, `.badge` และ breakpoint ให้เหลือคอลัมน์เดียวที่ ≤ 640px

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS ทั้งหมด (≥ 85 tests) และไม่มี regression ของ 3 โหมดเดิม

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css tests/test_web.py
git commit -m "feat: render SPICE results and comparison tables"
```

---

### Task 8: Browser acceptance B1–B8

**Files:**
- Create: `docs/screenshots/lab04-desktop.png`
- Create: `docs/screenshots/lab04-mobile.png`

**Interfaces:**
- ต้องมี Flask รันที่ `http://127.0.0.1:5000/` (สตาร์ทใหม่หลังแก้โค้ด)

- [ ] **Step 1: รันเทสต์ทั้งหมดก่อนเริ่มตรวจ**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK, ไม่มี FAIL/ERROR

- [ ] **Step 2: ตรวจ B1–B7 ในเบราว์เซอร์**

- B1: สลับ 3 โหมดเดิม กด Calculate — ค่า A1 Divider ต้องได้ IC 1.230 mA, VCE 8.052 V
- B2: โหมด amp กด Calculate — การ์ด DC แสดง VB/VE/VC/VCE/IC/Region
- B3: เปลี่ยน RE เป็น `2` → IC ลดลงและกราฟ/ตัวเลขเปลี่ยนจริง
- B4: ตรวจกราฟ Bode มี magnitude + phase และจุดที่ 1 kHz
- B5: ตรวจกราฟ Transient มี Vin/Vout และระบุกลับเฟส
- B6: เปลี่ยน Vs เป็น `20` mV → ค่า pp โตขึ้น ~2 เท่า
- B7: กรอก `vcc=abc` → error box; แล้วรีสตาร์ทเซิร์ฟเวอร์ด้วย `NGSPICE_BIN` ชี้ไฟล์ที่ไม่มี → error "ไม่พบ ngspice" และไม่มีกราฟ

บันทึกผลแต่ละข้อ (ค่าที่อ่านได้จริง) ไว้ใส่ `docs/validation.md` ใน Task 10

- [ ] **Step 3: เก็บ screenshot desktop**

ใช้ browser tool เปิดหน้า ผลลัพธ์โหมด amp แล้ว `browser.screenshot` แบบ `fullPage` บันทึกเป็น `docs/screenshots/lab04-desktop.png`

- [ ] **Step 4: เก็บ screenshot mobile (390px)**

browser tool ไม่มีความสามารถปรับ viewport — สร้างไฟล์ชั่วคราว `mobile-check.html` ที่มี `<iframe src="http://127.0.0.1:5000/?mode=amp" width="390" height="1200">` เปิดในแท็บแล้ว screenshot เฉพาะ iframe (media query ทำงานตามความกว้าง iframe) บันทึกเป็น `docs/screenshots/lab04-mobile.png` แล้วลบไฟล์ชั่วคราว
ถ้าวิธีนี้ให้ผลไม่น่าเชื่อถือ → บันทึก B8 ว่า `NOT RUN (browser tool ไม่มี viewport control)` ห้ามอ้างว่ารันแล้ว

- [ ] **Step 5: Commit**

```bash
git add docs/screenshots
git commit -m "docs: add Lab 04 browser acceptance screenshots"
```

---

### Task 9: Impeccable (critique → polish → audit)

**Files:**
- Modify: `templates/index.html`, `static/style.css` (ตามผล critique)

- [ ] **Step 1: ติดตั้ง Node LTS และ Impeccable**

Run: `winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements`
จากนั้นเปิดเชลล์ใหม่แล้วรัน `npx impeccable install` (เลือก OpenCode + project scope) และโหลด skill `impeccable`

- [ ] **Step 2: ทำ critique → polish → audit**

โหลด skill `impeccable` แล้วทำตามขั้นตอนกับหน้า `/` และ `/?mode=amp` ที่รันจริง ทั้ง desktop และ mobile **ห้ามแตะสมการและห้ามแทนกราฟจริงด้วยภาพ placeholder**

- [ ] **Step 3: ตรวจว่าไม่มีอะไรเสีย**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK ทั้งหมด; เปิดหน้าเว็บซ้ำแล้วกราฟยังมาจากการรันจริง

- [ ] **Step 4: ถ้าติดตั้งไม่ได้**

บันทึกใน `docs/validation.md` ว่า `NOT RUN (ติดตั้ง Impeccable ไม่สำเร็จ: <เหตุผล>)` และทำ audit ด้วยมือ (contrast, spacing, focus state, responsive) แล้ว commit การแก้ที่ได้

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css docs/validation.md
git commit -m "style: polish Lab 04 UI after critique"
```

---

### Task 10: เอกสารส่งงานและตรวจครั้งสุดท้าย

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`

- [ ] **Step 1: เขียน README ส่วน ngspice**

ระบุเส้นทางจริง: `C:\Users\B6807153\ngspice\bin\ngspice.exe`, การเพิ่ม PATH, `SPICE_LIB_DIR`, วิธีตรวจ `ngspice --version`, env `NGSPICE_BIN`/`SPICE_MODEL_PATH`, และคำเตือนว่า model เป็น placeholder

- [ ] **Step 2: เขียน `docs/validation.md`**

ตาราง B1–B8: วิธีตรวจ, ค่าที่อ่านได้จริง (คัดลอกจากผลรัน ไม่เดา), ผ่าน/ไม่ผ่าน, หมายเหตุ `NOT RUN` ถ้ามี; ระบุ SHA ของ commit ที่ใช้ตรวจ

- [ ] **Step 3: ตรวจทั้งชุดอีกครั้ง**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK; จำนวนเทสต์ตรงกับที่เขียนในเอกสาร

- [ ] **Step 4: ตรวจ git**

Run: `git status --short`
Expected: ไม่มีไฟล์ค้างที่ไม่ได้ตั้งใจ (ไม่มี `__pycache__`, ไม่มี temp)

- [ ] **Step 5: Commit และ push**

```bash
git add README.md docs/validation.md
git commit -m "docs: document Lab 04 setup and browser acceptance"
git push -u origin feat/lab04-spice-amplifier
```
