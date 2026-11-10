# Lab 02 — BJT DC Bias Web App · Design Note

**รายวิชา:** ENG29 2121 Computer Programming for Electrical Engineers (2/2569)
**วันที่:** 10 พฤศจิกายน 2569
**Repo:** `https://github.com/Ritthakorn01/BJT-DC-Bias-Web-App`
**สถานะ:** รออนุมัติ Design (ยังไม่เริ่มเขียนโค้ด)

---

## 1. Intent และเหตุผล

สร้าง Web Application จริงที่ทำงานบน Local Web Server เพื่อให้นักศึกษาเห็นครบว่าค่าที่กรอกใน Browser ถูกส่งไปคำนวณที่ Python Backend แล้วสะท้อนกลับมาเป็นผลลัพธ์ทางวิศวกรรม ไม่ใช่ตัวเลขที่ฝังไว้ใน HTML

คุณค่าของชิ้นงานนี้ไม่ใช่แค่ "เว็บคำนวณได้" แต่คือการแยกความรับผิดชอบให้ชัด: สมการอยู่ในโมดูลวิศวกรรม, HTTP routing อยู่ใน Flask, การแสดงผลอยู่ใน template และคุณภาพถูกรับประกันด้วย automated tests — ซึ่งเป็นโครงเดียวกับที่จะต่อยอดเป็น Virtual Transistor Laboratory ในสัปดาห์ถัดไป

**ผู้ใช้:** นักศึกษา/ผู้สอนที่ต้องการตรวจ DC Operating Point ของวงจร Voltage-Divider Bias อย่างรวดเร็ว พร้อมรู้ว่าผลนั้นเชื่อถือได้หรือไม่ภายใต้สมมติฐาน Forward-Active

---

## 2. Goals

- G1 · เปิด `http://127.0.0.1:5000/` แล้วเห็นฟอร์มกรอกค่าได้ (HTTP 200)
- G2 · กรอก `VCC, R1, R2, RC, RE, β, VBE` แล้วกด **Calculate DC Bias** → Python คำนวณและแสดง `VB, VE, VC, VCE, IC` พร้อม `IB, IE` และหน่วยกำกับ
- G3 · ผลตรงกับการคำนวณอิสระภายใต้แบบจำลองเดียวกัน (tolerance 0.01)
- G4 · ข้อมูลไม่ถูกต้อง → ข้อความ error ที่อ่านรู้เรื่อง และหน้าเว็บไม่ล้ม
- G5 · นอก Forward-Active → warning ระบุว่า approximation ใช้ไม่ได้ พร้อมบอกว่าอยู่ใน region ใด
- G6 · มี automated tests: engineering ≥ 3 ตัว และ Flask test client ≥ 1 ตัว
- G7 · clone repo แล้วทำตาม README แล้วรันเว็บและรัน tests ได้

## 3. Non-goals (Lab 2 เท่านั้น)

- ไม่ทำ AC small-signal, Bode plot, Transient, Signal Generator
- ไม่ทำ Bias type อื่น (Fixed, Emitter) — อยู่ใน W3
- ไม่ทำ SPICE/ngspice, DC Load Line — อยู่ใน W4
- ไม่ทำ Interactive schematic, Animation, Export
- ไม่มี authentication, database, deployment ขึ้น cloud

## 4. Anti-goals (ทำงานได้แต่ถือว่าล้มเหลว)

- ผลลัพธ์ hardcode ใน HTML หรือคำนวณด้วย JavaScript ฝั่ง client
- เปิดผลลัพธ์ได้เฉพาะตอนเปิดด้วย `file://` หรือต้องพึ่ง CDN/อินเทอร์เน็ต
- แสดงตัวเลขใน region ที่แบบจำลองใช้ไม่ได้ โดยไม่มี warning
- test ที่ผ่านเพราะ assert ค่าที่ตัวเองสร้างขึ้น หรือไม่ได้รันจริง
- commit `.venv/`, credential หรือ API key

## 5. Constraints

- **เวลา:** ต้องจบในคาบ 180 นาที (Build window 75 นาที)
- **Toolchain ที่มีจริงในเครื่อง:** OpenCode v2.2.6 + Superpowers (active), Python 3.15.2, pip 26.2.2, Git 2.56.0
- **ทดสอบมาตรฐาน:** ใช้ `unittest` จาก standard library เพื่อให้ตรงกับคำสั่งในใบงาน `python -m unittest discover -s tests -v` และไม่เพิ่ม dependency
- **Flask:** pin `Flask>=3.1,<4` และต้องรันได้จริงบน Python 3.15 (จะตรวจด้วย venv ก่อนสรุป)
- **Offline-friendly:** CSS เขียนเอง ไม่ใช้ CDN

