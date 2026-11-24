# Lab 03 — Fixed Bias + Emitter Bias · Design

**วันที่:** 17 พฤศจิกายน 2569
**อ้างอิง:** ใบงาน ENG29 2121 Lab 03, `docs/design-note.md` (Lab 02), `docs/validation.md`
**สถานะ:** อนุมัติแล้ว (17 พฤศจิกายน 2569)

## 1. Intent

ต่อยอดเว็บ Flask เดิมจาก Lab 02 ให้เลือกวงจรไบอัสได้สามแบบ (Fixed, Emitter, Voltage Divider)
โดยใช้ Python คำนวณตามสมการในใบงาน แล้วตรวจผลจากหน้าเว็บจริงด้วยตาราง A1–A5

**ทำไม:** ใบงานต้องการให้นักศึกษาเห็นว่าโค้ดที่ AI สร้างตรงกับสมการที่เรียน และตรวจผลจากเบราว์เซอร์จริง
ไม่ใช่เชื่อตัวเลขบนหน้าจอ

## 2. Goals

- G1 · `GET /?mode=fixed|emitter|divider` แสดงเฉพาะช่องของโหมดนั้น
- G2 · `POST /calculate` เลือกฟังก์ชันตามโหมด แปลงหน่วยครั้งเดียว และคืนผลเป็น `dict` คีย์ร่วม
- G3 · Fixed และ Emitter ใช้สมการในใบงาน; Divider ให้ผลเดิมทุกหลัก (A1)
- G4 · อินพุตผิด → error รายฟิลด์; อินพุตถูกแต่โมเดลใช้ไม่ได้ → warning (ไม่ใช่ error)
- G5 · ผ่าน A1–A5 บนเบราว์เซอร์จริง พร้อมหลักฐานใน `docs/validation.md`
- G6 · คงชุดทดสอบเดิมและเพิ่มเทสต์ของสองโหมดใหม่

## 3. Non-goals

- ไม่ทำ SPICE, DC Load Line, AC/Transient, Bypass capacitor
- ไม่เพิ่ม JavaScript คำนวณผล และไม่ใช้ CDN
- ไม่ทำ authentication/database/deployment
- ไม่เปลี่ยนแบบจำลอง (β และ VBE คงที่ใน Forward Active)

## 4. Approaches

| ทาง | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **A (เลือก)** | select โหมด + ปุ่ม "แสดงฟอร์มโหมดนี้" → `GET /?mode=` แล้ว server render เฉพาะช่องของโหมด | ไม่ใช้ JS, snapshot ของ Playwright เห็นเฉพาะช่องจริง, สอดคล้อง AGENTS | เปลี่ยนโหมดต้องคลิกหนึ่งครั้ง |
| B | แสดงทุกช่องแต่ `disabled` ช่องที่ไม่ใช้ | เห็นตำแหน่งอุปกรณ์ครบ | snapshot รก, ต้องจัดการ disabled ระหว่าง submit |
| C | JS `onchange` reload | ลื่นที่สุด | เพิ่ม JavaScript ที่โปรเจกต์ตั้งใจเลี่ยง และเสี่ยงผลไม่ตรง backend |

เลือก A เพราะใบงานระบุ "เห็นช่องที่ใช้เท่านั้น หรือทำให้ช่องที่ไม่เกี่ยวข้องใช้งานไม่ได้" และ "ไม่จำเป็นต้องเพิ่ม JavaScript"

## 5. Interface

### `dc_bias.py`
- `calculate_fixed(vcc, rb, rc, beta, vbe) -> BiasResult`
- `calculate_emitter(vcc, rb, rc, re, beta, vbe) -> BiasResult`
- `calculate_divider(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult` (ตรรกะเดิมของ `calculate`)
- `calculate` คงเป็น alias ของ `calculate_divider` เพื่อไม่ให้โค้ด/เทสต์เดิมพัง
- `validate_common(vcc, beta, vbe)` + `validate_resistors(**fields)` ใช้ร่วมทั้งสามโหมด
- `classify_region(vce)` ใช้ `VCE ≤ 0.2 V` เป็นแหล่งตัดสินเดียว
- `BiasResult.to_dict()` คืนคีย์ที่ Flask ใช้:
  `vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ua, ie_ma, region, warnings`
  (ภายในยังเป็น SI; แปลงหน่วยเฉพาะใน `to_dict`)

