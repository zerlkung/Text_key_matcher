#!/usr/bin/env python
"""
Key Matcher GUI — จับคู่ key-value ระหว่าง 2 ไฟล์ + แยก/รวมไฟล์ txt
รองรับ .txt .csv .json .xml
Built with CustomTkinter + orange theme
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import OrderedDict
import csv
import json
import xml.etree.ElementTree as ET
import os
import re

# ═══════════════════════════════════════════════════════════
# Parsers (key-value)
# ═══════════════════════════════════════════════════════════

def parse_txt(path, delimiter="|", encoding="utf-8", alt_lines=False):
    result = OrderedDict()
    with open(path, "r", encoding=encoding) as f:
        lines = [l.rstrip("\n\r") for l in f]

    if alt_lines:
        # key/value alternating lines: *ID*\nvalue\n*ID*\nvalue\n...
        # also supports [[TAG]] lines as extra keys for the same value
        # structure: *ID*\n[[TAG]]\ntext → both ID and TAG → same value
        i = 0
        if lines and not (lines[0].startswith("*") or lines[0].startswith("[")):
            i = 1
        while i < len(lines):
            while i < len(lines) and not (lines[i].startswith("*") or lines[i].startswith("[")):
                i += 1
            if i + 1 >= len(lines):
                break
            # collect consecutive key lines (starts with * or [)
            keys = []
            while i < len(lines) and (lines[i].startswith("*") or lines[i].startswith("[")):
                key_raw = lines[i].strip()
                if key_raw.startswith("*"):
                    keys.append(key_raw.strip("*"))
                elif key_raw.startswith("[["):
                    keys.append(key_raw.strip("[]"))
                i += 1
            # next line is the value
            if i < len(lines):
                val = lines[i]
                for k in keys:
                    if k:
                        result[k] = val
                i += 1
        return result

    # standard delimiter mode
    for line in lines:
        if not line.strip():
            continue
        idx = line.find(delimiter)
        if idx == -1:
            result[line] = ""
        else:
            result[line[:idx]] = line[idx + len(delimiter):]
    return result

def write_txt(data, path, delimiter="|", encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as f:
        for key, val in data.items():
            f.write(f"{key}{delimiter}{val}\n")

def parse_csv_file(path, key_col=0, val_col=1, delimiter=",", has_header=True, encoding="utf-8"):
    result = OrderedDict()
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if has_header:
            next(reader, None)
        for row in reader:
            if len(row) > max(key_col, val_col):
                result[row[key_col].strip()] = (
                    row[val_col].strip() if len(row) > val_col else "")
    return result

def write_csv_file(data, path, key_header="key", val_header="value",
                   delimiter=",", encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow([key_header, val_header])
        for key, val in data.items():
            writer.writerow([key, val])

def parse_json_file(path, key_field="id", val_field="value", structure="array", encoding="utf-8", src_field=None):
    with open(path, "r", encoding=encoding) as f:
        raw = json.load(f)
    read_field = src_field if src_field else val_field
    result = OrderedDict()
    original_structure = None
    is_wrapped = False
    if structure == "array" and isinstance(raw, dict):
        entries = raw.get("entries")
        if entries is not None:
            original_structure = raw
            raw = entries
            is_wrapped = True
    if structure == "object":
        if isinstance(raw, dict):
            for k, v in raw.items():
                result[str(k)] = str(v) if v is not None else ""
    else:
        if isinstance(raw, list):
            for item in raw:
                k = item.get(key_field)
                v = item.get(read_field, "")
                if k is not None:
                    result[str(k)] = str(v) if v is not None else ""
    return result, is_wrapped, original_structure

def write_json_file(data, path, structure="array", key_field="id",
                    val_field="value", original_structure=None, encoding="utf-8"):
    if original_structure is not None and "entries" in original_structure:
        for entry in original_structure["entries"]:
            k = str(entry.get(key_field, ""))
            if k in data:
                entry[val_field] = data[k]
        out = original_structure
    elif structure == "object":
        out = dict(data)
    else:
        out = [{key_field: k, val_field: v} for k, v in data.items()]
    with open(path, "w", encoding=encoding) as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def parse_xml_file(path, item_tag="string", key_attr="id", val_attr="#text", encoding="utf-8"):
    result = OrderedDict()
    with open(path, "r", encoding=encoding) as f:
        raw = f.read()
    raw_stripped = raw.strip()
    if not raw_stripped.startswith("<?xml") and not raw_stripped.startswith("<root"):
        tag_pattern = re.compile(
            rf'<{re.escape(item_tag)}\s+{re.escape(key_attr)}=([^\s>]+)>(.*)'
        )
        line_struct = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                line_struct.append({"type": "empty", "text": line})
                continue
            if stripped.startswith("#") or stripped.startswith("//"):
                line_struct.append({"type": "comment", "text": line})
                continue
            m = tag_pattern.match(stripped)
            if m:
                key = m.group(1)
                val = m.group(2)
                result[key] = val
                line_struct.append({"type": "entry", "key": key, "val": val})
            else:
                line_struct.append({"type": "comment", "text": line})
        return result, True, line_struct
    tree = ET.fromstring(raw)
    for elem in tree.iter(item_tag):
        key = elem.tag if key_attr == "#tag" else elem.get(key_attr)
        if key is None:
            key = elem.tag
        val = (elem.text or "") if val_attr == "#text" else elem.get(val_attr, "")
        result[key] = val
    return result, False, []

def write_xml_file(data, path, root_tag="root", item_tag="string",
                   key_attr="id", val_attr="#text", encoding="utf-8"):
    root = ET.Element(root_tag)
    for key, val in data.items():
        elem = ET.SubElement(root, item_tag)
        if key_attr != "#tag":
            elem.set(key_attr, str(key))
        if val_attr == "#text":
            elem.text = str(val)
        else:
            elem.set(val_attr, str(val))
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding=encoding, xml_declaration=True)

def write_xml_fragments(data, line_struct, path, item_tag="string", key_attr="guid", encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="\n") as f:
        for item in line_struct:
            if item["type"] == "comment" or item["type"] == "empty":
                f.write(item["text"] + "\n")
            elif item["type"] == "entry":
                key = item["key"]
                val = data.get(key, item["val"])
                f.write(f'<{item_tag} {key_attr}={key}>{val}\n')

# ═══════════════════════════════════════════════════════════
# Split & Join — txt folder merge
# ═══════════════════════════════════════════════════════════

PATH_MARKER = "[PATH]"

def merge_txt_folder(folder, output_path, encoding="utf-8"):
    """รวมทุก .txt ใน folder เป็นไฟล์เดียว คั่นด้วย [PATH]filename[PATH]"""
    files = sorted([f for f in os.listdir(folder) if f.lower().endswith(".txt")])
    count = 0
    with open(output_path, "w", encoding=encoding, newline="\n") as out:
        for fname in files:
            fpath = os.path.join(folder, fname)
            with open(fpath, "r", encoding=encoding) as inf:
                content = inf.read()
            out.write(f"{PATH_MARKER}{fname}{PATH_MARKER}\n")
            if content and not content.endswith("\n"):
                content += "\n"
            out.write(content)
            count += 1
    return count

def split_merged_txt(merged_path, output_folder, encoding="utf-8"):
    """แยกไฟล์รวมกลับเป็น .txt ตาม [PATH] markers"""
    with open(merged_path, "r", encoding=encoding) as f:
        content = f.read()

    # ponytail: split on marker lines, simple state machine
    pattern = re.compile(rf'^{re.escape(PATH_MARKER)}(.+?){re.escape(PATH_MARKER)}\s*$', re.MULTILINE)
    splits = pattern.split(content)

    # splits[0] = before first marker (usually empty), then alternating: filename, content
    count = 0
    os.makedirs(output_folder, exist_ok=True)
    i = 1  # skip text before first marker
    while i + 1 < len(splits):
        fname = splits[i].strip()
        body = splits[i + 1]
        if fname:
            fpath = os.path.join(output_folder, fname)
            with open(fpath, "w", encoding=encoding, newline="\n") as f:
                f.write(body.strip("\n") + "\n")
            count += 1
        i += 2
    return count

# ═══════════════════════════════════════════════════════════
# Matcher logic
# ═══════════════════════════════════════════════════════════

def is_likely_garbled(text):
    if not text or len(text) < 3:
        return False
    garbled_ranges = [
        (0x0080, 0x00FF), (0x0100, 0x024F), (0x02B0, 0x02FF),
    ]
    garbled_count = 0
    total = len(text)
    for ch in text:
        cp = ord(ch)
        if ch.isspace() or cp < 128:
            continue
        for lo, hi in garbled_ranges:
            if lo <= cp <= hi:
                garbled_count += 1
                break
    ratio = garbled_count / max(total, 1)
    if ratio > 0.25:
        return True
    if garbled_count >= 5 and ratio > 0.15:
        return True
    return False

def match_keys(base_dict, target_dict):
    result = OrderedDict()
    matched = unmatched = garbled_skip = 0
    for key, base_val in base_dict.items():
        if key in target_dict:
            tval = target_dict[key]
            if is_likely_garbled(tval):
                result[key] = base_val
                garbled_skip += 1
            else:
                result[key] = tval
                matched += 1
        else:
            result[key] = base_val
            unmatched += 1
    return result, matched, unmatched, garbled_skip, len(base_dict)

# ═══════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════

THEME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orange.json")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(THEME_FILE)

ACCENT      = "#FF8C42"
ACCENT_DARK = "#FF6505"
GREEN       = "#4ade80"
YELLOW      = "#fbbf24"
RED         = "#f87171"

FONT_CARD   = ("Segoe UI", 12, "bold")
FONT_MONO   = ("Cascadia Code", 10)

class KeyMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Key Matcher")
        self.root.geometry("1020x800")
        self.root.minsize(740, 580)

        # matcher state
        self.base_path = ctk.StringVar()
        self.target_path = ctk.StringVar()
        self.format_var = ctk.StringVar(value="txt")
        self.delimiter_var = ctk.StringVar(value="|")
        self.encoding_var = ctk.StringVar(value="utf-8")
        self.csv_key_col = ctk.StringVar(value="0")
        self.csv_val_col = ctk.StringVar(value="1")
        self.csv_has_header = ctk.BooleanVar(value=True)
        self.json_structure = ctk.StringVar(value="array")
        self.json_key_field = ctk.StringVar(value="id")
        self.json_val_field = ctk.StringVar(value="value")
        self.json_src_field = ctk.StringVar(value="")
        self.xml_item_tag = ctk.StringVar(value="string")
        self.xml_key_attr = ctk.StringVar(value="id")
        self.xml_val_attr = ctk.StringVar(value="#text")
        self.txt_alt_lines = ctk.BooleanVar(value=False)
        self._presets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")
        self._presets = self._load_presets()
        self.preset_var = ctk.StringVar(value="Auto")
        self.manual_keys = ctk.StringVar()
        self.merged_data = None
        self._xml_is_merged = False
        self._xml_line_struct = []
        self._xml_item_tag = ""
        self._xml_key_attr = ""
        self._json_original = None
        self._json_val_field = ""
        self._json_key_field = ""
        self._json_structure = ""

        # split/join state
        self.sj_folder = ctk.StringVar()
        self.sj_merged = ctk.StringVar()
        self.sj_output = ctk.StringVar()

        self._build_ui()

    # ── helpers ───────────────────────────────────────

    def _card(self, parent, title, **kwargs):
        card = ctk.CTkFrame(parent, corner_radius=8, border_width=1, **kwargs)
        card.grid_columnconfigure(0, weight=1)
        if title:
            lbl = ctk.CTkLabel(card, text=title, font=FONT_CARD, text_color=ACCENT)
            lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))
        return card

    def _sep(self, parent):
        ctk.CTkFrame(parent, width=1, height=18, fg_color=("gray60", "gray40")).pack(side="left", padx=8)

    # ── build UI ──────────────────────────────────────

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # tab view
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 6))
        self.tabview.add("🔑 Key Matcher")
        self.tabview.add("📦 Split & Join")
        self.tabview.set("🔑 Key Matcher")

        self._build_matcher_tab(self.tabview.tab("🔑 Key Matcher"))
        self._build_splitjoin_tab(self.tabview.tab("📦 Split & Join"))

    # ── MATCHER TAB ───────────────────────────────────

    def _build_matcher_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=2, pady=2)
        main.grid_rowconfigure(5, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # header bar
        hbar = ctk.CTkFrame(main, corner_radius=8, fg_color=("gray20", "gray10"))
        hbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        hbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hbar, text="🔑  Key Matcher",
                     font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT).grid(row=0, column=0, padx=18, pady=12, sticky="w")
        ctk.CTkLabel(hbar, text="จับคู่ Key-Value ระหว่างไฟล์",
                     font=("Segoe UI", 10),
                     text_color=("gray50", "gray60")).grid(row=0, column=1, padx=4, pady=12, sticky="w")

        self.theme_switch = ctk.CTkSwitch(
            hbar, text="🌙  Dark", command=self._toggle_theme,
            onvalue="dark", offvalue="light",
            variable=ctk.StringVar(value="dark"))
        self.theme_switch.grid(row=0, column=2, padx=(0, 14), pady=12)
        self.theme_switch.select()

        p4 = {"padx": 6, "pady": 4}

        # card: file selection
        fcard = self._card(main, "📁  เลือกไฟล์")
        fcard.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        fcard.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fcard, text="Base (อ้างอิง key):", width=130, anchor="e").grid(row=1, column=0, sticky="e", **p4)
        ctk.CTkEntry(fcard, textvariable=self.base_path, height=34).grid(row=1, column=1, sticky="ew", **p4)
        ctk.CTkButton(fcard, text="📂 Browse", width=90, height=34,
                      command=self._browse_base).grid(row=1, column=2, padx=(6, 10), pady=4)

        ctk.CTkLabel(fcard, text="Target (ดึง value):", width=130, anchor="e").grid(row=2, column=0, sticky="e", **p4)
        ctk.CTkEntry(fcard, textvariable=self.target_path, height=34).grid(row=2, column=1, sticky="ew", **p4)
        ctk.CTkButton(fcard, text="📂 Browse", width=90, height=34,
                      command=self._browse_target).grid(row=2, column=2, padx=(6, 10), pady=4)

        # card: format config
        self.config_card = self._card(main, "⚙  ตั้งค่ารูปแบบไฟล์")
        self.config_card.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.config_card.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(self.config_card, text="Game:").grid(row=1, column=0, sticky="w", padx=6, pady=(2, 0))
        self.preset_menu = ctk.CTkOptionMenu(self.config_card, variable=self.preset_var,
                          values=list(self._presets.keys()), width=200,
                          command=self._apply_preset)
        self.preset_menu.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(2, 0))
        ctk.CTkButton(self.config_card, text="+ Save", width=60, height=24,
                      font=("Segoe UI", 9),
                      command=self._save_preset_dialog).grid(row=1, column=5, sticky="e", padx=(0, 6), pady=(2, 0))

        ctk.CTkLabel(self.config_card, text="Format:").grid(row=2, column=0, sticky="w", **p4)
        ctk.CTkOptionMenu(self.config_card, variable=self.format_var,
                          values=["txt", "csv", "json", "xml"], width=80,
                          command=lambda _: self._update_config_panel()).grid(row=2, column=1, sticky="w", **p4)

        self.delim_label = ctk.CTkLabel(self.config_card, text="Delimiter:")
        self.delim_label.grid(row=2, column=2, sticky="e", **p4)
        self.delim_combo = ctk.CTkComboBox(self.config_card, variable=self.delimiter_var,
                                           values=["|", "=", ":", "\t", ",", " -> "], width=90)
        self.delim_combo.grid(row=2, column=3, sticky="w", **p4)

        ctk.CTkLabel(self.config_card, text="Encoding:").grid(row=2, column=4, sticky="e", **p4)
        ctk.CTkOptionMenu(self.config_card, variable=self.encoding_var,
                          values=["utf-8", "utf-8-sig", "utf-16", "cp874", "tis-620", "latin-1"],
                          width=100).grid(row=2, column=5, sticky="w", **p4)

        self.dynamic_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.dynamic_frame.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(8, 2))
        self._update_config_panel()

        # card: manual keys
        mcard = self._card(main, "✚  เพิ่ม Key เอง")
        mcard.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        mcard.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(mcard, textvariable=self.manual_keys,
                     placeholder_text="คั่นด้วย , ; หรือเว้นวรรค").grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 10))

        # action bar
        abar = ctk.CTkFrame(main, fg_color="transparent")
        abar.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        abar.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(abar, text="🔍  MATCH & PREVIEW", width=180, height=36,
                      font=("Segoe UI", 11, "bold"),
                      command=self._do_match).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(abar, text="💾  SAVE", width=120, height=36,
                      font=("Segoe UI", 11, "bold"),
                      fg_color="transparent", border_width=2,
                      text_color=ACCENT, border_color=ACCENT,
                      hover_color=(ACCENT, ACCENT_DARK),
                      command=self._do_save).grid(row=0, column=1, padx=(0, 14))

        self.progress = ctk.CTkProgressBar(abar, width=140, height=10, mode="determinate")
        self.progress.grid(row=0, column=2, padx=(0, 8))
        self.progress.set(0)

        self.stats_label = ctk.CTkLabel(abar, text="", font=("Segoe UI", 10),
                                        text_color=("gray50", "gray60"))
        self.stats_label.grid(row=0, column=3, sticky="w")

        # card: preview
        pcard = self._card(main, "👁  Preview (50 บรรทัดแรก)")
        pcard.grid(row=5, column=0, sticky="nsew", pady=(0, 6))
        pcard.grid_rowconfigure(1, weight=1)
        pcard.grid_columnconfigure(0, weight=1)

        self.preview_text = ctk.CTkTextbox(pcard, font=FONT_MONO,
                                           fg_color=("gray10", "#11121d"),
                                           text_color=("#d4d6e2", "#cdd6f4"),
                                           wrap="word", activate_scrollbars=True)
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=14, pady=(2, 10))
        self.preview_text.insert("0.0", "กด Match & Preview เพื่อดูผลลัพธ์\n")
        self.preview_text.configure(state="disabled")

        # status bar
        sbar = ctk.CTkFrame(main, corner_radius=4, fg_color=("gray90", "gray13"))
        sbar.grid(row=6, column=0, sticky="ew")
        self.status_label = ctk.CTkLabel(sbar, text="✅  พร้อมใช้งาน", font=("Segoe UI", 9),
                                         text_color=("gray50", "gray60"))
        self.status_label.pack(side="left", padx=14, pady=4)

    # ── SPLIT & JOIN TAB ──────────────────────────────

    def _build_splitjoin_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=2, pady=2)
        main.grid_rowconfigure(4, weight=1)
        main.grid_columnconfigure(0, weight=1)

        pad = {"padx": 6, "pady": 4}

        # header
        hbar = ctk.CTkFrame(main, corner_radius=8, fg_color=("gray20", "gray10"))
        hbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hbar, text="📦  Split & Join — รวม/แยกไฟล์ .txt",
                     font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT).grid(row=0, column=0, padx=18, pady=12, sticky="w")
        ctk.CTkLabel(hbar, text="รวมไฟล์หลายไฟล์เป็นไฟล์เดียวเพื่อแปล แล้วแยกกลับ",
                     font=("Segoe UI", 10),
                     text_color=("gray50", "gray60")).grid(row=0, column=1, padx=4, pady=12, sticky="w")

        # ── Merge section ──
        mcard = self._card(main, "🧩  Merge — รวม .txt ทั้งโฟลเดอร์เป็นไฟล์เดียว")
        mcard.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        mcard.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(mcard, text="Input folder:").grid(row=1, column=0, sticky="e", **pad)
        ctk.CTkEntry(mcard, textvariable=self.sj_folder, height=34).grid(row=1, column=1, sticky="ew", **pad)
        ctk.CTkButton(mcard, text="📂 Browse", width=90, height=34,
                      command=self._browse_merge_folder).grid(row=1, column=2, padx=(6, 10), pady=4)

        ctk.CTkLabel(mcard, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
        ctk.CTkEntry(mcard, textvariable=self.sj_merged, height=34).grid(row=2, column=1, sticky="ew", **pad)
        ctk.CTkButton(mcard, text="📂 Save As", width=90, height=34,
                      command=self._browse_merge_output).grid(row=2, column=2, padx=(6, 10), pady=4)

        ctk.CTkButton(mcard, text="🔀  MERGE", width=140, height=34,
                      font=("Segoe UI", 10, "bold"),
                      command=self._do_merge).grid(row=3, column=1, pady=(4, 10))

        # ── Split section ──
        scard = self._card(main, "✂  Split — แยกไฟล์รวมกลับเป็น .txt")
        scard.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        scard.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(scard, text="Merged file:").grid(row=1, column=0, sticky="e", **pad)
        ctk.CTkEntry(scard, textvariable=self.sj_merged, height=34).grid(row=1, column=1, sticky="ew", **pad)
        ctk.CTkButton(scard, text="📂 Browse", width=90, height=34,
                      command=self._browse_split_input).grid(row=1, column=2, padx=(6, 10), pady=4)

        ctk.CTkLabel(scard, text="Output folder:").grid(row=2, column=0, sticky="e", **pad)
        ctk.CTkEntry(scard, textvariable=self.sj_output, height=34).grid(row=2, column=1, sticky="ew", **pad)
        ctk.CTkButton(scard, text="📂 Browse", width=90, height=34,
                      command=self._browse_split_output).grid(row=2, column=2, padx=(6, 10), pady=4)

        ctk.CTkButton(scard, text="✂  SPLIT", width=140, height=34,
                      font=("Segoe UI", 10, "bold"),
                      command=self._do_split).grid(row=3, column=1, pady=(4, 10))

        # ── preview area (shared) ──
        pcard = self._card(main, "👁  Preview")
        pcard.grid(row=4, column=0, sticky="nsew")
        pcard.grid_rowconfigure(1, weight=1)
        pcard.grid_columnconfigure(0, weight=1)

        self.sj_preview = ctk.CTkTextbox(pcard, font=FONT_MONO,
                                         fg_color=("gray10", "#11121d"),
                                         text_color=("#d4d6e2", "#cdd6f4"),
                                         wrap="word", activate_scrollbars=True)
        self.sj_preview.grid(row=1, column=0, sticky="nsew", padx=14, pady=(2, 10))
        self.sj_preview.insert("0.0", "เลือกโฟลเดอร์แล้วกด Merge หรือ Split เพื่อดูตัวอย่าง\n")
        self.sj_preview.configure(state="disabled")

        # status
        sbar = ctk.CTkFrame(main, corner_radius=4, fg_color=("gray90", "gray13"))
        sbar.grid(row=5, column=0, sticky="ew")
        self.sj_status = ctk.CTkLabel(sbar, text="✅  พร้อมใช้งาน", font=("Segoe UI", 9),
                                      text_color=("gray50", "gray60"))
        self.sj_status.pack(side="left", padx=14, pady=4)

    # ── Split & Join actions ──────────────────────────

    def _browse_merge_folder(self):
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่มี .txt")
        if path:
            self.sj_folder.set(path)
            self.sj_status.configure(text=f"📁 {path}")

    def _browse_merge_output(self):
        path = filedialog.asksaveasfilename(
            title="บันทึกไฟล์รวม", defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.sj_merged.set(path)

    def _browse_split_input(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์รวม", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.sj_merged.set(path)
            self.sj_status.configure(text=f"📄 {os.path.basename(path)}")

    def _browse_split_output(self):
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if path:
            self.sj_output.set(path)

    def _do_merge(self):
        folder = self.sj_folder.get().strip()
        out = self.sj_merged.get().strip()
        if not folder or not out:
            messagebox.showwarning("กรุณากรอกข้อมูล", "ต้องระบุทั้ง Input folder และ Output file")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("ไม่พบโฟลเดอร์", f"ไม่พบ: {folder}")
            return
        try:
            n = merge_txt_folder(folder, out, self.encoding_var.get())
            with open(out, "r", encoding=self.encoding_var.get()) as f:
                preview = "".join(f.readlines()[:20])
            self.sj_preview.configure(state="normal")
            self.sj_preview.delete("0.0", "end")
            self.sj_preview.insert("0.0", preview)
            self.sj_preview.configure(state="disabled")
            self.sj_status.configure(text=f"✅  Merge สำเร็จ: {n} ไฟล์ → {out}")
            messagebox.showinfo("Merge สำเร็จ", f"รวมแล้ว {n} ไฟล์\n{out}")
        except Exception as e:
            messagebox.showerror("ผิดพลาด", str(e))

    def _do_split(self):
        merged = self.sj_merged.get().strip()
        outdir = self.sj_output.get().strip()
        if not merged or not outdir:
            messagebox.showwarning("กรุณากรอกข้อมูล", "ต้องระบุทั้ง Merged file และ Output folder")
            return
        if not os.path.isfile(merged):
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบ: {merged}")
            return
        try:
            n = split_merged_txt(merged, outdir, self.encoding_var.get())
            self.sj_preview.configure(state="normal")
            self.sj_preview.delete("0.0", "end")
            files = sorted(os.listdir(outdir))[:30]
            self.sj_preview.insert("0.0", f"แยกแล้ว {n} ไฟล์:\n" + "\n".join(files))
            if n > 30:
                self.sj_preview.insert("end", f"\n... และอีก {n - 30} ไฟล์")
            self.sj_preview.configure(state="disabled")
            self.sj_status.configure(text=f"✅  Split สำเร็จ: {n} ไฟล์ → {outdir}")
            messagebox.showinfo("Split สำเร็จ", f"แยกแล้ว {n} ไฟล์\n{outdir}")
        except Exception as e:
            messagebox.showerror("ผิดพลาด", str(e))

    # ── theme toggle ──────────────────────────────────

    def _toggle_theme(self):
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)
        self.theme_switch.configure(text="🌙  Dark" if mode == "dark" else "☀  Light")

    # ── presets ───────────────────────────────────────

    def _load_presets(self):
        if os.path.exists(self._presets_file):
            try:
                with open(self._presets_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "Auto": {},
            "Crimson Desert (PALOC)": {
                "fmt": "json", "structure": "array",
                "key_field": "key", "val_field": "translation", "src_field": "",
            },
            "Crimson Desert (EN/TH)": {
                "fmt": "json", "structure": "array",
                "key_field": "key", "val_field": "translation", "src_field": "original",
            },
        }

    def _save_presets(self):
        with open(self._presets_file, "w", encoding="utf-8") as f:
            json.dump(self._presets, f, ensure_ascii=False, indent=2)

    def _refresh_preset_menu(self):
        names = list(self._presets.keys())
        self.preset_menu.configure(values=names)

    def _save_preset_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Save Game Preset")
        dialog.geometry("360x140")
        dialog.configure(fg_color=("gray20", "gray10"))
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="ชื่อเกม / Preset name:").pack(pady=(14, 2))
        name_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=name_var, width=300).pack(padx=20)

        def do_save():
            name = name_var.get().strip()
            if not name:
                return
            self._presets[name] = {
                "fmt": self.format_var.get(),
                "structure": self.json_structure.get(),
                "key_field": self.json_key_field.get(),
                "val_field": self.json_val_field.get(),
                "src_field": self.json_src_field.get(),
            }
            self._save_presets()
            self._refresh_preset_menu()
            self.preset_var.set(name)
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save", command=do_save).pack(pady=(8, 4))
        dialog.bind("<Return>", lambda e: do_save())

    def _apply_preset(self, choice):
        preset = self._presets.get(choice, {})
        if not preset:
            return
        if "fmt" in preset:
            self.format_var.set(preset["fmt"])
        if "structure" in preset:
            self.json_structure.set(preset["structure"])
        if "key_field" in preset:
            self.json_key_field.set(preset["key_field"])
        if "val_field" in preset:
            self.json_val_field.set(preset["val_field"])
        if "src_field" in preset:
            self.json_src_field.set(preset["src_field"])
        self._update_config_panel()

    # ── matcher config panel ──────────────────────────

    def _update_config_panel(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        fmt = self.format_var.get()
        if fmt in ("json", "xml"):
            self.delim_label.grid_remove()
            self.delim_combo.grid_remove()
        else:
            self.delim_label.grid()
            self.delim_combo.grid()

        p = {"padx": 4, "pady": 2}
        if fmt == "txt":
            ctk.CTkLabel(self.dynamic_frame, text="Delimiter:").pack(side="left", **p)
            ctk.CTkComboBox(self.dynamic_frame, variable=self.delimiter_var,
                            values=["|", "=", ":", "\t", ",", " -> ", "custom..."],
                            width=100).pack(side="left", **p)
            self._sep(self.dynamic_frame)
            ctk.CTkCheckBox(self.dynamic_frame, text="Alt lines (*ID*\\ntext)",
                            variable=self.txt_alt_lines).pack(side="left", **p)
        elif fmt == "csv":
            ctk.CTkLabel(self.dynamic_frame, text="Delim:").pack(side="left", **p)
            ctk.CTkComboBox(self.dynamic_frame, variable=self.delimiter_var,
                            values=[",", ";", "\t", "|"], width=70).pack(side="left", **p)
            self._sep(self.dynamic_frame)
            ctk.CTkLabel(self.dynamic_frame, text="Key Col:").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.csv_key_col, width=42).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="Value Col:").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.csv_val_col, width=42).pack(side="left", **p)
            self._sep(self.dynamic_frame)
            ctk.CTkCheckBox(self.dynamic_frame, text="มี Header", variable=self.csv_has_header).pack(side="left", **p)
        elif fmt == "json":
            ctk.CTkLabel(self.dynamic_frame, text="โครงสร้าง:").pack(side="left", **p)
            ctk.CTkOptionMenu(self.dynamic_frame, variable=self.json_structure,
                              values=["array", "object"], width=80).pack(side="left", **p)
            self._sep(self.dynamic_frame)
            ctk.CTkLabel(self.dynamic_frame, text="Key field:").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.json_key_field, width=60).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="Value (write):").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.json_val_field, width=60).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="Source (read):").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.json_src_field, width=60).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="(src ว่าง = อ่านจาก value)",
                         font=("Segoe UI", 9), text_color=("gray40", "gray60")).pack(side="left", **p)
        elif fmt == "xml":
            ctk.CTkLabel(self.dynamic_frame, text="Item tag:").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.xml_item_tag, width=80).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="Key attr:").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.xml_key_attr, width=80).pack(side="left", **p)
            ctk.CTkLabel(self.dynamic_frame, text="Value attr (#text=เนื้อหา):").pack(side="left", **p)
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.xml_val_attr, width=80).pack(side="left", **p)

    # ── browse ────────────────────────────────────────

    def _browse_base(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ Base",
            filetypes=[("All supported", "*.txt;*.csv;*.json;*.xml"),
                       ("Text files", "*.txt"), ("CSV files", "*.csv"),
                       ("JSON files", "*.json"), ("XML files", "*.xml"),
                       ("All files", "*.*")])
        if path:
            self.base_path.set(path)
            self._auto_detect(path)
            self.status_label.configure(text=f"📄 Base: {os.path.basename(path)}")

    def _browse_target(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ Target",
            filetypes=[("All supported", "*.txt;*.csv;*.json;*.xml"),
                       ("Text files", "*.txt"), ("CSV files", "*.csv"),
                       ("JSON files", "*.json"), ("XML files", "*.xml"),
                       ("All files", "*.*")])
        if path:
            self.target_path.set(path)
            self.status_label.configure(text=f"📄 Target: {os.path.basename(path)}")

    def _auto_detect(self, path):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ("txt", "csv", "json", "xml"):
            self.format_var.set(ext)
            self._update_config_panel()

    def _auto_output_path(self):
        base = self.base_path.get().strip()
        if not base:
            return ""
        folder = os.path.dirname(base)
        name, ext = os.path.splitext(os.path.basename(base))
        return os.path.join(folder, f"{name}_matched{ext}")

    # ── parse ─────────────────────────────────────────

    def _parse_file(self, path):
        fmt = self.format_var.get()
        enc = self.encoding_var.get()
        if fmt == "txt":
            return parse_txt(path, self.delimiter_var.get(), enc,
                           alt_lines=self.txt_alt_lines.get())
        elif fmt == "csv":
            return parse_csv_file(path,
                                  key_col=int(self.csv_key_col.get()),
                                  val_col=int(self.csv_val_col.get()),
                                  delimiter=self.delimiter_var.get(),
                                  has_header=self.csv_has_header.get(),
                                  encoding=enc)
        elif fmt == "json":
            src = self.json_src_field.get().strip()
            data, is_wrapped, orig_struct = parse_json_file(path,
                                   key_field=self.json_key_field.get(),
                                   val_field=self.json_val_field.get(),
                                   structure=self.json_structure.get(),
                                   encoding=enc,
                                   src_field=src if src else None)
            self._json_original = orig_struct
            self._json_val_field = self.json_val_field.get()
            self._json_key_field = self.json_key_field.get()
            self._json_structure = self.json_structure.get()
            return data
        elif fmt == "xml":
            data, is_merged, line_struct = parse_xml_file(path,
                                  item_tag=self.xml_item_tag.get(),
                                  key_attr=self.xml_key_attr.get(),
                                  val_attr=self.xml_val_attr.get(),
                                  encoding=enc)
            self._xml_is_merged = is_merged
            self._xml_line_struct = line_struct
            self._xml_item_tag = self.xml_item_tag.get()
            self._xml_key_attr = self.xml_key_attr.get()
            return data
        else:
            raise ValueError(f"Unknown format: {fmt}")

    # ── match ─────────────────────────────────────────

    def _do_match(self):
        base_path = self.base_path.get().strip()
        target_path = self.target_path.get().strip()
        if not base_path or not target_path:
            messagebox.showwarning("กรุณาเลือกไฟล์", "ต้องเลือกทั้งไฟล์ Base และ Target")
            return
        if not os.path.exists(base_path):
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบ Base:\n{base_path}")
            return
        if not os.path.exists(target_path):
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบ Target:\n{target_path}")
            return

        self.status_label.configure(text="⏳ กำลังอ่านไฟล์...")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.root.update_idletasks()

        try:
            base_dict = self._parse_file(base_path)
            json_struct = getattr(self, '_json_original', None)
            target_dict = self._parse_file(target_path)
            self._json_original = json_struct

            manual = self.manual_keys.get().strip()
            manual_added = 0
            if manual:
                for k in re.split(r"[,;\s]+", manual):
                    k = k.strip()
                    if k and k not in base_dict:
                        base_dict[k] = ""
                        manual_added += 1

            merged, n_match, n_unmatch, n_garbled, n_total = match_keys(base_dict, target_dict)
            self.merged_data = merged
            pct = ((n_match + n_garbled) / n_total * 100) if n_total > 0 else 0

            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(pct / 100)

            if pct >= 95:
                color = GREEN
            elif pct >= 70:
                color = YELLOW
            else:
                color = RED

            parts = [f"จับคู่ {n_match}/{n_total} ({pct:.1f}%)"]
            if n_garbled > 0:
                parts.append(f"ข้ามข้อความเพี้ยน {n_garbled}")
            if n_unmatch > 0:
                parts.append(f"ไม่พบ {n_unmatch}")
            if manual_added > 0:
                parts.append(f"เพิ่มเอง {manual_added}")

            self.stats_label.configure(text="  │  ".join(parts), text_color=color)
            self.progress.configure(progress_color=color)
            self.status_label.configure(text=f"✅  จับคู่แล้ว {n_match:,} keys — พร้อมบันทึก")
            self._show_preview(merged)

        except Exception as e:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(0)
            self.stats_label.configure(text="เกิดข้อผิดพลาด", text_color=RED)
            messagebox.showerror("เกิดข้อผิดพลาด", f"{type(e).__name__}:\n{e}")
            self.status_label.configure(text=f"❌ Error: {e}")

    def _show_preview(self, data):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        delimiter = self.delimiter_var.get()
        fmt = self.format_var.get()
        lines = list(data.items())
        for i, (key, val) in enumerate(lines):
            if i >= 50:
                self.preview_text.insert("end",
                    f"\n⋯  อีก {len(lines) - 50:,} บรรทัด  (กด 💾 Save เพื่อบันทึกทั้งหมด)\n")
                break
            if fmt == "txt":
                self.preview_text.insert("end", f"{key}{delimiter}{val}\n")
            else:
                self.preview_text.insert("end", f"{key}  →  {val}\n")
        self.preview_text.configure(state="disabled")

    # ── save ──────────────────────────────────────────

    def _do_save(self):
        if self.merged_data is None:
            messagebox.showwarning("ยังไม่มีข้อมูล", "กรุณากด Match & Preview ก่อน")
            return
        default_path = self._auto_output_path()
        fmt = self.format_var.get()
        ext_map = {"txt": ".txt", "csv": ".csv", "json": ".json", "xml": ".xml"}
        default_ext = ext_map.get(fmt, ".txt")
        path = filedialog.asksaveasfilename(
            title="บันทึกไฟล์ผลลัพธ์",
            initialfile=os.path.basename(default_path) if default_path else f"output{default_ext}",
            initialdir=os.path.dirname(default_path) if default_path else "",
            defaultextension=default_ext,
            filetypes=[(f"{fmt.upper()} files", f"*{default_ext}"), ("All files", "*.*")])
        if not path:
            return
        enc = self.encoding_var.get()
        try:
            if fmt == "txt":
                write_txt(self.merged_data, path, self.delimiter_var.get(), enc)
            elif fmt == "csv":
                write_csv_file(self.merged_data, path,
                               delimiter=self.delimiter_var.get(), encoding=enc)
            elif fmt == "json":
                write_json_file(self.merged_data, path,
                                structure=self._json_structure,
                                key_field=self._json_key_field,
                                val_field=self._json_val_field,
                                original_structure=self._json_original,
                                encoding=enc)
            elif fmt == "xml":
                if self._xml_is_merged:
                    write_xml_fragments(self.merged_data, self._xml_line_struct, path,
                                        item_tag=self._xml_item_tag,
                                        key_attr=self._xml_key_attr,
                                        encoding=enc)
                else:
                    write_xml_file(self.merged_data, path,
                                   item_tag=self.xml_item_tag.get(),
                                   key_attr=self.xml_key_attr.get(),
                                   val_attr=self.xml_val_attr.get(),
                                   encoding=enc)
            self.status_label.configure(text=f"💾  บันทึกแล้ว: {path}")
            messagebox.showinfo("บันทึกสำเร็จ",
                                f"บันทึกแล้ว:\n{path}\n\n📊 {len(self.merged_data):,} keys")
        except Exception as e:
            messagebox.showerror("บันทึกไม่สำเร็จ", f"{type(e).__name__}:\n{e}")
            self.status_label.configure(text=f"❌ บันทึกไม่สำเร็จ: {e}")

# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = ctk.CTk()
    app = KeyMatcherApp(root)
    root.mainloop()
