# Lab 04 — BJT Amplifier Simulator v1 (CE Voltage Divider) — Design

วันที่: 2026-11-24
สถานะ: รออนุมัติ (ผ่าน builder check แล้ว)
ต่อยอดจาก: Lab 03 — BJT DC Bias Web App (`feat/lab03-bias-modes`, tip `c39515f`)

## 1. บริบทและเหตุผล

Lab 03 เป็นเครื่องคิด DC Bias แบบ analytical ล้วน (สมการใน `dc_bias.py`) ซึ่งตอบโจทย์ Lab 03 ได้ครบ
แต่ Lab 04 ต้องการ **simulator ที่รัน ngspice จริง** สำหรับวงจร Common-Emitter Voltage Divider
หนึ่งวงจร เพื่อแสดง DC operating point, AC frequency response และ Transient waveform
โดยที่กราฟทุกเส้นต้องมาจากผลการรันจริง ไม่ใช่ภาพประกอบหรือค่าที่แต่งขึ้น

เหตุผลที่ต้องทำ: คะแนน Lab 04 ให้น้ำหนักกับ "มี simulation จริง" ถึง 3 คะแนน และกำหนดไว้ชัดว่า
ถ้าเรียก ngspice ไม่ผ่านแต่ยังโชว์กราฟเดิมพร้อมสถานะ Success = FAIL

## 2. เป้าหมาย

- **G1** เพิ่มโหมดที่ 4 "CE Amplifier (SPICE)" ใน dropdown เดิมของหน้าเดียว (ผู้ใช้เลือกแบบ A)
- **G2** รัน ngspice จริง 3 analysis (`.op`, `.ac`, `.tran`) และแสดงผลที่ parse มาจากไฟล์ผลลัพธ์จริง
- **G3** DC Bias 3 โหมดเดิม (Divider / Fixed / Emitter) ยังทำงานเหมือนเดิมทุกกรณี (B1)
- **G4** จัดการ error ครบ: engine หาย, run ล้ม, output ว่าง, timeout, input ผิด — HTTP 200 + error box, คงค่าฟอร์ม, ไม่มีผลเก่าค้าง
- **G5** แยกผล SPICE กับผล Analytical ให้เห็นชัดบนหน้าเว็บ
- **G6** ใช้งานได้ที่ desktop (~1280px) และ mobile (~390px) พร้อมเอกสาร B1–B8

## 3. ไม่ใช่เป้าหมาย (Non-goals)

- ไม่ทำ drag-and-drop circuit editor หรือต่อวงจรอิสระ
- ไม่ทำ AC/Transient ให้ Fixed Bias และ Emitter Bias
- ไม่รองรับ FET / Op-Amp / วงจรหลายสเตจ
- ไม่เขียน SPICE solver เอง
- ไม่ทำ animation บนวงจร และไม่ deploy ขึ้นอินเทอร์เน็ต
- ไม่ทำ CE bypass capacitor (baseline ของแล็บไม่มี CE)
- ไม่แก้ Minor ที่ค้างใน ledger ของ Lab 03 (ยกเว้นถูกสั่ง)

## 4. Anti-goals (ทำงานได้แต่ถือว่าล้มเหลว)

- กราฟหรือตัวเลขที่ไม่ได้มาจากการรัน ngspice จริง
- คืนผล/graph เก่าพร้อมสถานะ Success เมื่อ engine ล้ม
- แสดงผล SPICE ปนกับ analytical โดยไม่ติดป้ายว่าเป็นอันไหน
- ใช้ `shell=True` หรือต่อสตริงคำสั่งจาก input ผู้ใช้
- ฝังค่าคงที่ของผลลัพธ์ไว้ใน template

## 5. ข้อจำกัด

- Windows 10/11, ngspice **47** (console build) ติดตั้งแล้วที่ `C:\Users\B6807153\ngspice\bin\ngspice.exe` อยู่ใน user PATH และตั้ง `SPICE_LIB_DIR` แล้ว
- Python 3.15.2, Flask 3.1, เทสต์เป็น `unittest`
- เครื่องไม่มี Node/npx → ติดตั้ง Impeccable ยังไม่ได้ (ต้องตัดสินใจในขั้น implement)
- ไม่มี BJT model จากผู้สอน → ใช้ **2N3904 เป็น placeholder** (ผู้ใช้เลือก) ต้องติดป้ายและเปลี่ยนได้ด้วยการแทนไฟล์เดียว
- แนวเดิมของโปรเจกต์: ไม่ใช้ JavaScript ในการคำนวณ/เติมค่า (ชุด A ที่เลือกจึงไม่มี JS เลย)
- ตัวเลข default ทั้งหมดอยู่ใน `app.py` (`DEFAULT_FORMS`) เท่านั้น

