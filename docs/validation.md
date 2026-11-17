# Validation Log — BJT DC Bias Web App

วันที่ตรวจ: 17 พฤศจิกายน 2569
เครื่องที่ใช้: Windows 11, Python 3.15.2, Flask 3.1.3
คำสั่งที่ใช้รันเทสต์:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลลัพธ์: **Ran 50 tests — OK** (32 เทสต์วิศวกรรม + 18 เทสต์ HTTP)

## 1. Automated tests

| กลุ่ม | จำนวน | ตรวจอะไร |
|---|---|---|
| `test_dc_bias.ReferencePointTests` | 4 | ค่า VB, VE, VC, VCE, IC, IE, IB ของ Divider ตรงกับการคำนวณมือ ±0.01 และกรณี β สูงมาก |
| `test_dc_bias.FixedBiasTests` | 2 | Fixed Bias (A2) และ Cutoff เมื่อ VBE ≥ VCC |
| `test_dc_bias.EmitterBiasTests` | 3 | Emitter Bias (A3), RE ใหญ่ขึ้นทำให้ IC ลด (A4), Cutoff |
| `test_dc_bias.ResultDictTests` | 2 | คีย์/หน่วยของ `BiasResult.to_dict()` และ alias `calculate` |
| `test_dc_bias.CalculatorInputTests` | 4 | ฟังก์ชันคำนวณเรียกตรงด้วย RB/R1 = 0 หรือติดลบต้องได้ `ValidationError` ไม่ใช่ traceback/ผลติดลบ |
| `test_dc_bias.InputParsingTests` | 5 | รับช่องว่างและ comma คั่นหลักพัน, ปฏิเสธค่าว่าง/ไม่ใช่ตัวเลข/ค่าไม่จำกัด |
| `test_dc_bias.ValidationTests` | 3 | ปฏิเสธ R ≤ 0, β ≤ 0, และยอมให้ VBE ≥ VCC ไปเตือนที่ชั้นแบบจำลอง |
| `test_dc_bias.ModeValidationTests` | 4 | แยก `validate_common` กับ `validate_resistors` ให้ใช้ได้รายโหมด |
| `test_dc_bias.RegionThresholdTests` | 2 | ขอบเขต Saturation ใช้ `VCE ≤ 0.2 V` |
| `test_dc_bias.RegionTests` | 3 | Cutoff, Saturation, Forward Active |
| `test_web.WebIndexTests` | 1 | `GET /` → 200 และมีฟอร์ม |
| `test_web.CalculateRouteTests` | 8 | ผลลัพธ์จาก server, error, หน่วย kΩ/Ω, ค่าสุดขั้ว, หน่วยไม่รู้จัก, UTF-8 |
| `test_web.ModeCalculateTests` | 5 | POST แต่ละโหมด, โหมดไม่รู้จัก, RB = 0 ระบุชื่อช่อง |
| `test_web.ModeSelectionTests` | 4 | `GET /?mode=` แสดงเฉพาะช่องของโหมด และโหมดไม่รู้จักเป็น error |

## 2. เทียบค่าจากเว็บกับการคำนวณมือ (Divider — A1 ของ Lab 03)

ข้อมูลนำเข้า: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

| ปริมาณ | คำนวณมือ | ค่าที่เว็บแสดง | ต่าง |
|---|---|---|---|
| VB | 1.942 V | 1.942 V | 0.000 |
| VE | 1.242 V | 1.242 V | 0.000 |
| VC | 9.294 V | 9.294 V | 0.000 |
| VCE | 8.052 V | 8.052 V | 0.000 |
| IC | 1.230 mA | 1.230 mA | 0.000 |
| IB | 12.299 µA | 12.299 µA | 0.000 |
| IE | 1.242 mA | 1.242 mA | 0.000 |
| Region | Forward Active | Forward Active | ตรง |

## 3. ตรวจรับ Lab 02 (HTTP, A1–A7)

รันเซิร์ฟเวอร์ด้วย `.venv\Scripts\python.exe -m flask --app app run --port 5000` แล้วยิง HTTP request จริง

| # | เกณฑ์ | หลักฐาน | ผล |
|---|---|---|---|
| A1 | `GET /` | HTTP 200, พบ `Calculate DC Bias`, มี field `vcc`, `r1`, charset=utf-8 | ผ่าน |
| A2 | `POST /calculate` | HTTP 200, region=Forward Active, VB=1.942 (ค่ามาจาก Python) | ผ่าน |
| A3 | Engineering reference | ตารางข้อ 2 ต่าง 0.000 ทุกค่า | ผ่าน |
| A4 | Validation | `r1=0` → HTTP 200 + กล่อง "ไม่สามารถคำนวณได้", ไม่มี Traceback | ผ่าน |
| A5 | Outside active region | `r2=1 kΩ` → region=Cutoff + warning; `rc=50 kΩ` → region=Saturation + warning 2 ข้อ | ผ่าน |
| A6 | Unit + HTTP tests | 13 engineering tests + 7 HTTP tests (รวม 20) | ผ่าน |
| A7 | Reproducibility | README มีขั้นตอนติดตั้ง/รัน/ทดสอบครบ, dependency มีเพียง Flask | ผ่าน |

