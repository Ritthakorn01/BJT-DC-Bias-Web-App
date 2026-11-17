# Lab 03 — Fixed Bias + Emitter Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed Bias และ Emitter Bias ให้เว็บ Flask เดิม โดยคงผล Voltage Divider เดิมไว้ทุกหลัก

**Architecture:** สมการอยู่ใน `dc_bias.py` แยกฟังก์ชันต่อโหมดและคืน `BiasResult` ที่มี `to_dict()` สำหรับ Flask; `app.py` ใช้ `if/elif` เลือกโหมดและตรวจเฉพาะช่องของโหมด; `templates/index.html` หน้าเดียว เลือกโหมดผ่าน `GET /?mode=` แล้วโหลดฟอร์มใหม่โดยไม่ใช้ JavaScript

**Tech Stack:** Python 3.15, Flask 3.x, Jinja2, unittest (standard library)

**Spec:** `docs/lab03-design.md`

## Global Constraints

- สมการฟิสิกส์ทั้งหมดอยู่ใน `dc_bias.py`; template และ `app.py` ห้ามมีสมการ
- หน่วยภายใน SI (V, A, Ω); แปลงเป็น V/mA/µA เฉพาะ `BiasResult.to_dict()` และ template แสดงผล
- Error ทั้งหมดตอบ HTTP 200 พร้อม error box; ห้าม 400/500
- ห้ามใช้ JavaScript คำนวณผล; ไม่ใช้ CDN; ไม่เพิ่ม dependency
- ข้อความ error เป็นภาษาไทย; ศัพท์วิศวกรรมคงอังกฤษ (VCC, VCE, β)
- ค่าคาดหวังในเทสต์ต้องมาจากการคำนวณมือ: VCC=12, RC=2.2 kΩ, β=100, VBE=0.70
  - A1 Divider R1=100k R2=22k RE=1k: IC 1.2299 mA, VCE 8.0522 V
  - A2 Fixed RB=1M: IC 1.1300 mA, VCE 9.5140 V
  - A3 Emitter RB=1M RE=1k: IC 1.0263 mA, VCE 8.7054 V
  - A4 Emitter RB=1M RE=2k: IC 0.9401 mA, VCE 8.0328 V
- ห้าม commit ในเซสชันนี้จนกว่าผู้ใช้จะยืนยัน (ต่างจากค่าเริ่มต้นของ skill)

## Review Focus

1. **RB = 0 หรือค่าติดลบ** → ต้องเป็น error ที่ระบุชื่อ RB ไม่ใช่ traceback (Task 3, 4)
2. **A1 เดิม** → Divider ต้องให้ 1.230 mA / 8.052 V เท่า Lab 2 (Task 1, 2)
3. **โหมดไม่รู้จัก** → ต้อง error ไม่ใช่เงียบ ๆ ใช้ Divider (Task 3)
4. **ค่าที่กรอกหลัง error** → ต้องคงค่าและโหมดเดิม แต่ไม่แสดงผลรอบเก่า (Task 3, 4)
5. **หน่วย kΩ** → ต้องคูณ 1000 ครั้งเดียวกับทุกตัวต้านทานของโหมดนั้น (Task 3)

---

