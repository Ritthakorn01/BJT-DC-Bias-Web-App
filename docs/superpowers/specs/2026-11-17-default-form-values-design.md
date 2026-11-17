# Design — ค่าเริ่มต้นของฟอร์มตามโจทย์ Lab 03

**วันที่:** 17 พฤศจิกายน 2569
**สถานะ:** อนุมัติแล้ว

## Intent / ทำไม
ผู้ใช้ต้องการเปิดเว็บแล้วเห็นช่องกรอกที่มีค่าตามโจทย์ Lab 03 อยู่แล้ว เพื่อกด Calculate ได้ทันทีโดยไม่ต้องพิมพ์ซ้ำทุกครั้ง

## Goals
- `GET /?mode=divider|fixed|emitter` แสดงค่าตามโจทย์ในทุกช่องของโหมดนั้นทันที
- ค่าที่ผู้ใช้ส่งมาและเกิด error ยังคงอยู่เหมือนเดิม (ไม่ถูก default ทับ)
- ไม่ใช้ JavaScript และไม่ย้ายสมการ/ตัวเลขไปไว้ใน template

## Non-goals / Anti-goals
- ไม่เปลี่ยนสมการ หน่วย ภายใน หรือผลลัพธ์ของทั้งสามโหมด
- ไม่เปลี่ยนพฤติกรรม `POST /calculate`, error box, warning หรือ region
- ไม่เพิ่ม dependency หรือ UI framework

## Constraints
- โปรเจกต์เป็น Flask server-rendered; `app.py` ส่ง `form` dict ให้ template, template อ่านด้วย `form.get(...)`
- ปัจจุบัน `GET /` ส่ง `{"r_unit": "k"}`; template มี default เฉพาะ VBE `0.70` และหน่วย `k`
- ข้อความ error เป็นภาษาไทย; ศัพท์วิศวกรรมคงอังกฤษ
- A4 ต้องยังเปลี่ยน RE จาก 1 เป็น 2 kΩ ได้ด้วยมือ (default เป็น 1 ตาม A3)

## Approaches
1. **เลือก: ใส่ default ใน `app.py` ตอน GET ตามโหมด** — ค่าอยู่แหล่งเดียวกับที่ render ฟอร์ม, ไม่ใช้ JS, POST ไม่เปลี่ยน; ต้องดูแล dict เพิ่มเติมหนึ่งตัว
2. เขียน `value="..."` ลงใน template — ต้องแยกตามโหมดใน HTML และตัวเลขอยู่สองที่ (route + template) เสี่ยงไม่ตรงกัน
3. ใช้ `placeholder` — ช่องยังว่าง ไม่แก้ปัญหาที่ผู้ใช้บอก

## Design ที่ตกลง
- เพิ่ม `DEFAULT_FORMS` ใน `app.py`:
  - ร่วม: `vcc="12"`, `vbe="0.70"`, `rc="2.2"`, `beta="100"`, `r_unit="k"`
  - divider: `r1="100"`, `r2="22"`, `re="1"`
  - fixed: `rb="1000"`
  - emitter: `rb="1000"`, `re="1"`
- `index()` ใช้ `dict(DEFAULT_FORMS.get(mode, {}))` (โหมดไม่รู้จักยังได้ error เหมือนเดิมและไม่ render ช่องคำนวณ)
- `calculate_bias()` ไม่เปลี่ยน: ตอน error ยังส่ง `form` ที่ผู้ใช้กรอกกลับไป
- เทสต์: `GET /` และ `GET /?mode=fixed|emitter` มีค่าครบตามโหมด; ไม่มีช่องของโหมดอื่น; `POST` error ยังคงค่าที่ส่ง; โหมดไม่รู้จักยัง error
- เอกสาร: README กล่าวถึงค่า default; `docs/validation.md` ไม่ต้องเปลี่ยนผล A1–A5 เพราะค่า/สมการเหมือนเดิม