### หลักฐาน HTTP (ยิงจริง)

```
reference  -> HTTP 200 | region=Forward Active | VB=1.942 | error=False | warning=False
r1_zero    -> HTTP 200 | error=True
cutoff     -> HTTP 200 | region=Cutoff | VB=0.119 | warning=True
saturation -> HTTP 200 | region=Saturation | warning=True
ohm_unit   -> HTTP 200 | region=Forward Active | VB=1.942 (ให้ผลตรงกับกรอกหน่วย kΩ)
```

## 4. ตรวจรับ Lab 03 (A1–A5) ผ่านเบราว์เซอร์จริง

- วิธีที่ใช้จริง: **OpenCode Browser** (Chromium ใน OpenCode desktop app) — ไม่ใช่ Playwright MCP
- `opencode.json` ตั้ง Playwright MCP ไว้แล้ว แต่ MCP server จะถูกโหลดตอนเริ่ม session จึงต้องรีสตาร์ท OpenCode ก่อนใช้; session ที่ตรวจนี้ยังไม่เห็นเครื่องมือ Playwright
- เบราว์เซอร์คุยกับ Flask dev server ที่ `http://127.0.0.1:5000/` โดยตรง
- การสลับโหมดทำผ่าน dropdown **Bias Mode** + ปุ่ม **แสดงฟอร์มโหมดนี้** (`GET /?mode=...`) ไม่มี JavaScript คำนวณผล
- ค่าที่กรอกร่วม: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V, หน่วย kΩ
- เกณฑ์ผ่าน: IC ±0.01 mA และ VCE ±0.02 V เทียบค่ามือ

### ตารางทดสอบ A1–A5 ตามหัวข้อ 06 / Browser acceptance ของใบงาน

| กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| A1 · โหมดเดิม | Divider · R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ; ร่วมกับ VCC 12 V, RC 2.2 kΩ, β 100, VBE 0.70 V | ผลต้องตรงกับ Lab 2 ก่อนแก้ และค่าอ้างอิงเดิม **IC 1.2299 mA · VCE 8.0522 V** | IC **1.230 mA** · VCE **8.052 V** · VB 1.942 V · VE 1.242 V · VC 9.294 V · IB 12.299 µA · IE 1.242 mA · Forward Active (ต่างจากค่ามือ 0.0001 mA / 0.0002 V) | OpenCode Browser | ผ่าน |
| A2 · Fixed | Fixed · RB = 1 MΩ (ไม่กรอก RE; ฟอร์มต้องไม่มีช่อง RE) | คำนวณได้โดยไม่ต้องกรอก RE **IC 1.1300 mA · VCE 9.5140 V** | IC **1.130 mA** · VCE **9.514 V** · VB 0.700 V · VE 0.000 V · IB 11.300 µA · IE 1.141 mA · Forward Active | OpenCode Browser | ผ่าน |
| A3 · Emitter | Emitter · RB = 1 MΩ, RE = 1 kΩ | มีช่องและใช้ค่า RE **IC 1.0263 mA · VCE 8.7054 V** | IC **1.026 mA** · VCE **8.705 V** · VB 1.737 V · VE 1.037 V · VC 9.742 V · IB 10.263 µA · IE 1.037 mA · Forward Active | OpenCode Browser | ผ่าน |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่เปลี่ยน RE เป็น 2 kΩ | ทำนายก่อนรันว่า **IC จะลดจาก A3** เพราะตัวหาร RB + (β+1)·RE เพิ่มขึ้น → IB ลด; ค่ามือ **IC 0.9401 mA · VCE 8.0328 V** | IC **0.940 mA** · VCE **8.033 V** · VB 2.599 V · VE 1.899 V · VC 9.932 V · IB 9.401 µA · IE 0.950 mA · Forward Active; IC ลดจาก 1.026 → 0.940 mA ตามทำนาย | OpenCode Browser | ผ่าน |
| A5 · อินพุตผิด | Fixed · RB = 0 | มีข้อความให้แก้ RB, เว็บไม่ล่ม และไม่แสดงผลเดิมเป็นผลของรอบนี้ | HTTP 200 + กล่อง **"ไม่สามารถคำนวณได้"** ข้อความ **"ค่า RB ต้องมากกว่า 0 Ω"**; ไม่มีบล็อก `Region:`/ผลลัพธ์; ค่าที่กรอกยังคงอยู่ | OpenCode Browser | ผ่าน |

