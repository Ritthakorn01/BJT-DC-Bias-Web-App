# BJT DC Bias Web App

เว็บแอปพลิเคชัน Flask สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT แบบ NPN Common Emitter สามโหมดไบอัส — **Voltage Divider**, **Fixed Bias** และ **Emitter Bias** (แหล่งจ่ายเดียว) ผลลัพธ์คำนวณจาก Python Backend ทุกครั้ง ไม่มีการฝังตัวเลขไว้ใน HTML และไม่มี JavaScript คำนวณผล

ENG29 2121 Computer Programming for Electrical Engineers · Lab 03

## การเลือกโหมด

เปิด <http://127.0.0.1:5000/> แล้วเลือกโหมดจาก dropdown **Bias Mode** กด **แสดงฟอร์มโหมดนี้** หน้าเว็บจะโหลดใหม่และแสดงเฉพาะช่องที่วงจรนั้นใช้ (ไม่ใช้ JavaScript)

| โหมด | URL | ช่องที่ใช้ |
|---|---|---|
| Voltage Divider | `/` หรือ `/?mode=divider` | `r1`, `r2`, `rc`, `re` |
| Fixed Bias | `/?mode=fixed` | `rb`, `rc` |
| Emitter Bias | `/?mode=emitter` | `rb`, `rc`, `re` |

ทุกโหมดใช้ `vcc`, `vbe`, `beta` และ `r_unit` (`k` = kΩ, ว่าง = Ω) ร่วมกัน

## แบบจำลองที่ใช้

Forward-Active Approximation โดยถือว่า β และ VBE คงที่:

```
Fixed    : IB = (VCC − VBE) / RB
Emitter  : IB = (VCC − VBE) / [RB + (β + 1)·RE]
Divider  : IB = (VTH − VBE) / [RTH + (β + 1)·RE]
           VTH = VCC · R2 / (R1 + R2)
           RTH = R1 · R2 / (R1 + R2)

IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE            (Fixed: VE = 0)
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

**ข้อจำกัด:** แบบจำลองนี้ใช้ได้เฉพาะ Forward Active ถ้า IB ≤ 0 (Cutoff) หรือ `VCE ≤ 0.2 V` (Saturation) ระบบจะแสดง region และคำเตือนว่าแบบจำลองใช้ไม่ได้ — ไม่ใช่ผลจาก SPICE และยังไม่มี AC / Transient / Load Line

## โครงสร้างโปรเจกต์

```
app.py                Flask app factory + routes และการเลือกโหมด
dc_bias.py            สมการ DC Bias สามโหมด, validation และ region warning (ไม่รู้จัก HTML)
templates/index.html  ฟอร์มเลือกโหมด ฟอร์มอินพุต และตารางผลลัพธ์ (Jinja2)
static/style.css      หน้าตาเว็บ (ไม่ใช้ CDN)
tests/test_dc_bias.py เทสต์วิศวกรรม
tests/test_web.py     เทสต์ HTTP ด้วย Flask test client
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

ผลปัจจุบัน: **50 tests, OK** (32 เทสต์วิศวกรรม + 18 เทสต์ HTTP)

## ค่าอ้างอิงสำหรับตรวจผล (A1–A5)

ใช้ร่วมกัน: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

| กรณี | โหมด / อินพุต | IB | IC | VCE | Region |
|---|---|---|---|---|---|
| A1 | Divider · R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 12.299 µA | 1.2299 mA | 8.0522 V | Forward Active |
| A2 | Fixed · RB=1 MΩ | 11.300 µA | 1.1300 mA | 9.5140 V | Forward Active |
| A3 | Emitter · RB=1 MΩ, RE=1 kΩ | 10.263 µA | 1.0263 mA | 8.7054 V | Forward Active |
| A4 | Emitter · RB=1 MΩ, RE=2 kΩ | 9.401 µA | 0.9401 mA | 8.0328 V | Forward Active |
| A5 | Fixed · RB=0 | — | — | — | error ที่ช่อง RB |

tolerance สำหรับตรวจหน้าเว็บ: IC ±0.01 mA, VCE ±0.02 V เทียบค่ามือที่ยังไม่ปัดเศษ

## การตรวจสอบข้อมูลนำเข้า

ระบบจะแจ้ง error และไม่คำนวณ เมื่อ

- ช่องที่โหมดนั้นใช้ ว่าง / ไม่ใช่ตัวเลข / ไม่เป็นจำนวนจำกัด
- `VCC ≤ 0`, ตัวต้านทานที่ใช้ ≤ 0, `β ≤ 0`, `VBE ≤ 0`
- หน่วยตัวต้านทานไม่ใช่ `k` หรือ `Ω`
- โหมดไม่รู้จัก

ถ้าอินพุตถูกต้องแต่ `VBE ≥ VCC` ระบบจะรายงาน **Cutoff** พร้อมคำเตือน (ไม่ใช่ input error)

เลือกหน่วยตัวต้านทาน (kΩ หรือ Ω) ได้จาก dropdown — ค่าตัวต้านทานของโหมดนั้นจะถูกแปลงเป็น Ω ก่อนคำนวณครั้งเดียว

## เอกสารเพิ่มเติม

- `docs/lab03-design.md` — design ของ Lab 03
- `docs/design-note.md` — design note เดิมของ Lab 02
- `docs/validation.md` — ผลตรวจสอบเทียบค่าอิสระ, test log และตาราง A1–A5
- `docs/reflection.md` — บันทึกสะท้อนคิด
- `.opencode/skills/browser-acceptance-check/SKILL.md` — ขั้นตอนตรวจรับผ่านเบราว์เซอร์
