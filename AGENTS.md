# AGENTS.md — กติกาสำหรับ AI Coding Agent

โปรเจกต์นี้เป็นงาน Lab 03 ของ ENG29 2121 (Flask + BJT DC Bias) อ่าน `docs/lab03-design.md` และ `docs/design-note.md` ก่อนแก้โค้ด

## ขอบเขต

- ฟีเจอร์ที่อนุญาต: DC Bias ของ NPN Common Emitter สามโหมด — Voltage Divider Bias, Fixed Bias และ Emitter Bias แบบแหล่งจ่ายเดียว
- ห้ามเพิ่ม AC analysis, Bode plot, Transient, SPICE, DC Load Line, bias type อื่น หรือ UI framework โดยไม่มีการอนุมัติ
- งานตรวจรับหลักคือ Browser A1–A5 ตามใบงาน; automated tests เป็นตาข่ายกันถอยหลัง

## กติกาโค้ด

1. **สมการทั้งหมดอยู่ใน `dc_bias.py`** — ห้ามเขียนสมการฟิสิกส์ใน `app.py`, template หรือ CSS
2. `dc_bias.py` ต้องไม่ import Flask หรือรู้จัก HTTP/form — รับเป็นตัวเลขและคืน `BiasResult`; Flask เรียก `BiasResult.to_dict()` เพื่อรับคีย์และหน่วยที่ใช้แสดงผล
3. หน่วยภายใน `dc_bias.py` เป็น SI (V, A, Ω) การแปลงเป็น mA/µA อยู่ใน `to_dict()` และ template แสดงผลเท่านั้น
4. **ห้ามใช้ JavaScript คำนวณผล** — หน้าเว็บต้องเป็น server-rendered form post; การเปลี่ยนโหมดใช้ `GET /?mode=`
5. ไม่ใช้ CDN — CSS ต้องทำงานได้ตอนไม่มีอินเทอร์เน็ต
6. ข้อความที่ผู้ใช้เห็นเป็นภาษาไทย ศัพท์วิศวกรรมคงเป็นอังกฤษ (VCC, VCE, β)
7. Error ทั้งหมดตอบ **HTTP 200** พร้อม error box ไม่ใช้ 400/500; error ต้องไม่แสดงผลของรอบก่อน
8. Dependency ใหม่ต้องขออนุมัติก่อน และต้องอัปเดต `requirements.txt`

## Testing

- ใช้ `unittest` จาก standard library เท่านั้น (ไม่ใช้ pytest)
- ทุกฟีเจอร์ใหม่ต้องมีเทสต์ที่เขียนก่อนและเห็นมัน fail ก่อน
- คำสั่ง: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- ค่าคาดหวังของ DC Bias ต้องมาจากการคำนวณมือ ไม่ใช่ค่าที่ generate จากฟังก์ชันที่กำลังทดสอบ
- ห้าม commit ถ้าเทสต์ไม่ผ่าน

## Browser acceptance

- ใช้ `.opencode/skills/browser-acceptance-check/SKILL.md` และตาราง A1–A5 ของนักศึกษา
- รายงานวิธีที่ใช้จริง: `Playwright MCP`, `OpenCode Browser` หรือ `Manual`
- ห้ามใช้ curl หรือการอ่านโค้ดแทนการรัน browser case; ถ้ารันไม่ได้ให้รายงาน `NOT RUN` พร้อมเหตุผล

## Git

- commit message แบบ Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`)
- ห้าม commit `.venv/`, `.env`, credential หรือ API key
- ก่อน push ให้ตรวจ `git status` และ `git diff --staged`