**หมายเหตุวิธีตรวจ:** Playwright MCP = `NOT RUN` (ตั้งค่าใน `opencode.json` แล้วแต่ MCP server ยังไม่โหลดใน session ที่ตรวจ จึงต้องรีสตาร์ท OpenCode) — ใช้ **OpenCode Browser** แทนตามที่ใบงานอนุญาต ให้คะแนนการตรวจผลเท่ากันทุกวิธี

### รายละเอียดผลทั้ง 7 ปริมาณ (ตารางเสริม)

| # | โหมด / อินพุต | ค่าคาดหมาย (IC / VCE) | VB | VE | VC | VCE | IC | IB | IE | Region | วิธีตรวจ | ผล |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Divider · R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 1.2299 mA / 8.0522 V | 1.942 V | 1.242 V | 9.294 V | 8.052 V | 1.230 mA | 12.299 µA | 1.242 mA | Forward Active | OpenCode Browser | ผ่าน |
| A2 | Fixed · RB=1 MΩ | 1.1300 mA / 9.5140 V | 0.700 V | 0.000 V | 9.514 V | 9.514 V | 1.130 mA | 11.300 µA | 1.141 mA | Forward Active | OpenCode Browser | ผ่าน |
| A3 | Emitter · RB=1 MΩ, RE=1 kΩ | 1.0263 mA / 8.7054 V | 1.737 V | 1.037 V | 9.742 V | 8.705 V | 1.026 mA | 10.263 µA | 1.037 mA | Forward Active | OpenCode Browser | ผ่าน |
| A4 | Emitter · RB=1 MΩ, RE=2 kΩ | 0.9401 mA / 8.0328 V | 2.599 V | 1.899 V | 9.932 V | 8.033 V | 0.940 mA | 9.401 µA | 0.950 mA | Forward Active | OpenCode Browser | ผ่าน |
| A5 | Fixed · RB=0 | error ที่ช่อง RB | — | — | — | — | — | — | — | ไม่แสดงผล | OpenCode Browser | ผ่าน |

**A5 รายละเอียด:** หน้าเว็บตอบ HTTP 200 พร้อมกล่อง "ไม่สามารถคำนวณได้" ข้อความ **"ค่า RB ต้องมากกว่า 0 Ω"** และไม่แสดงบล็อก `Region:` / ผลลัพธ์รอบก่อน

### หลักฐานจากเบราว์เซอร์

- `docs/evidence/lab03-a1-divider.png` — A1 สำเร็จ: IC 1.230 mA, VCE 8.052 V, Forward Active
- `docs/evidence/lab03-a5-rb-zero.png` — A5: error ที่ช่อง RB และไม่มีผลลัพธ์

### ค่าอ้างอิงอิสระของโหมดใหม่ (คำนวณมือ)

ใช้ VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

**A2 — Fixed Bias, RB = 1 MΩ**

```
IB = (VCC − VBE) / RB = (12 − 0.70) V / 1 MΩ = 11.300 µA
IC = β·IB = 100 × 11.300 µA = 1.1300 mA
IE = (β + 1)·IB = 101 × 11.300 µA = 1.1413 mA
VB = VBE = 0.700 V ; VE = 0 V
VC = VCC − IC·RC = 12 V − (1.1300 mA)(2.2 kΩ) = 9.5140 V
VCE = VC − VE = 9.5140 V
```

**A3 — Emitter Bias, RB = 1 MΩ, RE = 1 kΩ**

```
IB = (VCC − VBE) / [RB + (β + 1)·RE]
   = 11.30 V / (1 MΩ + 101 × 1 kΩ) = 11.30 V / 1.101 MΩ = 10.2634 µA
IC = β·IB = 1.0263 mA
IE = (β + 1)·IB = 1.0366 mA
VE = IE·RE = (1.0366 mA)(1 kΩ) = 1.0366 V
VB = VE + VBE = 1.7366 V
VC = 12 V − (1.0263 mA)(2.2 kΩ) = 9.7421 V
VCE = VC − VE = 8.7054 V
```

A4 ใช้สมการเดียวกับ A3 โดยเปลี่ยน RE เป็น 2 kΩ → IB = 9.4010 µA, IC = 0.9401 mA, VCE = 8.0328 V

