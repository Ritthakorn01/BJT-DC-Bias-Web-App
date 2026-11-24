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

เปิดด้วย `?mode=` เพื่อเลือกโหมด เช่น <http://127.0.0.1:5000/?mode=emitter> — ฟอร์มแต่ละโหมดมี **ค่าเริ่มต้นตามโจทย์ Lab 03 ใส่ไว้ให้แล้ว** (VCC 12 V, RC 2.2 kΩ, β 100, VBE 0.70 V, หน่วย kΩ; Divider R1 100 / R2 22 / RE 1 kΩ; Fixed RB 1000 kΩ; Emitter RB 1000 / RE 1 kΩ) กด **Calculate DC Bias** ได้ทันที กรณี A4 ให้เปลี่ยน RE จาก 1 เป็น 2 kΩ เองก่อนกด ค่าที่กรอกแล้วเกิด error จะยังคงอยู่ ไม่ถูกค่าเริ่มต้นทับ

## การรันเทสต์

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลปัจจุบัน: **90 tests, OK** (55 เทสต์ Lab 03 + 35 เทสต์ Lab 04 รวม integration กับ ngspice จริง)

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

## Lab 04 — CE Amplifier Simulator (ngspice)

เลือกโหมด **CE Amplifier (SPICE)** ใน dropdown เดิมแล้วกด **แสดงฟอร์มโหมดนี้** ฟอร์มแบ่งเป็น DC Bias / AC Coupling / Input Source / Model & Units แล้วกด **Calculate DC Bias** เพื่อรัน `.op`, `.ac` และ `.tran` ด้วย ngspice หน้าผลแสดงจุดทำงานจาก SPICE เทียบการคำนวณมือ กราฟ Bode magnitude/phase และ waveform แบบ transient (PNG ที่สร้างจากข้อมูลจริงแล้วฝังเป็น base64 ไม่มี JavaScript ในแอป)

### ติดตั้งและตรวจ ngspice

ในเครื่องที่ใช้ตรวจรับ ngspice 47 อยู่ที่:

```powershell
C:\Users\B6807153\ngspice\bin\ngspice.exe --version
# ** ngspice-47 : Circuit level simulation program
```

ถ้าเปิด Flask จาก PowerShell อีกชุด ให้เพิ่มไดเรกทอรี `bin` เข้า PATH ก่อน (หรือตั้ง `NGSPICE_BIN` เป็น path เต็มก็ได้):

```powershell
$env:PATH += ';C:\Users\B6807153\ngspice\bin'
$env:SPICE_LIB_DIR = 'C:\Users\B6807153\ngspice\share\ngspice'
.venv\Scripts\python.exe -m flask --app app run --port 5000
```

`SPICE_LIB_DIR` ไม่ได้ถูกอ่านโดยโค้ดของแอป — netlist ใช้ `.include model.lib` และโค้ดคัดลอกไฟล์โมเดลเข้า temp dir ทุกครั้งที่รัน จึงตั้งค่านี้เฉพาะกรณี ngspice แบบพกพาต้องการตำแหน่ง library เพิ่มเติม (ค่าในเครื่องนี้แสดงไว้ข้างบน)

### ตัวแปรสภาพแวดล้อม

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `NGSPICE_BIN` | `ngspice` | ชื่อ/พาธของ binary ที่จะเรียก ถ้าไม่มีจะแสดง error ว่า "ไม่พบ ngspice ในเครื่องนี้ กรุณาติดตั้งและเพิ่มเข้า PATH" |
| `SPICE_MODEL_PATH` | `spice/models/2n3904.lib` | ไฟล์โมเดลที่คัดลอกเข้า temp dir ก่อนรัน |

ตัวอย่างการ override:

```powershell
$env:NGSPICE_BIN = 'C:\Users\B6807153\ngspice\bin\ngspice.exe'
$env:SPICE_MODEL_PATH = 'C:\Users\B6807153\Documents\GitHub\BJT DC Bias Web App\spice\models\2n3904.lib'
```

> **คำเตือน:** `spice/models/2n3904.lib` เป็น **placeholder ที่เลือกใช้เอง ไม่ใช่ fixture จากอาจารย์** ค่า BF ของโมเดลประมาณ 416 ขณะที่ β ในฟอร์มคือ 100 จึงเป็นเรื่องปกติที่ SPICE กับการคำนวณมือจะต่างกันหลายเปอร์เซ็นต์ (หน้าผลแสดง % ผลต่างและจะเตือนถ้าเกิน 15%) อย่านำตัวเลข SPICE ไปเทียบกับคำตอบของอาจารย์โดยไม่ระบุโมเดลที่ใช้

หลักฐานการตรวจรับ B1–B8 อยู่ใน `docs/validation.md` ส่วนที่ 8 และ screenshot ที่ `docs/screenshots/lab04-desktop.png` / `lab04-mobile.png`

## ข้อมูลสำหรับส่งงาน (Lab 03)

- GitHub repository: <https://github.com/Ritthakorn01/BJT-DC-Bias-Web-App>
- Pull Request: <https://github.com/Ritthakorn01/BJT-DC-Bias-Web-App/pull/1>
- Commit SHA ของงาน Lab 03: `91c022f` (branch `feat/lab03-bias-modes`)
- วิธีรัน/เปิดเว็บ/รันเทสต์: อยู่ในหัวข้อ **การติดตั้ง**, **การรันเว็บ** และ **การรันเทสต์** ด้านบน

| ส่วน | AI สร้าง/ช่วย | สิ่งที่ตรวจแล้ว |
|---|---|---|
| โค้ด | `dc_bias.py` (สมการสามโหมด + validation), `app.py` (เลือกโหมด/แปลงหน่วย), `templates/index.html` | ทดสอบ unit/HTTP 50 ตัว และเทียบค่ามือ A1–A5 |
| เอกสาร | design, validation log, README, screenshot หลักฐาน | ทวนตาราง A1–A5 กับค่าที่เห็นในเบราว์เซอร์จริง |
| ตำแหน่งสำคัญ | เลือกฟังก์ชัน: `app.py` บรรทัด 62–79 · แปลง kΩ→Ω: `app.py` บรรทัด 55 · สมการ: `dc_bias.py` บรรทัด 157–220 | ตรวจว่า kΩ ถูกคูณครั้งเดียว และ Divider ให้ผลเดิมทุกหลัก |

## เอกสารเพิ่มเติม

- `docs/lab03-design.md` — design ของ Lab 03
- `docs/design-note.md` — design note เดิมของ Lab 02
- `docs/validation.md` — ผลตรวจสอบเทียบค่าอิสระ, test log และตาราง A1–A5
- `docs/reflection.md` — บันทึกสะท้อนคิด
- `.opencode/skills/browser-acceptance-check/SKILL.md` — ขั้นตอนตรวจรับผ่านเบราว์เซอร์