### Task 1: Fixed Bias ใน `dc_bias.py`

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces: `calculate_fixed(vcc: float, rb: float, rc: float, beta: float, vbe: float) -> BiasResult`
- Consumes: `BiasResult`, `classify_region()`, `VCE_SAT`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class FixedBiasTests(unittest.TestCase):
    def test_reference_point_matches_hand_calculation(self):
        r = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 0.70)
        self.assertAlmostEqual(r.ib * 1e6, 11.300, delta=0.01)
        self.assertAlmostEqual(r.ic * 1e3, 1.130, delta=0.01)
        self.assertAlmostEqual(r.ie * 1e3, 1.141, delta=0.01)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 0.70, delta=0.01)
        self.assertAlmostEqual(r.vc, 9.514, delta=0.01)
        self.assertAlmostEqual(r.vce, 9.514, delta=0.01)
        self.assertEqual(r.region, "Forward Active")

    def test_cutoff_when_vbe_reaches_vcc(self):
        r = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 12.0)
        self.assertEqual(r.region, "Cutoff")
        self.assertEqual(r.ic, 0.0)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_dc_bias.FixedBiasTests -v`
Expected: ERROR `cannot import name 'calculate_fixed'`

- [ ] **Step 3: เพิ่ม `calculate_fixed`**

`if vbe >= vcc` คืนผล Cutoff (ib=ic=ie=0, ve=0, vb=vcc, vc=vcc, vce=vcc, warning เดียวกับ Divider)
มิฉะนั้น `ib=(vcc-vbe)/rb`, `ic=beta*ib`, `ie=(beta+1)*ib`, `ve=0`, `vb=vbe`, `vc=vcc-ic*rc`, `vce=vc`
แล้วตัดสิน region/warning ด้วยตรรกะเดียวกับ Divider

- [ ] **Step 4: รันให้ผ่าน**

Run: เดียวกับ Step 2 — Expected: OK

---

### Task 2: Emitter Bias + `to_dict()`

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces: `calculate_emitter(vcc, rb, rc, re, beta, vbe) -> BiasResult`
- Produces: `BiasResult.to_dict() -> dict` คีย์ `vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ua, ie_ma, region, warnings`
- Produces: `calculate_divider(...)` (rename ของ `calculate`), คง `calculate` เป็น alias

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class EmitterBiasTests(unittest.TestCase):
    def test_reference_point_matches_hand_calculation(self):
        r = calculate_emitter(12.0, 1_000_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertAlmostEqual(r.ic * 1e3, 1.0263, delta=0.01)
        self.assertAlmostEqual(r.vce, 8.7054, delta=0.02)

    def test_larger_re_lowers_ic(self):
        r = calculate_emitter(12.0, 1_000_000.0, 2_200.0, 2_000.0, 100.0, 0.70)
        self.assertAlmostEqual(r.ic * 1e3, 0.9401, delta=0.01)
        self.assertAlmostEqual(r.vce, 8.0328, delta=0.02)

class ResultDictTests(unittest.TestCase):
    def test_shared_keys_and_units(self):
        d = calculate_fixed(12.0, 1_000_000.0, 2_200.0, 100.0, 0.70).to_dict()
        self.assertEqual(set(d), {"vb_v", "ve_v", "vc_v", "vce_v",
                                  "ic_ma", "ib_ua", "ie_ma", "region", "warnings"})
        self.assertAlmostEqual(d["ic_ma"], 1.130, delta=0.01)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_dc_bias.EmitterBiasTests tests.test_dc_bias.ResultDictTests -v`
Expected: ERROR `cannot import name 'calculate_emitter'` / `AttributeError: to_dict`

- [ ] **Step 3: เพิ่ม `calculate_emitter` และ `to_dict()`**

Emitter: `ib=(vcc-vbe)/(rb+(beta+1)*re)`; ใช้รูปหารด้วย β เหมือน Divider
`ic=(vcc-vbe)/(rb/beta+re*(1+1/beta))`, `ib=ic/beta`, `ie=ic*(1+1/beta)`
`ve=ie*re`, `vb=ve+vbe`, `vc=vcc-ic*rc`, `vce=vc-ve`; Cutoff เมื่อ `vbe>=vcc` (ib=ic=ie=0, vb=vcc)
`to_dict()` แปลง `ic_ma=ic*1000`, `ib_ua=ib*1e6`, `ie_ma=ie*1000`, `warnings=list(...)`

- [ ] **Step 4: รันให้ผ่าน + รันทั้งชุดเดิม**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — Expected: OK
(REFACTOR: ดึงส่วนท้ายที่ตัดสิน region/warning ของทั้งสามโหมดมาใช้ร่วมกัน โดยเทสต์ต้องเขียวตลอด)

---

### Task 3: Flask dispatch ตามโหมด

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `calculate_fixed`, `calculate_emitter`, `calculate_divider`, `validate_common`, `validate_resistors`, `to_float`
- Produces: `GET /?mode=fixed|emitter|divider`, `POST /calculate` รับ `mode` (ค่าเริ่มต้น `divider`)

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
FIXED_FORM = {"mode": "fixed", "vcc": "12", "vbe": "0.70", "beta": "100",
              "rc": "2.2", "rb": "1000", "r_unit": "k"}
EMITTER_FORM = dict(FIXED_FORM, mode="emitter", re="1")

def test_fixed_mode_calculates(self):
    body = self.client.post("/calculate", data=FIXED_FORM).get_data(as_text=True)
    self.assertIn("Fixed Bias", body)
    self.assertIn("9.514", body)
    self.assertIn("1.130 mA", body)

def test_emitter_mode_uses_re(self):
    body = self.client.post("/calculate", data=EMITTER_FORM).get_data(as_text=True)
    self.assertIn("8.705", body)

def test_unknown_mode_is_error(self):
    body = self.client.post("/calculate", data=dict(FIXED_FORM, mode="mystery")).get_data(as_text=True)
    self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
    self.assertNotIn("Region:", body)