---

## 6. Approaches ที่พิจารณา

| ทาง | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| A | `app = Flask(__name__)` ระดับ module + `dc_bias.py` | เขียนน้อย เร็วที่สุด | W3 ต้องรื้อโครงเมื่อเพิ่ม bias type |
| **B (เลือก)** | `create_app()` factory + service layer, `dc_bias.py` คืน object พร้อม `warnings[]` | แยกเทสต์วิศวกรรม/HTTP ได้สะอาด, ต่อยอด W3 ได้ทันที | งานเพิ่ม 5–10 นาที |
| C | B + blueprint + dataclass model เต็มรูปแบบ | โครงสวยที่สุด | เกินจำเป็น เสี่ยงไม่จบในคาบ |

**เลือก B** เพราะเกณฑ์ A6 ต้องการเทสต์สองชั้นอยู่แล้ว การมี factory ทำให้สร้าง app ด้วย config ต่าง ๆ ในเทสต์ได้โดยไม่ชน state และการให้ `dc_bias.py` คืน `warnings` ทำให้ route ทำหน้าที่แค่ map ข้อมูล ไม่มี logic ทางวิศวกรรมปนอยู่

---

## 7. โครงสร้างไฟล์

```
BJT DC Bias Web App/
├── app.py                  # create_app(), routes GET / และ POST /calculate
├── dc_bias.py              # สมการ DC Bias + validation + region warnings (ไม่รู้จัก HTML/HTTP)
├── requirements.txt        # Flask>=3.1,<4
├── README.md               # วิธีติดตั้ง/รัน/ทดสอบ + ค่าอ้างอิง
├── AGENTS.md               # convention สำหรับ AI coding
├── .gitignore              # .venv/, __pycache__/, *.pyc, .env
├── templates/
│   └── index.html          # ฟอร์ม + ตารางผลลัพธ์ (Jinja) ไม่มีสมการฟิสิกส์
├── static/
│   └── style.css           # responsive, ไม่ใช้ CDN
├── tests/
│   ├── test_dc_bias.py     # engineering math, validation, warnings
│   └── test_web.py         # Flask test client
└── docs/
    ├── design-note.md      # เอกสารนี้
    ├── validation.md       # ผลตรวจเทียบค่าอิสระ + test log
    └── reflection.md       # บันทึกสะท้อนคิด (นักศึกษาเติมเอง)
```

## 8. Data flow

```
Browser (GET /)            → Flask คืน index.html (ฟอร์มว่าง)
Browser (POST /calculate)  → Flask อ่านฟอร์ม → validate
                           → dc_bias.calculate(...) คืนผล + warnings
                           → Jinja render index.html พร้อมผลลัพธ์ (HTTP 200)
ข้อมูลผิด                 → render ฟอร์มเดิม + error box (HTTP 200, ไม่ใช่ 500)
```

ไม่มี JavaScript คำนวณ และไม่มี API JSON ใน Lab นี้ — ทุกอย่างเป็น server-rendered form post ตามที่ใบงานกำหนด

---

## 9. แบบจำลองวิศวกรรม

Forward-Active approximation, β และ VBE คงที่:

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

**ค่าอ้างอิง (คำนวณด้วยมือ, VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V):**

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.299 µA |
| IC | 1.2299 mA |
| IE | 1.2422 mA |
| VE | 1.2422 V |
| VB | 1.9422 V |
| VC | 9.2943 V |
| VCE | 8.0522 V |
| Region | Forward Active |

ค่าเหล่านี้จะถูก hardcode **ในเทสต์เท่านั้น** (เป็น expected value ที่มาจากการคำนวณมือ) ไม่ปรากฏใน `app.py`, template หรือ `dc_bias.py`

## 10. Validation และ Warning rules

**Error (ปฏิเสธการคำนวณ, แสดง error box):**