## 6. ทางเลือกที่พิจารณา

| ชุด | กราฟ | การรัน | การอ่านผล | สรุป |
|---|---|---|---|---|
| **A (เลือก)** | matplotlib → PNG ฝัง base64 | แยก 3 deck/3 process | `wrdata` ตาราง ASCII | ไม่มี JS, พิสูจน์ได้ด้วยเทสต์, ล้มแยก analysis |
| B | เขียน SVG เอง | เหมือน A | เหมือน A | ไม่เพิ่ม dependency แต่ต้องเขียน chart engine เอง เสี่ยงบั๊ก |
| C | Chart.js ฝั่ง client | deck เดียว | raw file | โต้ตอบได้ แต่ต้องใช้ JS, ต้อง vendor ไฟล์, ล้มทั้งชุด |

**เหตุผลที่เลือก A:** โจทย์ให้คะแนนที่ "กราฟมาจากการรันจริง" — PNG ที่สร้างจาก array จริงตรวจได้ด้วยเทสต์ (magic bytes + ค่าใน array) ง่ายที่สุด, คงปรัชญาไม่ใช้ JS, และการแยก run ทำให้ B7 (engine fail) ตรวจได้ตรงจุด
ยืนยันแล้วว่า `matplotlib 3.11.2` มี wheel `cp315-win_amd64` จึงติดตั้งได้บน Python 3.15.2

## 7. สถาปัตยกรรม

```
Browser (GET /?mode=amp, POST /calculate)
   │
   ▼
app.py ── validate ฟอร์ม (reuse to_float / validate_*)
   │        ├─ mode ∈ {divider, fixed, emitter} → dc_bias.py (เดิม ไม่แก้)
   │        └─ mode = amp → spice_engine.analyze(...)
   ▼
spice_engine.py
   ├─ build_*_netlist(inputs, model_path) → str
   ├─ run_ngspice(netlist, kind) → tempdir + subprocess.run([...], timeout)
   ├─ parse_* (wrdata text) → dataclass หน่วย SI
   └─ plot_ac / plot_tran → PNG bytes
   ▼
templates/index.html (+ static/style.css)
```

### ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `spice_engine.py` | **ใหม่** — netlist, runner, parser, plot |
| `spice/models/2n3904.lib` | **ใหม่** — model card placeholder พร้อมคอมเมนต์เตือน |
| `app.py` | เพิ่ม `MODE_LABELS["amp"]`, `DEFAULT_FORMS["amp"]`, dispatch ใน `POST /calculate` |
| `templates/index.html` | ฟอร์มโหมด amp + ผล 3 ส่วน + ป้าย SPICE/Analytical |
| `static/style.css` | สไตล์การ์ดผล, กราฟ, responsive |
| `requirements.txt` | เพิ่ม `matplotlib>=3.11,<4` |
| `tests/test_spice_engine.py` | **ใหม่** — unit + integration |
| `tests/test_web.py` | เพิ่มเทสต์โหมด amp, error, regression |
| `README.md`, `docs/validation.md` | วิธีติดตั้ง ngspice, ตาราง B1–B8, ค่าจริง |

## 8. API ของ `spice_engine.py`

หน่วย SI ภายในทั้งหมด (V, A, Ω, F, Hz, วินาที) แปลงหน่วยแสดงผลที่ชั้น template เท่านั้น

```python
@dataclass(frozen=True)
class AmpInputs:
    vcc: float; r1: float; r2: float; rc: float; re: float; rl: float
    cin: float; cout: float
    vs_peak: float; freq: float
    beta_ref: float; vbe_ref: float   # ใช้เฉพาะ analytical reference

@dataclass(frozen=True)
class OpPoint:   vb, ve, vc, vce, ic, ib, region  # region = dc_bias.classify_region(vce)
@dataclass(frozen=True)
class AcSweep:   freq[], gain_db[], phase_deg[], midband_gain_db, gain_at_1khz_db
@dataclass(frozen=True)
class Transient: time[], vin[], vout[], vin_pp, vout_pp, inverted
@dataclass(frozen=True)
class SpiceRun:  op, ac, tran, ac_png: bytes, tran_png: bytes, engine_version: str
```

ฟังก์ชันหลัก: `analyze(inputs) -> SpiceRun`, `build_op_netlist`, `build_ac_netlist`,
`build_tran_netlist`, `run_netlist`, `parse_op`, `parse_ac`, `parse_tran`,
`plot_ac`, `plot_tran`, `to_display(run) -> dict`

