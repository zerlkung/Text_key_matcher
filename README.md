# 🔑 Key Matcher

**Key Matcher** — เครื่องมือจับคู่ key-value ระหว่าง 2 ไฟล์ แบบ GUI
รองรับ `.txt` `.csv` `.json` `.xml`

อ่าน key จากไฟล์ Base → หา key ที่ตรงกันในไฟล์ Target → เอาค่า value จาก Target มาใส่ในไฟล์ใหม่
โดยคงลำดับ key ตาม Base ไว้

> A Python GUI tool to match and merge key-value pairs between two files.
> Base defines key order → Target provides replacement values → output a merged file.

---

## 📸 หน้าตาโปรแกรม / Screenshot

```
┌─────────────────────────────────────────────┐
│  🔑  Key Matcher              [🌙 Dark]     │
├─────────────────────────────────────────────┤
│  📁  เลือกไฟล์                               │
│  Base:   [PC_eng.common.txt]  [📂 Browse]   │
│  Target: [PS4_.common.txt]    [📂 Browse]   │
├─────────────────────────────────────────────┤
│  ⚙  ตั้งค่ารูปแบบไฟล์   Format: [txt▾]       │
│  Delimiter: [|▾]  Encoding: [utf-8▾]       │
├─────────────────────────────────────────────┤
│  ✚  เพิ่ม Key เอง                            │
│  [___________________________________]      │
├─────────────────────────────────────────────┤
│  [🔍 MATCH]  [💾 SAVE]  ████████░░  88.9%   │
├─────────────────────────────────────────────┤
│  👁  Preview (50 บรรทัดแรก)                  │
│  302613|Slow Motion                         │
│  1545394|Shoot the lock to open the door    │
│  ...                                        │
└─────────────────────────────────────────────┘
```

---

## 🚀 วิธีใช้ / How to Use

### ภาษาไทย

1. ติดตั้ง Python 3.8 ขึ้นไป + CustomTkinter:
   ```bash
   pip install customtkinter
   ```
2. ดาวน์โหลด `key_matcher_gui.py` และ `orange.json` (ไว้โฟลเดอร์เดียวกัน)
3. รัน:
   ```bash
   python key_matcher_gui.py
   ```
4. เลือกไฟล์ Base (ไฟล์ที่มี key เป็นหลัก)
5. เลือกไฟล์ Target (ไฟล์ที่ต้องการดึง value)
6. ตั้งค่า format และ delimiter ให้ถูกต้อง (auto-detect จากนามสกุลไฟล์)
7. *(ไม่บังคับ)* พิมพ์ key เพิ่มเองในช่อง "เพิ่ม Key เอง"
8. กด **🔍 MATCH & PREVIEW** เพื่อดูผล
9. กด **💾 SAVE** — ชื่อไฟล์ขึ้นอัตโนมัติ `ชื่อเดิม_matched.นามสกุล`
10. สลับ Dark/Light ได้ที่มุมขวาบน ☀🌙

### English

1. Install Python 3.8+ + CustomTkinter:
   ```bash
   pip install customtkinter
   ```
2. Download `key_matcher_gui.py` and `orange.json` (same folder)
3. Run:
   ```bash
   python key_matcher_gui.py
   ```
4. Select **Base** file (reference keys)
5. Select **Target** file (source of replacement values)
6. Set format + delimiter (auto-detected from file extension)
7. *(Optional)* Add manual keys
8. Click **🔍 MATCH & PREVIEW** to see results
9. Click **💾 SAVE** — filename auto-generates as `original_matched.ext`
10. Toggle Dark/Light mode at top-right corner ☀🌙

---

## 🔧 รูปแบบไฟล์ที่รองรับ / Supported Formats

### `.txt` — Delimiter-based
```
KEY|VALUE
302613|Slow Motion
1545394|Shoot the lock to open the door
```
ตั้งค่า delimiter ได้: `|` `=` `:` `\t` `,` `->` หรือ custom

### `.csv` — Column-based
```csv
id,text
302613,Slow Motion
1545394,Shoot the lock to open the door
```
ตั้งค่า: delimiter, Key Column #, Value Column #, มี Header หรือไม่

### `.json` — Object หรือ Array
```json
{ "302613": "Slow Motion", "1545394": "Shoot the lock..." }
```
หรือ
```json
[{ "id": "302613", "value": "Slow Motion" }, ...]
```
ตั้งค่า: structure (`object`/`array`), Key field, Value field

### `.xml` — Elements with attributes
```xml
<root>
  <string id="302613">Slow Motion</string>
  <string id="1545394">Shoot the lock to open the door</string>
</root>
```
ตั้งค่า: Item tag, Key attribute, Value attribute (`#text` = เนื้อหาภายใน element)

### `.xml` / `.txt` — Merged XML fragments (ไม่มี root, ไม่มี closing tag)
```xml
# src: archive_figure.msg.23
<string guid=cd5998f9-ce71-40f2-beee-585ce93ae678>วอล์คเกอร์
<string guid=bdb759bc-aff3-4834-bed5-46d7ac73b215>2.40 ม.
```
ตั้งค่า: Format `xml`, Item tag `string`, Key attr `guid`, Value attr `#text`
(โปรแกรม auto-detect merged format, ไม่ต้องใช้ delimiter)
รองรับไฟล์ที่มี `#` comment, unquoted attributes, ไม่มี `</string>` ปิด
เมื่อ Save — output จะคง format เดิม (ไม่มี root, ไม่มี closing tag, ไม่ quote attributes)

---

## ⚙ ความต้องการ / Requirements

- **Python** 3.8 ขึ้นไป
- **CustomTkinter** (`pip install customtkinter`)
- รองรับ Windows / macOS / Linux
- Encoding: `utf-8` (default), `utf-8-sig`, `utf-16`, `cp874`, `tis-620`, `latin-1`
- Theme: `orange.json` (CTkThemesPack)

---

## 📝 License

MIT — ใช้ได้อิสระ
