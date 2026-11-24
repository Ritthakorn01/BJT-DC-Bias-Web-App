# Default Form Values Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ให้ `GET /?mode=...` แสดงค่าตามโจทย์ Lab 03 ในฟอร์มทันที โดยไม่ใช้ JavaScript และไม่กระทบผลคำนวณ

**Architecture:** `app.py` มี `DEFAULT_FORMS` dict แยกตามโหมด; route `index()` ส่ง dict นั้นให้ template แทน `{"r_unit": "k"}`; template ยังอ่าน `form.get()` เหมือนเดิม; `POST /calculate` ไม่เปลี่ยน จึงยังคงค่าที่ผู้ใช้ส่งตอน error

**Tech Stack:** Python 3.15, Flask 3.x, Jinja2, unittest (standard library)

**Spec:** `docs/superpowers/specs/2026-11-17-default-form-values-design.md`

## Global Constraints

- สมการและหน่วยภายในไม่เปลี่ยน; ผล A1–A5 ต้องเหมือนเดิมทุกหลัก
- ห้ามใช้ JavaScript คำนวณหรือเติมค่า; server-rendered เท่านั้น
- ตัวเลข default อยู่ใน `app.py` เท่านั้น ห้าม hard-code ใน template
- `POST /calculate` ต้องคง `form` ที่ผู้ใช้ส่งตอน error (ไม่ถูก default ทับ)
- โหมดไม่รู้จักยังตอบ error และไม่ render ช่องคำนวณ
- A4 ยังเปลี่ยน RE จาก 1 เป็น 2 kΩ ได้ด้วยมือ

## Review Focus

1. หลัง error ค่าที่ผู้ใช้พิมพ์ต้องอยู่ในฟอร์ม ไม่ใช่ค่าตามโจทย์ — ทดสอบใน Task 1 ด้วย POST ที่มีอินพุตผิดแล้ว assert `value="..."`
2. โหมดไม่รู้จักต้องไม่ได้ default และยัง error — ทดสอบใน Task 1 ด้วย `GET /?mode=mystery`
3. แต่ละโหมดต้องเห็นเฉพาะช่องของตัวเองและได้ default ตรงโหมด — ทดสอบใน Task 1 ทั้ง divider/fixed/emitter
4. การกด Calculate จาก default ต้องได้ผล A1/A2/A3 ตามเดิม — เทสต์ HTTP เดิม (`ModeCalculateTests`) + browser check ใน Task 2
5. A4 ยังเปลี่ยน RE ได้และ IC ลด — เทสต์เดิม `test_larger_re_changes_the_result` ต้องยังผ่าน

---

### Task 1: เทสต์ค่า default (RED)

**Files:**
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `create_app()` จาก `app.py`, Flask test client
- Produces: `DefaultFormTests` ที่ใช้ตรวจ Task 2

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
class DefaultFormTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_divider_defaults(self):
        body = self.client.get("/").get_data(as_text=True)
        for field, value in (("vcc", "12"), ("vbe", "0.70"), ("rc", "2.2"),
                             ("r1", "100"), ("r2", "22"), ("re", "1"),
                             ("beta", "100")):
            self.assertIn(f'name="{field}" value="{value}"', body)

    def test_fixed_defaults_have_no_divider_fields(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb" value="1000"', body)
        self.assertIn('name="vcc" value="12"', body)
        self.assertNotIn('name="r1"', body)

    def test_emitter_defaults_have_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('name="rb" value="1000"', body)
        self.assertIn('name="re" value="1"', body)
        self.assertNotIn('name="r1"', body)

    def test_error_keeps_submitted_values(self):
        form = {"mode": "fixed", "vcc": "99", "vbe": "0.70", "beta": "100",
                "rc": "2.2", "rb": "0", "r_unit": "k"}
        body = self.client.post("/calculate", data=form).get_data(as_text=True)
        self.assertIn('name="vcc" value="99"', body)
        self.assertIn('name="rb" value="0"', body)

    def test_unknown_mode_has_no_defaults(self):
        body = self.client.get("/?mode=mystery").get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertNotIn('name="vcc"', body)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web.DefaultFormTests -v`
Expected: FAIL เพราะช่องยังว่าง (`name="vcc" value=""`)

---

### Task 2: ใส่ default ใน route + เอกสาร (GREEN)

**Files:**
- Modify: `app.py`
- Modify: `README.md`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `DefaultFormTests` จาก Task 1
- Produces: `DEFAULT_FORMS` dict ที่ `index()` ใช้; ไม่มี interface ใหม่สำหรับโค้ดอื่น

- [ ] **Step 1: เพิ่ม `DEFAULT_FORMS` ใน `app.py`**

```
DEFAULT_FORMS = {
    "divider": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "r1": "100",
                "r2": "22", "re": "1", "beta": "100", "r_unit": "k"},
    "fixed": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
              "beta": "100", "r_unit": "k"},
    "emitter": {"vcc": "12", "vbe": "0.70", "rc": "2.2", "rb": "1000",
                "re": "1", "beta": "100", "r_unit": "k"},
}
```

`index()` เปลี่ยนบรรทัดที่ส่ง form เป็น `dict(DEFAULT_FORMS.get(mode, {}))`; ตรวจ mode ก่อนเหมือนเดิม; `calculate_bias()` ไม่แตะ

- [ ] **Step 2: รันเทสต์ใหม่ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web.DefaultFormTests -v`
Expected: OK (5 tests)

- [ ] **Step 3: รันชุดทั้งหมด**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK, 55 tests (50 เดิม + 5 ใหม่)

- [ ] **Step 4: อัปเดต README**

เพิ่มข้อความว่า Opening `/?mode=...` มีค่า default ตามโจทย์ให้แล้ว และ A4 เปลี่ยน RE เป็น 2 kΩ เอง

- [ ] **Step 5: ตรวจ browser และ commit/push**

รีสตาร์ท Flask แล้วเปิด `http://127.0.0.1:5000/?mode=emitter` ตรวจว่าช่องมีค่าและกด Calculate ได้ IC 1.026 mA / VCE 8.705 V; commit และ push เข่า branch เดิม; รายงาน commit SHA