| เงื่อนไข | ข้อความ |
|---|---|
| ค่าว่าง / ไม่ใช่ตัวเลข | "กรุณากรอกตัวเลขให้ครบทุกช่อง" |
| `VCC ≤ 0` | "VCC ต้องมากกว่า 0 V" |
| `R1, R2, RC, RE ≤ 0` | "ค่าความต้านทานต้องมากกว่า 0 Ω" |
| `β ≤ 0` | "β ต้องมากกว่า 0" |
| `VBE ≤ 0` หรือ `VBE ≥ VCC` | "VBE ต้องอยู่ระหว่าง 0 กับ VCC" |

**Warning (ยังคำนวณและแสดงผล แต่ต้องเตือน):**

| เงื่อนไข | ข้อความ |
|---|---|
| `VTH ≤ VBE` | "วงจรอยู่ในช่วง Cutoff — IB ≤ 0 และแบบจำลอง Forward-Active ใช้ไม่ได้" |
| `VCE < 0.2 V` | "VCE ต่ำกว่า VCE(sat) ≈ 0.2 V — วงจรอยู่ใน Saturation และแบบจำลอง Forward-Active ใช้ไม่ได้" |
| `VC < 0` | "VC ติดลบ แสดงว่า RC ใหญ่เกินกว่าที่วงจรจะอยู่ใน Active Region" |

**กฎการตัดสิน region (single source of truth ใน `dc_bias.py`):**

```
ถ้า VTH ≤ VBE          → "Cutoff"      (ไม่คำนวณ IB/IC ต่อ, IB = 0)
มิฉะนั้นถ้า VCE < 0.2   → "Saturation"  (แสดงทั้งข้อความ VCE และ VC<0 เมื่อเข้าเงื่อนไขทั้งคู่)
มิฉะนั้น               → "Forward Active"
```

`VC < 0` ไม่มีสถานะแยก: ตามสมการ VCE = VCC − IC·RC − IE·RE ค่า `VC < 0` ย่อมหมายถึง `VCE < 0.2` อยู่แล้ว จึงรายงานเป็น `Saturation` พร้อม warning สองข้อ (ไม่ใช่สถานะที่สาม) — ไม่มีสถานะ `ไม่ทราบแน่ชัด` ในระบบ

เมื่อ region ไม่ใช่ Forward Active หน้าจอต้องแสดง badge ตาม region จริง และต้องไม่กล่าวอ้างว่าเป็นผลจำลองที่แม่นยำ

## 11. UI (ข้อความจำลองหน้าจอ)

```
┌─ BJT DC Bias Calculator ─────────────────────────────┐
│ Voltage-Divider Bias · NPN Common Emitter            │
│                                                      │
│ VCC [ 12 ] V                    VBE [ 0.70 ] V       │
│ R1  [ 100 ] R2 [ 22 ] RC [ 2.2 ] RE [ 1 ]            │
│ หน่วยตัวต้านทาน: (•) kΩ  ( ) Ω                       │
│ β   [ 100 ]                                          │
│                                    [ Calculate DC Bias ]│
├─ DC Bias Results ────────────────────────────────────┤
│ VB 1.942 V │ VE 1.242 V │ VC 9.294 V                 │
│ VCE 8.052 V │ IC 1.230 mA │ IB 12.30 µA │ IE 1.242 mA│
│ Region: [ Forward Active ]                           │
└──────────────────────────────────────────────────────┘
```

- ภาษาไทยเป็นหลัก ศัพท์วิศวกรรมคงเป็นอังกฤษ (VCC, VCE, β)
- ค่าที่ผู้ใช้กรอกต้องคงอยู่ในฟอร์มหลัง submit (ทั้งกรณีสำเร็จและ error)
- Responsive: ตารางผลลัพธ์ยุบเป็นคอลัมน์เดียวบนจอแคบ

## 12. สิ่งที่ผมตัดสินใจเอง (ตรวจได้ระหว่างอ่าน)

1. **unittest แทน pytest** — ตรงกับคำสั่งในใบงาน, ไม่เพิ่ม dependency
2. **ตัวเลือกหน่วยตัวต้านทาน Ω/kΩ ระดับฟอร์ม (ค่าเริ่มต้น kΩ)** — ทำให้ข้อกำหนด "แปลง kΩ เป็น Ω ให้สอดคล้อง" จับต้องได้จริง โดยไม่ต้องมี dropdown 4 ตัว
3. **เกณฑ์ Saturation ใช้ VCE < 0.2 V** และเพิ่มเงื่อนไข `VC < 0` เป็น warning เสริม
4. **POST ไปที่ `/calculate`** และ render กลับที่ template เดียวกัน (ตามตัวเลือกในใบงาน A2)
5. **ไม่มี JavaScript** — ลดจุดที่ทำให้ผลไม่ตรงกับ backend
6. **Error ตอบ HTTP 200 พร้อม error box** ไม่ใช้ 400/500 เพื่อให้หน้าเว็บยังใช้งานต่อได้และเทสต์ง่าย
7. **`VC < 0` ไม่ใช่ region ที่สาม** — รายงานเป็น Saturation พร้อม warning สองข้อ (ตัดสถานะ `ไม่ทราบแน่ชัด` ออก)
8. **tolerance ±0.01 ในหน่วยที่แสดงผล** (V / mA / µA) ไม่ใช่หน่วย SI

