# BJT DC Bias Web App

เว็บแอปพลิเคชัน Flask สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT แบบ NPN Common Emitter ที่ไบแอสด้วย Voltage Divider (R1–R2) — ผลลัพธ์คำนวณจาก Python Backend ทุกครั้ง ไม่มีการฝังตัวเลขไว้ใน HTML และไม่มี JavaScript คำนวณผล

ENG29 2121 Computer Programming for Electrical Engineers · Lab 02

## แบบจำลองที่ใช้

Forward-Active Approximation โดยถือว่า β และ VBE คงที่:

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

**ข้อจำกัด:** แบบจำลองนี้ใช้ได้เฉพาะ Forward Active เท่านั้น ถ้า `VTH ≤ VBE` วงจรจะรายงานว่า **Cutoff** และถ้า `VCE < 0.2 V` จะรายงานว่า **Saturation** พร้อมคำเตือนว่าแบบจำลองใช้ไม่ได้ — ไม่ใช่ผลจาก SPICE และไม่มี AC / Transient / Load Line ในเวอร์ชันนี้

## โครงสร้างโปรเจกต์

```
app.py              Flask app factory + routes (HTTP เท่านั้น)
dc_bias.py          สมการ DC Bias, validation และ region warning (ไม่รู้จัก HTML)
templates/index.html  ฟอร์มและตารางผลลัพธ์ (Jinja2)
static/style.css    หน้าตาเว็บ (ไม่ใช้ CDN)
tests/test_dc_bias.py  เทสต์วิศวกรรม
tests/test_web.py      เทสต์ HTTP ด้วย Flask test client
```

## การติดตั้ง

ต้องมี Python 3.10 ขึ้นไป (พัฒนาและทดสอบบน Python 3.15.2)

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## การรันเว็บ

```powershell
.venv\Scripts\python.exe -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

> ต้องเปิดผ่าน Local Web Server เท่านั้น การ double-click เปิด `templates/index.html` จะไม่ทำงาน เพราะไม่มี Python มาคำนวณ

## การรันเทสต์

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลปัจจุบัน: **20 tests, OK** (13 เทสต์วิศวกรรม + 7 เทสต์ HTTP)

## ค่าอ้างอิงสำหรับตรวจผล

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

| ปริมาณ | ค่าที่ควรได้ |
|---|---|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.299 µA |
| IC | 1.2299 mA |
| IE | 1.2422 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| Region | Forward Active |

## การตรวจสอบข้อมูลนำเข้า

ระบบจะแจ้ง error และไม่คำนวณ เมื่อ `VCC ≤ 0`, `R1/R2/RC/RE ≤ 0`, `β ≤ 0`, `VBE ≤ 0` หรือ `VBE ≥ VCC` หรือช่องใดไม่ใช่ตัวเลข (รับ comma คั่นหลักพันได้ เช่น `1,000`)

เลือกหน่วยตัวต้านทาน (kΩ หรือ Ω) ได้จาก dropdown — ค่าทั้งสี่ตัวจะถูกแปลงเป็น Ω ก่อนคำนวณ

## เอกสารเพิ่มเติม

- `docs/design-note.md` — design ที่อนุมัติแล้ว
- `docs/validation.md` — ผลตรวจสอบเทียบค่าอิสระและ test log
- `docs/reflection.md` — บันทึกสะท้อนคิด