- `build_*_netlist(inputs)` อ้าง model ด้วยชื่อคงที่ `.include model.lib`
- `run_netlist(netlist, tag, timeout_s=20.0) -> (table_text, engine_version)` สร้าง temp dir ต่อรอบ, คัดลอกไฟล์ model เข้าไปเป็น `model.lib`, แล้วรัน `[ngspice, "-b", "deck.cir", "-o", "run.log"]`
- ตัวเลือกผ่าน env (มีไว้ทดสอบ/สลับ model): `NGSPICE_BIN` (default `ngspice`), `SPICE_MODEL_PATH` (default `spice/models/2n3904.lib`)

### Error taxonomy

| อินพุต | ความหมาย | ข้อความผู้ใช้ |
|---|---|---|
| `SpiceNotFound` | `FileNotFoundError` ตอน spawn | "ไม่พบ ngspice ในเครื่องนี้ กรุณาติดตั้งและเพิ่มเข้า PATH" |
| `SpiceTimeout` | เกิน 20 วินาที/analysis | "ngspice ใช้เวลานานเกินกำหนด" |
| `SpiceFailed` | exit code ≠ 0 | "ngspice ทำงานไม่สำเร็จ" + ท้าย stderr |
| `SpiceEmpty` | ไฟล์ผลลัพธ์ว่าง/ไม่มีข้อมูล | "ngspice ไม่คืนผลลัพธ์" |
| `SpiceParse` | อ่านตารางไม่ได้ | "อ่านผลลัพธ์จาก ngspice ไม่ได้" |

ทั้งหมดถูกแปลงเป็น error box ผ่านเส้นทางเดียวกับ `ValidationError` ของ Lab 03

## 9. Netlist

สร้างเป็น ASCII, ตัวเลขจัดรูปแบบ `f"{x:.12g}"`, path ของ model ใช้ absolute + forward slash

```
* CE amplifier — {kind}
.include model.lib
VCC vcc 0 DC {vcc}
R1  vcc vb {r1}
R2  vb 0 {r2}
RC  vcc vc {rc}
RE  ve 0 {re}
Q1  vc vb ve Q2N3904
VS  in 0 DC 0 AC 1 SIN(0 {vs_peak} {freq})
CIN in vb {cin}
COUT vc out {cout}
RL  out 0 {rl}
.control
set wr_singlescale
set wr_vecnames
{op | ac dec 20 10 1meg | tran {tstep} {tstop}}
wrdata {outfile} {vectors}
.endc
.end
```

- `.op` → vectors: `v(vb) v(ve) v(vc) v(vcc)` + กระแส BJT (`@q1[ic]`, `@q1[ib]`) ถ้ามี; ถ้าไม่มีให้ fallback คำนวณ IC = (VCC − VC)/RC จาก node voltage และบันทึกที่มา
- `.ac` → `v(out) v(in)`, 10 Hz–1 MHz, 20 จุด/decade
- `.tran` → `v(in) v(out)`, `tstop = 5/freq`, `tstep = tstop/2000`
- model ถูกคัดลอกเข้า temp dir เป็น `model.lib` ทุกครั้ง → ไม่มีปัญหา path มีช่องว่าง/อักษรไทย
- ทุก deck อยู่คนละ temp dir, ลบใน `finally`

## 10. การอ่านผล

- `wrdata` ให้ตาราง text: 1 คอลัมน์ scale + N คอลัมน์ค่า, มีหัวชื่อ vector
- AC เป็นจำนวนเชิงซ้อน → คำนวณ magnitude/phase ใน Python
  - **reference ที่ชัดเจน:** gain = 20·log10(|V(out)/V(in_source)|), phase = arg(V(out)) − arg(V(in_source)) โดย `V(in_source)` คือโหนดก่อน Cin
- Transient: อ่าน arrays เต็ม, หา peak-to-peak และตรวจการกลับเฟสจากเครื่องหมายของจุดสูงสุดเทียบ Vin

## 11. UI