### สมการที่เพิ่ม
```
Fixed   : IB = (VCC − VBE) / RB
Emitter : IB = (VCC − VBE) / [RB + (β+1)RE]
ทั้งคู่   : IC = βIB · IE = (β+1)IB · VE = IE·RE (Fixed: VE = 0)
          VB = VE + VBE · VC = VCC − IC·RC · VCE = VC − VE
```
คำนวณแบบหารด้วย β ทั้งเศษและส่วน (กัน overflow ของ β สูงมาก) เหมือน Divider

### `app.py`
- `MODES = {"divider", "fixed", "emitter"}`; โหมดไม่รู้จัก → error "โหมดวงจรไม่ถูกต้อง" ไม่เดาเป็น Divider
- `if/elif` ตามโหมด: แปลง kΩ→Ω ครั้งเดียว, ตรวจเฉพาะช่องของโหมด, เรียกฟังก์ชัน, ส่ง `result.to_dict()`
- error → `result=None` เสมอ (ไม่มีผลรอบเก่าค้าง) + คงโหมดและค่าที่กรอก
- คงการตอบ HTTP 200 พร้อม error box

### `templates/index.html`
- ฟอร์มเลือกโหมดแยกจากฟอร์มคำนวณ (`GET /`, `select#mode` + ปุ่ม)
- ฟอร์มคำนวณ `POST /calculate` มี `hidden mode` และเฉพาะช่องของโหมด
- ทุกช่องมี `id` + `<label for>` เพื่อให้ Playwright อ่าน/กรอกได้
- ผลลัพธ์ระบุโหมดที่ใช้ และ Region; error/warning แยกกล่อง

### เอกสาร
- `AGENTS.md`: ขอบเขต Lab 03 (สามโหมด), กติกาเดิมคงอยู่
- `README.md`: วิธีรัน + สามโหมด
- `docs/validation.md`: ตาราง A1–A5 พร้อมวิธีตรวจและหลักฐานจริง

## 6. การตรวจรับ

**A1–A5** (VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V; IC ±0.01 mA, VCE ±0.02 V)
| กรณี | อินพุต | ค่ามือ (IC / VCE) |
|---|---|---|
| A1 | Divider R1=100k, R2=22k, RE=1k | 1.2299 mA / 8.0522 V (ต้องเท่า Lab 2) |
| A2 | Fixed RB=1M | 1.1300 mA / 9.5140 V |
| A3 | Emitter RB=1M, RE=1k | 1.0263 mA / 8.7054 V |
| A4 | Emitter RB=1M, RE=2k | 0.9401 mA / 8.0328 V |
| A5 | Fixed RB=0 | ต้องมีข้อความให้แก้ RB, หน้าเว็บไม่ล่ม, ไม่มีผลเก่า |

**เครื่องมือ:** ตั้ง `opencode.json` เป็น Playwright MCP (V2) ตามใบงาน §5 ถ้าเซสชันปัจจุบันยังไม่โหลด MCP
จะใช้ OpenCode Browser ที่มีในแอปตรวจก่อน แล้วระบุวิธีจริงในตารางว่า `OpenCode Browser` ไม่ใช่ `Playwright MCP`

**เทสต์:** เพิ่มเทสต์ค่ามือของ Fixed/Emitter, การเลือกโหมด, โหมดไม่รู้จัก, ช่องเฉพาะโหมด, RB=0, คีย์ของ `to_dict`

## 7. ความเสี่ยง

| ความเสี่ยง | ทางรับมือ |
|---|---|
| Playwright MCP ต้องรีสตาร์ตแอป | ใช้ Browser tool ในแอปแล้วระบุวิธีจริง; คง config ไว้ให้รอบถัดไป |
| ปัดเศษต่างจากค่ามือ | แสดง 3 ตำแหน่ง + tolerance ตามใบงาน |
| แก้ Divider แล้วผลเปลี่ยน | เทสต์ A1 เทียบค่ามือเดิม ±0.01 ก่อน/หลัง |

## 8. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- ถ้อยคำภาษาไทยของปุ่ม/หัวข้อ (คงศัพท์อังกฤษ VCC, VBE, β)
- การจัดวาง CSS ของช่องที่เพิ่ม (ใช้ `style.css` เดิม ไม่เพิ่ม dependency)
