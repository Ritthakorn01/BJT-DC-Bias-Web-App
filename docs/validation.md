# Validation Log — BJT DC Bias Web App

วันที่ตรวจ: 10 พฤศจิกายน 2569
เครื่องที่ใช้: Windows 11, Python 3.15.2, Flask 3.1.3
คำสั่งที่ใช้รันเทสต์:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลลัพธ์: **Ran 20 tests — OK**

## 1. Automated tests

| กลุ่ม | จำนวน | ตรวจอะไร |
|---|---|---|
| `test_dc_bias.ReferencePointTests` | 3 | ค่า VB, VE, VC, VCE, IC, IE, IB ตรงกับการคำนวณมือ ±0.01 |
| `test_dc_bias.InputParsingTests` | 4 | รับช่องว่างและ comma คั่นหลักพัน, ปฏิเสธค่าว่าง/ไม่ใช่ตัวเลข |
| `test_dc_bias.ValidationTests` | 3 | ปฏิเสธ R ≤ 0, β ≤ 0, VBE ≥ VCC |
| `test_dc_bias.RegionTests` | 3 | Cutoff, Saturation, Forward Active |
| `test_web.WebIndexTests` | 1 | `GET /` → 200 และมีฟอร์ม |
| `test_web.CalculateRouteTests` | 6 | ผลลัพธ์จาก server, error, หน่วย kΩ/Ω, ค่าสุดขั้ว, UTF-8 |

## 2. เทียบค่าจากเว็บกับการคำนวณมือ (A3)

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

## 3. ตรวจรับ A1–A7

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

## 4. ข้อจำกัดที่ยังเหลือ

- ไม่ตรวจ DC Load Line หรือผลจาก SPICE — อยู่ในขอบเขต W4
- ไม่รองรับการบันทึก/แชร์ผลลัพธ์
- ตัวเลขแสดง 3 ตำแหน่งทศนิยม ค่าที่ละเอียดกว่านี้ต้องอ่านจาก `dc_bias.py` โดยตรง