- dropdown เดิมเพิ่ม `amp` → "CE Amplifier (SPICE)"
- ฟอร์มโหมด amp: VCC [V], R1, R2, RC, RE, RL (หน่วย kΩ/Ω เลือกได้เหมือนเดิม), Cin/Cout [µF], Vs [mV peak], f [Hz], β และ VBE (ใช้เฉพาะ analytical reference — ติดป้ายให้ชัด)
- ค่า default ของโหมด amp (ที่มา: input fixture ในใบงาน Lab 04; β/VBE มาจาก Lab 03 เพื่อใช้เป็น analytical reference เท่านั้น)
  VCC 12 V · R1 100 kΩ · R2 22 kΩ · RC 2.2 kΩ · RE 1 kΩ · RL 10 kΩ · Cin 10 µF · Cout 10 µF · Vs 10 mV peak · f 1 kHz · β 100 · VBE 0.70 V
  ค่าเหล่านี้อยู่ใน `DEFAULT_FORMS["amp"]` ใน `app.py` เท่านั้น
- ผลลัพธ์ 3 การ์ด:
  1. **DC Operating Point — SPICE** (VB, VE, VC, VCE, IC, IB, Region) + ตารางเทียบ **Analytical** และผลต่าง
  2. **AC Bode** — กราฟ magnitude (dB) + phase (°) เทียบ frequency (log), สรุป midband gain และ gain ที่ 1 kHz
     (นิยาม: `midband gain` = ค่า gain_db สูงสุดในช่วง 100 Hz–10 kHz — ใช้ตรงกันทั้ง UI และเทสต์)
  3. **Transient** — กราฟ Vin/Vout เทียบเวลา, ค่า pp, สถานะกลับเฟส
- ป้ายประจำการ์ด: "ngspice 47 (ผลจำลองจริง)" และ "dc_bias.py (คำนวณมือ)"
- ไม่มี JavaScript; responsive ด้วย CSS grid → 1 คอลัมน์ที่ ~390px

## 12. Error handling

- ทุก error = HTTP 200 + error card + คงค่าที่กรอก + **ไม่มีผลลัพธ์ใด ๆ** (all-or-nothing)
- ถ้า analysis ใดล้ม ให้ล้มทั้งชุดและระบุชื่อ analysis ที่ล้ม (กันการเห็นกราฟบางส่วนแล้วเข้าใจผิดว่า Success)
- timeout 20 วินาทีต่อ analysis, kill process tree
- ไม่มี state ข้าม request (ไม่มี session/cache) → ไม่มีทางเห็นกราฟเก่า

## 13. แผนเทสต์

**Unit (ไม่ต้องมี ngspice)**
- netlist: ค่าที่กรอกปรากฏใน netlist ถูกตำแหน่ง, จำนวนบรรทัดคงที่, ไม่มีอักขระแปลกปลอมหลุดเข้า deck
- parser: ตารางตัวอย่าง → dataclass ถูกต้อง, ตัวเลขว่าง/สั้นเกิน → `SpiceParse`
- error mapping: FileNotFoundError/TimeoutExpired/exit≠0/ไฟล์ว่าง
- plot: ได้ bytes ขึ้นต้นด้วย `\x89PNG`, ขนาด > 0

**Integration (skip ถ้าไม่พบ ngspice)**
- baseline: `.op` ให้ค่าที่สมเหตุสมผล — 0 < VCE < VCC, IC > 0, region = Forward Active, และทุกค่าอยู่ในกรอบ ±25% ของ analytical (กรอบหลวมเพื่อจับ bug ร้ายแรงเท่านั้น)
- เปลี่ยน RE 1k→2k: IC ลดลง
- เปลี่ยน Vs 10mV→20mV: Vout_pp เพิ่ม ~2 เท่า
- AC: จำนวนจุด ≥ 50; gain ที่ 1 kHz เป็นค่าจำกัดและอยู่ระหว่าง −20 ถึง +30 dB; phase ที่ 1 kHz ≈ 180° ± 30° (กลับเฟส); gain ที่ 10 Hz ต่ำกว่า gain ที่ 1 kHz (ผลของ Cin)
- Transient: จำนวนจุด > 100, Vout กลับเฟสกับ Vin

**Web**
- `GET /?mode=amp` → 200, ฟอร์มมีช่องครบ
- `POST /calculate` mode=amp ค่าผิด → 200 + error + คงค่า
- monkeypatch engine ให้ raise → 200 + error + ไม่มีกราฟ
- regression 3 โหมดเดิม (ค่า A1–A5 ยังตรง)
- unknown mode ยัง error เหมือนเดิม

## 14. เกณฑ์เทียบ SPICE กับ Analytical (DC)