## 13. เกณฑ์ตรวจรับ A1–A7 (สัญญาที่ใช้ตัดสินงาน)

เอกสารนี้เป็นสัญญาหลัก ไม่มีข้อกำหนดภายนอกเพิ่มเติมเรื่องชื่อ field, ชื่อไฟล์, ข้อความ error แบบตายตัว หรือรูปแบบ log ของ `docs/validation.md` — ค่าคงที่ทั้งหมดมาจากเอกสารนี้

| # | เกณฑ์ | สิ่งที่พิสูจน์ |
|---|---|---|
| A1 | `GET /` | HTTP 200 และเห็นฟอร์ม |
| A2 | `POST /calculate` | ค่าที่แสดงมาจาก Python ไม่ใช่ค่าคงที่ใน HTML |
| A3 | Engineering reference | ผลตรงกับ §9 ภายใน tolerance |
| A4 | Validation | R≤0, β≤0, ค่าไม่ใช่ตัวเลข → error ชัดเจน ไม่ล้ม |
| A5 | Outside Active Region | Cutoff / Saturation มี warning |
| A6 | Unit + HTTP tests | ≥ 3 engineering tests + ≥ 1 Flask client test |
| A7 | Reproducibility | clone → install → run → test ตาม README ได้ |

## 14. แผนการทดสอบ

**นิยาม tolerance:** เปรียบเทียบในหน่วยที่แสดงผล (V สำหรับแรงดัน, mA สำหรับ IC/IE, µA สำหรับ IB) ด้วย absolute tolerance **0.01** ต่อค่า — ค่าคาดหวังในเทสต์เป็นค่าคงที่ที่คำนวณมือจาก §9 ไม่ได้เรียกฟังก์ชันที่กำลังทดสอบมาสร้างค่าคาดหวัง

| Test | ชนิด | ตรวจอะไร |
|---|---|---|
| T1 | unit | ค่าอ้างอิงทั้งชุดตรง ±0.01 (VB, VE, VC, VCE, IC, IB, IE) |
| T2 | unit | `R = 0` → ValidationError |
| T3 | unit | `β = 0` → ValidationError |
| T4 | unit | ค่าไม่ใช่ตัวเลข → ValidationError |
| T5 | unit | VTH ≤ VBE → warning Cutoff, region = "Cutoff" |
| T6 | unit | RC ใหญ่ (VC < 0) → region = "Saturation", มี warning 2 ข้อ |
| T7 | Flask client | `GET /` → 200 และมีฟอร์ม |
| T8 | Flask client | `POST /calculate` ค่าอ้างอิง → 200 และ HTML มี 9.294 / 8.052 |
| T9 | Flask client | `POST /calculate` ค่า invalid → 200, มีข้อความ error, ไม่ crash |

จะรันจริงทุกตัวและบันทึกผลลง `docs/validation.md`

---

## 15. ความเสี่ยงและทางรับมือ

| ความเสี่ยง | ทางรับมือ |
|---|---|
| Flask รุ่นที่ติดตั้งไม่รองรับ Python 3.15 | ทดสอบใน venv ก่อนสรุป และ pin ช่วงเวอร์ชันที่ผ่านจริง |
| ตัวเลขทศนิยมต่างจากที่คำนวณมือเล็กน้อย | ใช้ tolerance 0.01 และจัดรูปแบบ 3 ตำแหน่งทศนิยม |
| เวลาออกแบบกินเวลา Build | Build window 75 นาที, งานทั้งหมดแยกเป็น task ย่อยในแผน |
| push ขึ้น GitHub ต้องใช้ credential ของนักศึกษา | commit ในเครื่องให้ครบ แล้วให้นักศึกษาเป็นผู้สั่ง push |
