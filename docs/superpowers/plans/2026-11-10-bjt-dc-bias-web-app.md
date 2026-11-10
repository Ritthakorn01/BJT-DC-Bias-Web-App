# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web Application หลายไฟล์ที่รับค่า VCC, R1, R2, RC, RE, β, VBE แล้วคำนวณ DC Operating Point ของวงจร Voltage-Divider Bias พร้อม validation, region warning และ automated tests

**Architecture:** Flask app factory (`create_app()`) ทำหน้าที่รับ HTTP และ render Jinja template เท่านั้น ส่วนสมการและกฎ region ทั้งหมดอยู่ใน `dc_bias.py` ซึ่งเป็น pure Python ไม่รู้จัก HTML/HTTP ทำให้เทสต์วิศวกรรมแยกจากเทสต์ HTTP ได้

**Tech Stack:** Python 3.15.2, Flask >=3.1,<4, `unittest` (standard library), Jinja2 templates, CSS เขียนเอง (ไม่มี CDN, ไม่มี JavaScript)

**Spec:** `docs/design-note.md`

## Global Constraints

- Python interpreter: `py` หรือ `.venv\Scripts\python.exe` — คำสั่ง `python` ใช้ได้หลังแก้ PATH แล้ว แต่ให้ใช้ `.venv\Scripts\python.exe` ในทุกคำสั่งของแผนนี้เพื่อความแน่นอน
- Dependency เดียวที่อนุญาต: `Flask>=3.1,<4` (ไม่เพิ่ม pytest, ไม่เพิ่ม flask-wtf)
- เทสต์ใช้ `unittest` เท่านั้น รันด้วย `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- tolerance ของค่าอ้างอิง: absolute **0.01 ในหน่วยที่แสดงผล** (V, mA, µA)
- ค่าคงที่: `VCE_SAT = 0.2` V
- region string ต้องเป็น `"Forward Active"`, `"Cutoff"`, `"Saturation"` (ตัวพิมพ์ตรงตามนี้)
- ห้ามมี JavaScript คำนวณผล และห้าม hardcode ผลลัพธ์ใน template
- ทุก response ของ error เป็น **HTTP 200** พร้อม error box (ไม่ใช้ 400/500)
- ไฟล์ทั้งหมดเป็น UTF-8, template ต้องมี `<meta charset="utf-8">`
- ชื่อฟังก์ชัน/ฟิลด์ต้องตรงกับ Interfaces block ของแต่ละ task (งานถัดไปอ้างอิงชื่อเหล่านี้)

## Review Focus

จุดที่คนใช้จริงมีโอกาสเจอ แต่ spec ไม่ได้เขียนถึง — แต่ละข้อมีเทสต์ประจำ task ที่ owns โค้ดนั้น

1. **หน่วยตัวต้านทาน kΩ/Ω** — ผู้ใช้เลือก kΩ แต่พิมพ์ค่าที่เป็น Ω อยู่แล้ว (หรือกลับกัน) ผลจะคลาด 1000 เท่าโดยไม่มีอาการผิดปกติ → Task 5
2. **ช่องว่างหรือ comma ในตัวเลข** — `" 100 "`, `"1,000"` ต้องไม่ทำให้หน้าเว็บล้ม → Task 3
3. **VBE ≥ VCC หรือค่าติดลบ** — ฟิสิกส์เป็นไปไม่ได้ ต้องถูกปฏิเสธพร้อมข้อความ ไม่ใช่ปล่อยให้ได้ IB ติดลบ → Task 3
4. **ค่าสุดขั้วจนได้ inf/nan** — β มหาศาลหรือ R เล็กมาก ต้องไม่แสดง `nan`/`inf` บนหน้าจอ → Task 5
5. **ข้อความไทยและ encoding** — error/warning ภาษาไทยต้องแสดงถูกต้อง ไม่เป็น mojibake → Task 5

---

### Task 1: Scaffold โปรเจกต์ + GET / แสดงฟอร์ม

**Files:**
- Create: `requirements.txt`, `.gitignore`, `app.py`, `templates/index.html`, `static/style.css`, `tests/test_web.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces: `app.create_app() -> flask.Flask` ที่มี route `GET /` → HTTP 200