def test_zero_rb_names_the_field(self):
    body = self.client.post("/calculate", data=dict(FIXED_FORM, rb="0")).get_data(as_text=True)
    self.assertIn("RB", body)
    self.assertNotIn("Region:", body)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v` — Expected: FAIL (ผลยังเป็น Divider / ไม่มีข้อความโหมด)

- [ ] **Step 3: แก้ `app.py`**

เพิ่ม `MODE_LABELS = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
ตรวจ `mode` ในรายการก่อน; แปลงหน่วย kΩ→Ω ครั้งเดียวต่อค่าที่โหมดใช้
`if/elif` ตามโหมด: เรียก validator ที่ตรงกับช่อง แล้วเรียกฟังก์ชันของโหมด
ส่ง `result=result.to_dict()`; error → `result=None` คง `form` และ `mode`

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v` — Expected: OK

---

### Task 4: ฟอร์มเลือกโหมดใน template

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_web.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
def test_default_is_divider_with_divider_fields(self):
    body = self.client.get("/").get_data(as_text=True)
    self.assertIn('value="divider" selected', body)
    self.assertIn('id="r1"', body)
    self.assertNotIn('id="rb"', body)

def test_fixed_mode_shows_only_rb(self):
    body = self.client.get("/?mode=fixed").get_data(as_text=True)
    self.assertIn('id="rb"', body)
    self.assertNotIn('id="r1"', body)
    self.assertIn('selected', body)

def test_emitter_mode_shows_rb_and_re(self):
    body = self.client.get("/?mode=emitter").get_data(as_text=True)
    self.assertIn('id="rb"', body)
    self.assertIn('id="re"', body)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web.TemplateModeTests -v` — Expected: FAIL

- [ ] **Step 3: แก้ `templates/index.html`**

เพิ่มฟอร์มโหมด `GET /` (`select#mode` + ปุ่ม) แยกจากฟอร์มคำนวณ
ฟอร์มคำนวณมี `hidden mode`; แสดงช่องตามโหมด (`divider`: r1,r2,re; `fixed`: rb; `emitter`: rb,re)
เพิ่ม `id` ให้ทุก input และ `for` ให้ label; หัวผลลัพธ์ระบุชื่อโหมด

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — Expected: OK

---

### Task 5: เอกสารและ config

**Files:**
- Modify: `AGENTS.md`, `README.md`
- Create: `opencode.json`

- [ ] **Step 1:** `AGENTS.md` — เปลี่ยนขอบเขตเป็น Lab 03 (สามโหมด) คงกติกาสมการ/หน่วย/HTTP 200; ระบุว่า Flask ใช้ `to_dict()` และงานตรวจหลักคือ Browser A1–A5
- [ ] **Step 2:** `README.md` — ระบุสามโหมด, วิธีรัน, วิธีเปิดแต่ละโหมด, ค่าอ้างอิง A1–A5
- [ ] **Step 3:** `opencode.json` — วาง Playwright MCP ใต้ `mcp.servers` ตามใบงาน V2
- [ ] **Step 4: ตรวจ JSON**

Run: `.venv\Scripts\python.exe -c "import json; json.load(open('opencode.json', encoding='utf-8'))"` — Expected: exit 0

---

### Task 6: ตรวจ A1–A5 ผ่านเบราว์เซอร์จริง

- [ ] **Step 1:** เริ่ม Flask: `.venv\Scripts\python.exe -m flask --app app run --port 5000` (background)
- [ ] **Step 2:** เปิด `http://127.0.0.1:5000/` ด้วย browser tool ที่มี; อ่าน snapshot และชื่อช่องจริง
- [ ] **Step 3:** รัน A1–A5 ตามตาราง design; บันทึกค่าที่เห็นจริงพร้อมหน่วย และวิธีตรวจ (`OpenCode Browser` ถ้าไม่ได้ใช้ Playwright MCP)
- [ ] **Step 4:** เก็บหลักฐานอย่างน้อย 1 กรณี (ข้อความผลหรือ screenshot)
- [ ] **Step 5:** อัปเดต `docs/validation.md` ด้วยตาราง A1–A5 และหมายเหตุข้อจำกัด Playwright MCP

---

### Task 7: ตรวจรวมก่อนส่ง

- [ ] **Step 1:** Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — Expected: OK, 0 failures
- [ ] **Step 2:** `git diff` / `git status` — ต้องไม่มี `.venv`, `.env`
- [ ] **Step 3:** ตรวจ A1 ซ้ำในเบราว์เซอร์เทียบค่ามือ (1.2299 mA / 8.0522 V)
- [ ] **Step 4:** รายงานผลและขออนุญาต commit/push (ยังไม่ commit เอง)