**บทบาท AI กับผู้ตรวจ:** AI เขียนสมการ/โค้ด/เทสต์/เอกสาร; นักศึกษาตรวจสมการมือข้างบน กด A1–A5 ในเบราว์เซอร์ และทบทวน commit ก่อนส่ง โค้ดเลือกฟังก์ชันอยู่ที่ `app.py` บรรทัด 62–79 (`if mode == ...`) แปลง kΩ→Ω ที่ `app.py` บรรทัด 55 (`scale = 1000.0 if unit == "k" else 1.0`) และสมการอยู่ที่ `dc_bias.py` บรรทัด 157–220

A1 ยังได้ผลตรงกับ Lab 02 ทุกหลัก (VTH 2.163934 V, IB 12.2986 µA, IC 1.2299 mA, VCE 8.0522 V) จึงยืนยันว่าโหมดใหม่ไม่กระทบผลเดิม

## 5. ข้อจำกัดที่ยังเหลือ

- ไม่ตรวจ DC Load Line หรือผลจาก SPICE — อยู่นอกขอบเขตของใบงาน
- ไม่รองรับการบันทึก/แชร์ผลลัพธ์
- ตัวเลขแสดง 3 ตำแหน่งทศนิยม ค่าที่ละเอียดกว่านี้ต้องอ่านจาก `dc_bias.py` โดยตรง
- ยังไม่ได้รัน A1–A5 ผ่าน Playwright MCP ในเซสชันนี้ (ต้องรีสตาร์ท OpenCode ก่อน) — ใช้ OpenCode Browser แทนตามที่บันทึกไว้ข้างบน

## 6. ปรับความแข็งแรงก่อน Lab 03 (17 พ.ย. 2569)

ทำแบบ test-first ทุกข้อ และ A1 ยังได้ผลเดิมทุกหลัก (VTH 2.163934 V, IB 12.2986 µA, IC 1.2299 mA, VCE 8.0522 V)

| ปัญหาเดิม | สิ่งที่แก้ | หลักฐาน |
|---|---|---|
| `float("nan")`, `"inf"`, `"1e400"` หลุดเข้าโมเดล | `to_float` ปฏิเสธค่าที่ไม่เป็นจำนวนจำกัด พร้อมชื่อฟิลด์ | `InputParsingTests.test_rejects_non_finite` |
| β = 1e308 ทำให้ IB = 0 และ IC = 0 เงียบ ๆ | หารเศษ/ส่วนด้วย β ก่อนคำนวณ | `test_huge_beta_keeps_ic_at_forward_active_limit` (ได้ 1.4639 mA ตามลิมิต) |
| `validate_inputs` บังคับ R1, R2, RE ทุกโหมด | แยก `validate_common` + `validate_resistors(**fields)` | `ModeValidationTests` |
| เขต Saturation ใช้ `< 0.2` | `classify_region()` ใช้ `≤ 0.2` | `RegionThresholdTests` |
| `VBE ≥ VCC` ถูกตีเป็น input error | ปล่อยให้โมเดลรายงาน Cutoff + warning | `test_accepts_vbe_at_vcc_so_model_reports_cutoff` |
| `r_unit` ค่าอื่นถูกตีเป็น Ω เงียบ ๆ | รับเฉพาะ `k` และ `""` | `test_unknown_resistor_unit_is_rejected` |

## 7. Final review fix (17 พ.ย. 2569)

Fresh reviewer ตรวจทั้ง branch แล้วพบว่า Flask path ปลอดภัย แต่ถ้าเรียกฟังก์ชันคำนวณตรง ๆ ด้วย `RB = 0` จะได้ `ZeroDivisionError` และ `RB` ติดลบจะคืนกระแสติดลบเงียบ ๆ

| ปัญหา | สิ่งที่แก้ | หลักฐาน |
|---|---|---|
| `calculate_fixed` / `calculate_emitter` / `calculate_divider` ไม่ตรวจอินพุตเอง | เรียก `validate_common` + `validate_resistors` ที่ต้นฟังก์ชันทั้งสามโหมด | `CalculatorInputTests` 4 ตัว (เขียนเทสต์เห็น fail ก่อนแก้: 3 failures + 1 error) |

หลังแก้: **Ran 50 tests — OK** และไม่ได้แก้พฤติกรรมหน้าเว็บ (ยัง validate ที่ `app.py` แล้วเรียกฟังก์ชันซ้ำอย่างปลอดภัย)

Minor ที่เลื่อนไว้: ข้อความ error กรณีค่าล้นเป็น infinity ยังขึ้นว่า "ต้องมากกว่า 0 Ω" (ควรเป็น "ต้องเป็นจำนวนจำกัด") และยังไม่มีเทสต์ regression ของการคงค่าหลัง error / หน่วย Ω ของ Fixed และ Emitter