- เทียบเฉพาะ VB, VE, VC, VCE, IC
- **ไม่ใช้ผลต่างเป็นเงื่อนไขผ่าน/ไม่ผ่านของเทสต์** เพราะ SPICE ใช้ model จริง (BF ≈ 416 และ VBE จากรอยต่อ p-n) ขณะที่ analytical ตรึง β ตามฟอร์ม (100) และ VBE 0.70 V → คาดต่างกันได้ราว 5–15% ตามธรรมชาติ
- หน้าเว็บแสดงผลต่างเป็น % ทุกแถว พร้อมหมายเหตุอธิบายสาเหตุ (β ใน model ≠ β ในฟอร์ม)
- เกณฑ์เตือนแบบ soft: |Δ| > 15% → แสดงข้อความเตือนใต้ตาราง (ไม่ใช่ error และไม่บล็อกผล)
- เทสต์ integration ยึด "ความสมเหตุสมผล + แนวโน้ม" (ดูข้อ 13) ไม่ยึดการเทียบค่าตรง
- ถ้า SPICE กับ analytical ให้ region ต่างกัน ให้แสดงทั้งสองค่าตามจริง ไม่ถือเป็น error

## 15. การโยง B1–B8

| ข้อ | วิธีตรวจ |
|---|---|
| B1 | unittest regression 3 โหมด + เปิดเว็บกดจริง |
| B2 | การ์ด DC Operating Point จาก `.op` |
| B3 | เปลี่ยน RE 1k→2k แล้ว IC/VCE เปลี่ยนจริง |
| B4 | กราฟ Bode magnitude + phase จาก `.ac` |
| B5 | กราฟ Vin/Vout จาก `.tran` |
| B6 | เปลี่ยน Vs 10mV→20mV แล้วกราฟ/ค่า pp เปลี่ยน |
| B7 | กรอกค่าผิด + จำลอง engine ล้ม (rename exe ชั่วคราว) |
| B8 | screenshot 1280px และ 390px |

## 16. เอกสารและงานส่ง

- `README.md`: วิธีติดตั้ง ngspice บน Windows (เส้นทางที่ใช้จริง: MSYS2 ucrt64 → ชุดพกพา + PATH + `SPICE_LIB_DIR`), วิธีรัน, ข้อจำกัด model placeholder
- `docs/validation.md`: ตาราง B1–B8 + ค่าที่วัดได้จริง + ระบุ `NOT RUN` ถ้าข้อใดยังไม่ได้รัน
- `docs/screenshots/`: `lab04-desktop.png`, `lab04-mobile.png`
- บันทึก 3–5 บรรทัดว่า AI ทำอะไร / เราตรวจอะไร

## 17. ความเสี่ยงและการรับมือ

| ความเสี่ยง | การรับมือ |
|---|---|
| รูปแบบ `wrdata` ไม่ตรงที่คาด | spike สั้น ๆ ก่อนเขียน parser; ถ้าไม่ได้ใช้ `-r` raw ASCII แทน |
| `@q1[ic]` ไม่มีใน `.op` | fallback คำนวณจาก node voltage + ระบุที่มา |
| ไม่มี Node → Impeccable | แผน: ติดตั้ง Node LTS ผ่าน `winget install OpenJS.NodeJS.LTS` → `npx impeccable install` (project scope) → critique/polish/audit; ถ้าติดตั้งไม่สำเร็จ บันทึก `NOT RUN` และทำ audit ด้วยมือ (ไม่แต่งผล) |
| model 2N3904 ไม่ใช่ของอาจารย์ | เก็บเป็นไฟล์เดียว เปลี่ยนได้โดยไม่แตะโค้ด |
| Python 3.15 + matplotlib | ยืนยันแล้วว่ามี wheel cp315 |
| ข้อความไทยใน netlist ทำให้ encoding เพี้ยน | netlist เป็น ASCII ล้วน (คอมเมนต์อังกฤษ) |

## 18. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- สี/ขนาด/จำนวน tick ของกราฟ และ layout ละเอียดของ CSS
- ชื่อฟังก์ชัน/คลาสภายใน, การแบ่งไฟล์ย่อยถ้า `spice_engine.py` ยาวเกิน ~400 บรรทัด
- จำนวนจุด sweep ที่เหมาะสมกับขนาด PNG
- ถ้อยคำ error ภาษาไทยฉบับเต็ม
- จะแสดงกราฟ DC เพิ่มหรือไม่ (ไม่บังคับตามใบงาน)

## 19. กระบวนการ

- branch: `feat/lab04-spice-amplifier` แตกจาก `feat/lab03-bias-modes` (tip `c39515f`) เพื่อไม่ต้องรอ merge PR #1; ถ้า PR #1 ถูก merge ก่อน จะ rebase ให้ประวัติสะอาด
- ลำดับ: design อนุมัติ → plan → TDD implement (engine ก่อน แล้ว UI) → browser acceptance B1–B8 → docs → commit/PR