- [ ] **Step 1: สร้าง venv และติดตั้ง Flask**

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install "Flask>=3.1,<4"
.venv\Scripts\python.exe -m pip show flask
```

Expected: `pip show flask` แสดง Version 3.1 ขึ้นไป และ import ได้บน Python 3.15

- [ ] **Step 2: บันทึก dependency และ ignore file**

`requirements.txt`:
```
Flask>=3.1,<4
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
```

- [ ] **Step 3: เขียนเทสต์ที่ยังไม่ผ่าน**

`tests/test_web.py`:
```python
import unittest

from app import create_app


class WebIndexTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_index_returns_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculate DC Bias", response.data)
        self.assertIn(b'name="vcc"', response.data)
        self.assertIn(b'name="r1"', response.data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: รันเทสต์ให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 5: เขียน `create_app()` + template + CSS**

`app.py` (เริ่มจากโครงนี้ — route `/calculate` จะเพิ่มใน Task 5):
```python
from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", form={}, result=None, errors=[], warnings=[])

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
```

`templates/index.html` ต้องมี: `<meta charset="utf-8">`, `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`, `<form method="post" action="/calculate">`, input ชื่อ `vcc`, `vbe`, `r1`, `r2`, `rc`, `re`, `beta`, select ชื่อ `r_unit` (ค่า `k` = kΩ เลือกไว้, ค่า `` = Ω), ปุ่ม submit ที่มีข้อความ `Calculate DC Bias`, และ `<div class="results">` ที่จะแสดงผลเมื่อ `result` ไม่ใช่ None

`static/style.css`: layout เรียบ ๆ ใช้ system font, `.results` เป็น grid, `@media (max-width: 640px)` ยุบเป็นคอลัมน์เดียว

- [ ] **Step 6: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 1 test

- [ ] **Step 7: ตรวจด้วย Browser จริง**

Run (background): `.venv\Scripts\python.exe -m flask --app app run --port 5000`
เปิด `http://127.0.0.1:5000/` → เห็นฟอร์ม, ส่ง request แล้วได้ 200
จากนั้นหยุด server

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .gitignore app.py templates/index.html static/style.css tests/test_web.py
git commit -m "feat: scaffold Flask app with DC bias input form"
```

---

### Task 2: โมดูลคำนวณ DC Bias (ค่าอ้างอิง)

**Files:**
- Create: `dc_bias.py`, `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces:
  - `class BiasResult` (frozen dataclass) ฟิลด์: `vth, rth, ib, ic, ie, ve, vb, vc, vce: float` (SI: V, A, Ω), `region: str`, `warnings: tuple[str, ...]`
  - `calculate(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float) -> BiasResult`
  - `VCE_SAT = 0.2`

- [ ] **Step 1: เขียนเทสต์ค่าอ้างอิง**

`tests/test_dc_bias.py`:
```python
import unittest

from dc_bias import calculate


class ReferencePointTests(unittest.TestCase):
    def setUp(self):
        # VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100, VBE=0.70
        self.result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

    def test_voltages_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.vth, 2.164, delta=0.01)
        self.assertAlmostEqual(self.result.vb, 1.942, delta=0.01)
        self.assertAlmostEqual(self.result.ve, 1.242, delta=0.01)
        self.assertAlmostEqual(self.result.vc, 9.294, delta=0.01)
        self.assertAlmostEqual(self.result.vce, 8.052, delta=0.01)

    def test_currents_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.ic * 1000, 1.230, delta=0.01)
        self.assertAlmostEqual(self.result.ie * 1000, 1.242, delta=0.01)
        self.assertAlmostEqual(self.result.ib * 1_000_000, 12.299, delta=0.01)

    def test_reference_point_is_forward_active(self):
        self.assertEqual(self.result.region, "Forward Active")
        self.assertEqual(self.result.warnings, ())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v -k ReferencePointTests`
Expected: ERROR `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: เขียน `dc_bias.py`**

สร้าง `BiasResult` เป็น `@dataclass(frozen=True)` ตามฟิลด์ใน Interfaces และ `calculate()` ที่ใช้สมการ:

```
vth = vcc*r2/(r1+r2)
rth = r1*r2/(r1+r2)
ib  = (vth - vbe)/(rth + (beta+1)*re)
ic  = beta*ib
ie  = (beta+1)*ib
ve  = ie*re
vb  = ve + vbe
vc  = vcc - ic*rc
vce = vc - ve
```

ใน Task นี้ให้ `region="Forward Active"` และ `warnings=()` แบบคงที่ก่อน (Task 4 จะแทนด้วยกฎจริง)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 4 tests

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add DC bias calculation core with reference tests"
```

---

### Task 3: แปลงค่าและ Validation ของข้อมูลนำเข้า

**Files:**
- Modify: `dc_bias.py`, `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `calculate()` จาก Task 2
- Produces:
  - `class ValidationError(Exception)` มี attribute `message: str`
  - `to_float(text: str, name: str) -> float` — strip ช่องว่าง, ตัด comma ที่เป็นตัวคั่นหลักพัน, raise `ValidationError` เมื่อว่างหรือไม่ใช่ตัวเลข
  - `validate_inputs(vcc, r1, r2, rc, re, beta, vbe) -> None` — raise `ValidationError`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_dc_bias.py`:
```python
from dc_bias import ValidationError, to_float, validate_inputs


class InputParsingTests(unittest.TestCase):
    def test_accepts_surrounding_whitespace(self):
        self.assertEqual(to_float("  100 ", "R1"), 100.0)

    def test_accepts_thousands_separator(self):
        self.assertEqual(to_float("1,000", "R1"), 1000.0)

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            to_float("   ", "R1")

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValidationError):
            to_float("abc", "R1")


class ValidationTests(unittest.TestCase):
    def test_rejects_zero_resistance(self):
        with self.assertRaises(ValidationError):
            validate_inputs(12.0, 0.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)

    def test_rejects_non_positive_beta(self):
        with self.assertRaises(ValidationError):
            validate_inputs(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 0.0, 0.70)

    def test_rejects_vbe_not_below_vcc(self):
        with self.assertRaises(ValidationError):
            validate_inputs(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 12.0)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v -k InputParsingTests`
Expected: ImportError `cannot import name 'ValidationError'`

- [ ] **Step 3: เพิ่ม `ValidationError`, `to_float`, `validate_inputs`**

ใน `dc_bias.py` — กติกา validation ตรงตาม design §10: `vcc > 0`, `r1/r2/rc/re > 0`, `beta > 0`, `0 < vbe < vcc` โดยข้อความ error เป็นภาษาไทย ระบุชื่อ field ที่ผิด

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 11 tests

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: validate and parse DC bias inputs"
```

---

### Task 4: Region Detection และ Warnings

**Files:**
- Modify: `dc_bias.py`, `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `calculate()` (Task 2), `ValidationError` (Task 3)
- Produces: `calculate()` คืน `region` ∈ {`"Forward Active"`, `"Cutoff"`, `"Saturation"`} และ `warnings` ที่ไม่ว่างเมื่อไม่อยู่ใน Forward Active

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_dc_bias.py`:
```python
class RegionTests(unittest.TestCase):
    def test_cutoff_when_base_divider_below_vbe(self):
        result = calculate(12.0, 100_000.0, 1_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Cutoff")
        self.assertGreater(len(result.warnings), 0)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ve, 0.0)

    def test_saturation_when_collector_resistor_too_large(self):
        result = calculate(12.0, 100_000.0, 22_000.0, 50_000.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Saturation")
        self.assertEqual(len(result.warnings), 2)

    def test_reference_point_has_no_warning(self):
        result = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(result.region, "Forward Active")
        self.assertEqual(result.warnings, ())
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v -k RegionTests`
Expected: FAIL — region ยังเป็น `"Forward Active"` ทุกกรณี

- [ ] **Step 3: ใช้กฎ region ใน `calculate()`**

ตาม design §10:
```
ถ้า vth <= vbe       -> region="Cutoff", ib=ic=ie=0, ve=0, vb=vth, vc=vcc, vce=vcc
                         warnings มีข้อความ Cutoff 1 ข้อ
มิฉะนั้นถ้า vce < VCE_SAT -> region="Saturation"
                         warnings มีข้อความ VCE ต่ำ (1 ข้อ)
                         และถ้า vc < 0 เพิ่มข้อความ VC ติดลบ (รวมเป็น 2 ข้อ)
มิฉะนั้น              -> region="Forward Active", warnings=()
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 14 tests

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: detect cutoff and saturation regions with warnings"
```

---

### Task 5: หน้า POST /calculate แสดงผลจริง

**Files:**
- Modify: `app.py`, `templates/index.html`, `tests/test_web.py`

**Interfaces:**
- Consumes: `to_float`, `validate_inputs`, `calculate`, `ValidationError` (Tasks 2–4)
- Produces: route `POST /calculate` → HTTP 200 พร้อม context `form`, `result` (`BiasResult`), `errors` (list[str]), `warnings` (list[str])

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_web.py`:
```python
REFERENCE_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70", "r_unit": "k",
}


class CalculateRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def post(self, **overrides):
        data = dict(REFERENCE_FORM)
        data.update(overrides)
        return self.client.post("/calculate", data=data)

    def test_reference_inputs_render_results(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("9.294", body)
        self.assertIn("8.052", body)
        self.assertIn("Forward Active", body)

    def test_invalid_input_shows_error_not_crash(self):
        response = self.post(r1="0")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า 0", body)
        self.assertNotIn("Traceback", body)

    def test_non_numeric_input_shows_error(self):
        response = self.post(vcc="abc")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ตัวเลข", response.get_data(as_text=True))

    def test_resistor_unit_converts_kilo_ohm(self):
        kilo = self.post()
        ohm = self.post(r_unit="", r1="100000", r2="22000", rc="2200", re="1000")
        self.assertIn("9.294", kilo.get_data(as_text=True))
        self.assertIn("9.294", ohm.get_data(as_text=True))

    def test_extreme_beta_does_not_show_nan(self):
        body = self.post(beta="1e12").get_data(as_text=True).lower()
        self.assertNotIn("nan", body)
        self.assertNotIn("inf", body)

    def test_thai_messages_are_utf8(self):
        response = self.post(r1="0")
        self.assertIn("charset=utf-8", response.headers.get("Content-Type", "").lower())
        self.assertIn("มากกว่า 0", response.get_data(as_text=True))
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v -k CalculateRouteTests`
Expected: FAIL — ทุกเคสได้ 405 Method Not Allowed

- [ ] **Step 3: เพิ่ม route `POST /calculate`**

ใน `app.py`:
- อ่าน `request.form`
- แปลง `vcc, beta, vbe` ด้วย `to_float`
- แปลง `r1, r2, rc, re` ด้วย `to_float` แล้วคูณ 1000 เมื่อ `r_unit == "k"`
- เรียก `validate_inputs` แล้ว `calculate`
- รับ `ValidationError` → `errors=[exc.message]`, `result=None`
- เก็บค่าที่ผู้ใช้กรอกกลับไปใน `form` ทุกกรณี
- กันค่าไม่จำกัด: ถ้าผลลัพธ์ใดเป็น `math.isfinite` ไม่จริง ให้แสดงเป็น error "ค่าที่กรอกทำให้ผลลัพธ์ไม่จำกัด กรุณาตรวจสอบค่าอุปกรณ์"

- [ ] **Step 4: แสดงผลใน `templates/index.html`**

เพิ่ม block ที่ render: ตาราง `VB, VE, VC, VCE` (หน่วย V), `IC, IE` (mA), `IB` (µA) ทศนิยม 3 ตำแหน่ง, badge `region`, รายการ `warnings` ในกล่องเตือนสีส้ม, รายการ `errors` ในกล่องแดง — ทั้งหมดใช้ `{{ }}` ของ Jinja (autoescape)

การแปลงหน่วยทำใน template ด้วย filter `format` เช่น `{{ "%.3f"|format(result.ic * 1000) }}`

- [ ] **Step 5: รันเทสต์ทั้งหมดให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 20 tests

- [ ] **Step 6: ตรวจด้วย Browser จริง**

Run (background): `.venv\Scripts\python.exe -m flask --app app run --port 5000`
- กรอกค่าอ้างอิง (kΩ) → เห็น VB 1.942 / VE 1.242 / VC 9.294 / VCE 8.052 / IC 1.230 mA / region Forward Active
- กรอก R1 = 0 → เห็น error ภาษาไทย หน้าเว็บไม่ล้ม
- หยุด server

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html tests/test_web.py
git commit -m "feat: calculate and render DC bias results from form input"
```

---

### Task 6: เอกสาร, Validation Log และการตรวจรับครบวงจร

**Files:**
- Create: `README.md`, `AGENTS.md`, `docs/validation.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: แอปที่สมบูรณ์จาก Tasks 1–5
- Produces: เอกสารที่ทำให้ A7 (reproducibility) ผ่าน

- [ ] **Step 1: เขียน `README.md`**

ต้องมี: ชื่อโปรเจกต์, สมมติฐาน Forward-Active, วิธีติดตั้ง (`py -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements.txt`), วิธีรัน (`.venv\Scripts\python.exe -m flask --app app run --debug` + เปิด `http://127.0.0.1:5000/`), วิธีรันเทสต์, ตารางค่าอ้างอิงชุดทดสอบ และข้อจำกัด (ไม่มี AC/Transient/SPICE)

- [ ] **Step 2: เขียน `AGENTS.md`**

กติกา: สมการอยู่ใน `dc_bias.py` เท่านั้น, ห้ามเพิ่ม JavaScript, dependency ใหม่ต้องขออนุมัติ, ทุกฟีเจอร์ต้องมี unittest, ข้อความผู้ใช้เป็นภาษาไทย

- [ ] **Step 3: รันเทสต์เต็มชุดและบันทึกผลลง `docs/validation.md`**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

`docs/validation.md` ต้องมี: คำสั่งที่รัน, จำนวนเทสต์, ผลลัพธ์ (pass), ตารางเทียบค่าจากเว็บกับค่าคำนวณมือทั้ง 7 ค่า และรายการเคส A1–A7 พร้อมหลักฐาน

- [ ] **Step 4: เขียนโครง `docs/reflection.md`**

หัวข้อคำถาม 4 ข้อจากใบงาน (ทำไมเปิด `index.html` ตรง ๆ ไม่เท่ากับรัน Flask / ฟอร์มส่งข้อมูลไป Python อย่างไร / แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML ไหม / ทำไม region ที่แบบจำลองใช้ไม่ได้ต้องมี warning) พร้อมช่องว่างให้เจ้าของงานเติมคำตอบเอง

- [ ] **Step 5: ตรวจรับด้วย Browser ครบ A1–A7**

รัน server แล้วไล่ตามตาราง A1–A7 ใน `docs/design-note.md` §13 ทีละข้อ และจดผลลง `docs/validation.md`

- [ ] **Step 6: Commit**

```bash
git add README.md AGENTS.md docs/validation.md docs/reflection.md docs/design-note.md docs/superpowers/plans/
git commit -m "docs: add README, validation log and reflection template"
```

- [ ] **Step 7: แสดงสถานะก่อน push**

```bash
git status
git log --oneline
```

Expected: working tree สะอาด, เห็น commit 6 รายการ และไม่มี `.venv/` ถูก track
