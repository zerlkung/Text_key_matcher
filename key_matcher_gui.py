#!/usr/bin/env python
"""
Key Matcher GUI — จับคู่ key-value ระหว่าง 2 ไฟล์
รองรับ .txt .csv .json .xml
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import OrderedDict
import csv
import json
import xml.etree.ElementTree as ET
import os
import re

# ═══════════════════════════════════════════════════════════
# Dark theme palette — สบายตา อ่านชัด
# ═══════════════════════════════════════════════════════════

BG_MAIN      = "#13141f"   # พื้นหลังหลัก
BG_CARD      = "#1c1d2e"   # พื้นการ์ด
BG_HEADER    = "#0f1019"   # แถบหัว
FG_HEADER    = "#e4e6f0"
ACCENT       = "#7c8cf8"   # ม่วง-น้ำเงิน (ปุ่มหลัก)
ACCENT_HOVER = "#96a5ff"
SUCCESS      = "#4ade80"   # เขียว
WARNING      = "#fbbf24"   # เหลือง
DANGER       = "#f87171"   # แดง
TEXT_MAIN    = "#d4d6e2"   # ข้อความหลัก
TEXT_MUTED   = "#7f82a0"   # ข้อความรอง
TEXT_HINT    = "#5b5e7a"   # ข้อความจาง
BORDER       = "#2e3048"   # เส้นขอบ
PREVIEW_BG   = "#11121d"   # พื้น preview
PREVIEW_FG   = "#cdd6f4"   # ข้อความ preview
STATUS_BG    = "#171824"   # แถบสถานะ
ENTRY_BG     = "#232439"   # พื้น input
ENTRY_FG     = "#d4d6e2"   # ข้อความ input

FONT_UI      = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO    = ("Cascadia Code", 10)

# ═══════════════════════════════════════════════════════════
# Parsers
# ═══════════════════════════════════════════════════════════

def parse_txt(path, delimiter="|", encoding="utf-8"):
    result = OrderedDict()
    with open(path, "r", encoding=encoding) as f:
        for line in f:
            line = line.rstrip("\n\r")
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
                key = row[key_col].strip()
                val = row[val_col].strip() if len(row) > val_col else ""
                result[key] = val
    return result

def write_csv_file(data, path, key_header="key", val_header="value",
                   delimiter=",", encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow([key_header, val_header])
        for key, val in data.items():
            writer.writerow([key, val])

def parse_json_file(path, key_field="id", val_field="value", structure="array", encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        raw = json.load(f)
    result = OrderedDict()
    if structure == "object":
        if isinstance(raw, dict):
            for k, v in raw.items():
                result[str(k)] = str(v) if v is not None else ""
    else:
        if isinstance(raw, list):
            for item in raw:
                k = item.get(key_field)
                v = item.get(val_field, "")
                if k is not None:
                    result[str(k)] = str(v) if v is not None else ""
    return result

def write_json_file(data, path, structure="array", key_field="id",
                    val_field="value", encoding="utf-8"):
    out = dict(data) if structure == "object" else [
        {key_field: k, val_field: v} for k, v in data.items()]
    with open(path, "w", encoding=encoding) as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def parse_xml_file(path, item_tag="string", key_attr="id", val_attr="#text", encoding="utf-8"):
    result = OrderedDict()
    tree = ET.parse(path)
    root = tree.getroot()
    for elem in root.iter(item_tag):
        key = elem.tag if key_attr == "#tag" else elem.get(key_attr)
        if key is None:
            key = elem.tag
        val = (elem.text or "") if val_attr == "#text" else elem.get(val_attr, "")
        result[key] = val
    return result

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

# ═══════════════════════════════════════════════════════════
# Matcher
# ═══════════════════════════════════════════════════════════

def match_keys(base_dict, target_dict):
    result = OrderedDict()
    matched = unmatched = 0
    for key, base_val in base_dict.items():
        if key in target_dict:
            result[key] = target_dict[key]
            matched += 1
        else:
            result[key] = base_val
            unmatched += 1
    return result, matched, unmatched, len(base_dict)

# ═══════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════

class KeyMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Key Matcher")
        self.root.geometry("1000x780")
        self.root.minsize(720, 560)
        self.root.configure(bg=BG_MAIN)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # state
        self.base_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.format_var = tk.StringVar(value="txt")
        self.delimiter_var = tk.StringVar(value="|")
        self.encoding_var = tk.StringVar(value="utf-8")
        self.csv_key_col = tk.StringVar(value="0")
        self.csv_val_col = tk.StringVar(value="1")
        self.csv_has_header = tk.BooleanVar(value=True)
        self.json_structure = tk.StringVar(value="array")
        self.json_key_field = tk.StringVar(value="id")
        self.json_val_field = tk.StringVar(value="value")
        self.xml_item_tag = tk.StringVar(value="string")
        self.xml_key_attr = tk.StringVar(value="id")
        self.xml_val_attr = tk.StringVar(value="#text")
        self.manual_keys = tk.StringVar()
        self.merged_data = None

        self._setup_styles()
        self._build_ui()

    # ── styles ────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # --- global defaults ---
        style.configure(".", font=FONT_UI, background=BG_CARD, foreground=TEXT_MAIN,
                        fieldbackground=ENTRY_BG, bordercolor=BORDER,
                        troughcolor=BG_MAIN, arrowcolor=TEXT_MUTED)

        # --- Card LabelFrame ---
        style.configure("Card.TLabelframe", background=BG_CARD, bordercolor=BORDER,
                        borderwidth=1, relief="solid", labelmargins=(10, 4))
        style.configure("Card.TLabelframe.Label", font=FONT_UI_BOLD, foreground=ACCENT,
                        background=BG_CARD)

        # --- Entry ---
        style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=ENTRY_FG,
                        bordercolor=BORDER, padding=5, relief="solid",
                        insertcolor=ENTRY_FG, insertwidth=1)
        style.map("TEntry", fieldbackground=[("focus", "#2a2c42")],
                  bordercolor=[("focus", ACCENT)])

        # --- Combobox ---
        style.configure("TCombobox", fieldbackground=ENTRY_BG, foreground=ENTRY_FG,
                        bordercolor=BORDER, arrowcolor=TEXT_MUTED, padding=4)
        style.map("TCombobox", fieldbackground=[("focus", "#2a2c42"), ("readonly", ENTRY_BG)],
                  bordercolor=[("focus", ACCENT)])

        # override combobox dropdown colors via root
        self.root.option_add("*TCombobox*Listbox.background", ENTRY_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT_MAIN)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", FONT_UI)

        # --- Accent button (primary) ---
        style.configure("Accent.TButton", font=FONT_UI_BOLD,
                        background=ACCENT, foreground="#ffffff",
                        bordercolor=ACCENT, borderwidth=0,
                        padding=(22, 7), relief="flat")
        style.map("Accent.TButton",
                  background=[("active", ACCENT_HOVER), ("!disabled", ACCENT)],
                  foreground=[("active", "#ffffff")])

        # --- Secondary button (outline) ---
        style.configure("Secondary.TButton", font=FONT_UI_BOLD,
                        background=BG_CARD, foreground=ACCENT,
                        bordercolor=ACCENT, borderwidth=1,
                        padding=(18, 7), relief="solid")
        style.map("Secondary.TButton",
                  background=[("active", "#252740")],
                  foreground=[("active", ACCENT_HOVER)])

        # --- Small browse button ---
        style.configure("Small.TButton", font=FONT_UI,
                        background=BG_MAIN, foreground=TEXT_MAIN,
                        bordercolor=BORDER, borderwidth=1,
                        padding=(10, 5), relief="solid")
        style.map("Small.TButton",
                  background=[("active", "#252740")])

        # --- Progress bar ---
        style.configure("TProgressbar", background=SUCCESS, troughcolor=BG_MAIN,
                        borderwidth=0, thickness=8)

        # --- Checkbutton ---
        style.configure("TCheckbutton", background=BG_CARD, foreground=TEXT_MAIN)
        style.map("TCheckbutton", background=[("active", BG_CARD)])

        # --- Label ---
        style.configure("TLabel", background=BG_CARD, foreground=TEXT_MAIN)

        # --- Separator ---
        style.configure("TSeparator", background=BORDER)

        # --- Vertical scrollbar ---
        style.configure("Vertical.TScrollbar", background=BG_MAIN, troughcolor=BG_MAIN,
                        bordercolor=BG_MAIN, arrowcolor=TEXT_MUTED, width=10)
        style.map("Vertical.TScrollbar", background=[("active", BORDER)])

    # ── build ─────────────────────────────────────────

    def _build_ui(self):
        p4 = {"padx": 6, "pady": 4}

        main = tk.Frame(self.root, bg=BG_MAIN)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(5, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # ── header ──
        header = tk.Frame(main, bg=BG_HEADER, height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        tk.Label(header, text=" 🔑  Key Matcher", font=("Segoe UI", 14, "bold"),
                 fg=FG_HEADER, bg=BG_HEADER).grid(row=0, column=0, padx=16, pady=10, sticky="w")
        tk.Label(header, text="จับคู่ Key-Value ระหว่างไฟล์",
                 font=FONT_UI, fg=TEXT_MUTED, bg=BG_HEADER).grid(row=0, column=1, padx=4, pady=10, sticky="w")

        # ── card: file selection ──
        fcard = ttk.LabelFrame(main, text="📁  เลือกไฟล์", style="Card.TLabelframe", padding=10)
        fcard.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 6))
        fcard.grid_columnconfigure(1, weight=1)

        ttk.Label(fcard, text="Base (อ้างอิง key):").grid(row=0, column=0, sticky="e", **p4)
        ttk.Entry(fcard, textvariable=self.base_path).grid(row=0, column=1, sticky="ew", **p4)
        ttk.Button(fcard, text="📂 Browse", style="Small.TButton",
                   command=self._browse_base).grid(row=0, column=2, **p4)

        ttk.Label(fcard, text="Target (ดึง value):").grid(row=1, column=0, sticky="e", **p4)
        ttk.Entry(fcard, textvariable=self.target_path).grid(row=1, column=1, sticky="ew", **p4)
        ttk.Button(fcard, text="📂 Browse", style="Small.TButton",
                   command=self._browse_target).grid(row=1, column=2, **p4)

        # ── card: format config ──
        self.config_card = ttk.LabelFrame(main, text="⚙  ตั้งค่ารูปแบบไฟล์", style="Card.TLabelframe", padding=10)
        self.config_card.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.config_card.grid_columnconfigure(5, weight=1)

        ttk.Label(self.config_card, text="Format:").grid(row=0, column=0, sticky="w", **p4)
        fmt_combo = ttk.Combobox(self.config_card, textvariable=self.format_var,
                                 values=["txt", "csv", "json", "xml"], state="readonly", width=8)
        fmt_combo.grid(row=0, column=1, sticky="w", **p4)
        fmt_combo.bind("<<ComboboxSelected>>", lambda e: self._update_config_panel())

        ttk.Label(self.config_card, text="Delimiter:").grid(row=0, column=2, sticky="e", **p4)
        self.delim_combo = ttk.Combobox(self.config_card, textvariable=self.delimiter_var,
                                        values=["|", "=", ":", "\t", ",", " -> "], width=8)
        self.delim_combo.grid(row=0, column=3, sticky="w", **p4)

        ttk.Label(self.config_card, text="Encoding:").grid(row=0, column=4, sticky="e", **p4)
        ttk.Combobox(self.config_card, textvariable=self.encoding_var,
                     values=["utf-8", "utf-8-sig", "utf-16", "cp874", "tis-620", "latin-1"],
                     width=10).grid(row=0, column=5, sticky="w", **p4)

        # dynamic sub-row
        self.dynamic_frame = tk.Frame(self.config_card, bg=BG_CARD)
        self.dynamic_frame.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(6, 0))
        self._update_config_panel()

        # ── card: manual keys ──
        mcard = ttk.LabelFrame(main, text="✚  เพิ่ม Key เอง (คั่นด้วย , ; หรือเว้นวรรค)", style="Card.TLabelframe", padding=10)
        mcard.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        mcard.grid_columnconfigure(0, weight=1)
        ttk.Entry(mcard, textvariable=self.manual_keys).grid(row=0, column=0, sticky="ew")

        # ── action bar ──
        abar = tk.Frame(main, bg=BG_MAIN)
        abar.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 4))
        abar.grid_columnconfigure(3, weight=1)

        ttk.Button(abar, text="🔍  MATCH & PREVIEW", style="Accent.TButton",
                   command=self._do_match).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(abar, text="💾  SAVE", style="Secondary.TButton",
                   command=self._do_save).grid(row=0, column=1, padx=(0, 16))

        self.progress = ttk.Progressbar(abar, mode="determinate", length=140)
        self.progress.grid(row=0, column=2, padx=(0, 8))

        self.stats_label = tk.Label(abar, text="", font=FONT_UI, fg=TEXT_MUTED,
                                    bg=BG_MAIN, anchor="w")
        self.stats_label.grid(row=0, column=3, sticky="ew")

        # ── card: preview ──
        pcard = ttk.LabelFrame(main, text="👁  Preview (50 บรรทัดแรก)", style="Card.TLabelframe", padding=10)
        pcard.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 8))
        pcard.grid_rowconfigure(0, weight=1)
        pcard.grid_columnconfigure(0, weight=1)

        prev_container = tk.Frame(pcard, bg=PREVIEW_BG, highlightthickness=1,
                                  highlightbackground=BORDER)
        prev_container.grid(row=0, column=0, sticky="nsew")
        prev_container.grid_rowconfigure(0, weight=1)
        prev_container.grid_columnconfigure(0, weight=1)

        self.preview_text = tk.Text(prev_container, font=FONT_MONO,
                                    bg=PREVIEW_BG, fg=PREVIEW_FG,
                                    insertbackground=PREVIEW_FG,
                                    selectbackground="#3a3d5e", selectforeground=PREVIEW_FG,
                                    wrap="char", state="disabled",
                                    borderwidth=0, relief="flat",
                                    padx=10, pady=8)
        scroll_y = ttk.Scrollbar(prev_container, orient="vertical",
                                 command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scroll_y.set)
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

        # ── status bar ──
        sbar = tk.Frame(main, bg=STATUS_BG, height=26)
        sbar.grid(row=6, column=0, sticky="ew")
        sbar.grid_propagate(False)
        self.status_label = tk.Label(sbar, text="✅  พร้อมใช้งาน", font=("Segoe UI", 9),
                                     fg=TEXT_MUTED, bg=STATUS_BG, anchor="w")
        self.status_label.pack(side="left", padx=12, pady=2)

    # ── config panel switcher ─────────────────────────

    def _update_config_panel(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()

        fmt = self.format_var.get()
        p = {"padx": 4, "pady": 2}

        if fmt == "txt":
            ttk.Label(self.dynamic_frame, text="Delimiter:").pack(side="left", **p)
            ttk.Combobox(self.dynamic_frame, textvariable=self.delimiter_var,
                         values=["|", "=", ":", "\t", ",", " -> ", "custom..."],
                         width=10).pack(side="left", **p)
            tk.Label(self.dynamic_frame, text="แยก key|value ด้วยตัวคั่นนี้",
                     font=("Segoe UI", 9), fg=TEXT_HINT, bg=BG_CARD).pack(side="left", **p)

        elif fmt == "csv":
            ttk.Label(self.dynamic_frame, text="Delimiter:").pack(side="left", **p)
            ttk.Combobox(self.dynamic_frame, textvariable=self.delimiter_var,
                         values=[",", ";", "\t", "|"], width=6).pack(side="left", **p)
            ttk.Separator(self.dynamic_frame, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Label(self.dynamic_frame, text="Key Col:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.csv_key_col, width=4).pack(side="left", **p)
            ttk.Label(self.dynamic_frame, text="Value Col:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.csv_val_col, width=4).pack(side="left", **p)
            ttk.Separator(self.dynamic_frame, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Checkbutton(self.dynamic_frame, text="มี Header", variable=self.csv_has_header).pack(side="left", **p)

        elif fmt == "json":
            ttk.Label(self.dynamic_frame, text="โครงสร้าง:").pack(side="left", **p)
            ttk.Combobox(self.dynamic_frame, textvariable=self.json_structure,
                         values=["array", "object"], state="readonly", width=8).pack(side="left", **p)
            ttk.Separator(self.dynamic_frame, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Label(self.dynamic_frame, text="Key field:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.json_key_field, width=10).pack(side="left", **p)
            ttk.Label(self.dynamic_frame, text="Value field:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.json_val_field, width=10).pack(side="left", **p)
            tk.Label(self.dynamic_frame, text="(object = keys มาจาก property names)",
                     font=("Segoe UI", 9), fg=TEXT_HINT, bg=BG_CARD).pack(side="left", **p)

        elif fmt == "xml":
            ttk.Label(self.dynamic_frame, text="Item tag:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.xml_item_tag, width=10).pack(side="left", **p)
            ttk.Label(self.dynamic_frame, text="Key attr:").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.xml_key_attr, width=10).pack(side="left", **p)
            ttk.Label(self.dynamic_frame, text="Value attr (#text=เนื้อหา):").pack(side="left", **p)
            ttk.Entry(self.dynamic_frame, textvariable=self.xml_val_attr, width=10).pack(side="left", **p)

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
            self.status_label.config(text=f"📄 Base: {os.path.basename(path)}")

    def _browse_target(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ Target",
            filetypes=[("All supported", "*.txt;*.csv;*.json;*.xml"),
                       ("Text files", "*.txt"), ("CSV files", "*.csv"),
                       ("JSON files", "*.json"), ("XML files", "*.xml"),
                       ("All files", "*.*")])
        if path:
            self.target_path.set(path)
            self.status_label.config(text=f"📄 Target: {os.path.basename(path)}")

    def _auto_detect(self, path):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ("txt", "csv", "json", "xml"):
            self.format_var.set(ext)
            self._update_config_panel()

    # ── auto output path ──────────────────────────────

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
            return parse_txt(path, self.delimiter_var.get(), enc)
        elif fmt == "csv":
            return parse_csv_file(path,
                                  key_col=int(self.csv_key_col.get()),
                                  val_col=int(self.csv_val_col.get()),
                                  delimiter=self.delimiter_var.get(),
                                  has_header=self.csv_has_header.get(),
                                  encoding=enc)
        elif fmt == "json":
            return parse_json_file(path,
                                   key_field=self.json_key_field.get(),
                                   val_field=self.json_val_field.get(),
                                   structure=self.json_structure.get(),
                                   encoding=enc)
        elif fmt == "xml":
            return parse_xml_file(path,
                                  item_tag=self.xml_item_tag.get(),
                                  key_attr=self.xml_key_attr.get(),
                                  val_attr=self.xml_val_attr.get(),
                                  encoding=enc)
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
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบ Base: {base_path}")
            return
        if not os.path.exists(target_path):
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบ Target: {target_path}")
            return

        self.status_label.config(text="⏳ กำลังอ่านไฟล์...")
        self.progress["mode"] = "indeterminate"
        self.progress.start(8)
        self.root.update_idletasks()

        try:
            base_dict = self._parse_file(base_path)
            target_dict = self._parse_file(target_path)

            manual = self.manual_keys.get().strip()
            manual_added = 0
            if manual:
                for k in re.split(r"[,;\s]+", manual):
                    k = k.strip()
                    if k and k not in base_dict:
                        base_dict[k] = ""
                        manual_added += 1

            merged, n_match, n_unmatch, n_total = match_keys(base_dict, target_dict)
            self.merged_data = merged

            pct = (n_match / n_total * 100) if n_total > 0 else 0

            self.progress.stop()
            self.progress["mode"] = "determinate"
            self.progress["value"] = pct

            if pct >= 95:
                color = SUCCESS
            elif pct >= 70:
                color = WARNING
            else:
                color = DANGER

            parts = [f"จับคู่ {n_match}/{n_total} ({pct:.1f}%)"]
            if n_unmatch > 0:
                parts.append(f"ไม่พบ {n_unmatch}")
            if manual_added > 0:
                parts.append(f"เพิ่มเอง {manual_added}")

            self.stats_label.config(text="  │  ".join(parts), fg=color)

            style = ttk.Style()
            style.configure("TProgressbar", background=color,
                            lightcolor=color, darkcolor=color)

            self.status_label.config(text=f"✅  จับคู่แล้ว {n_match:,} keys — พร้อมบันทึก")
            self._show_preview(merged)

        except Exception as e:
            self.progress.stop()
            self.progress["mode"] = "determinate"
            self.progress["value"] = 0
            self.stats_label.config(text="เกิดข้อผิดพลาด", fg=DANGER)
            messagebox.showerror("เกิดข้อผิดพลาด", f"{type(e).__name__}:\n{e}")
            self.status_label.config(text=f"❌ Error: {e}")

    def _show_preview(self, data):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")

        delimiter = self.delimiter_var.get()
        fmt = self.format_var.get()
        lines = list(data.items())

        for i, (key, val) in enumerate(lines):
            if i >= 50:
                self.preview_text.insert("end",
                    f"\n\n⋯  อีก {len(lines) - 50:,} บรรทัด  (กด 💾 Save เพื่อบันทึกทั้งหมด)", "muted")
                break
            if fmt == "txt":
                self.preview_text.insert("end", key, "key")
                self.preview_text.insert("end", delimiter, "delim")
                self.preview_text.insert("end", val + "\n", "val")
            else:
                self.preview_text.insert("end", key, "key")
                self.preview_text.insert("end", "  →  ", "delim")
                self.preview_text.insert("end", val + "\n", "val")

        self.preview_text.configure(state="disabled")

        self.preview_text.tag_configure("key", foreground="#89b4fa")
        self.preview_text.tag_configure("delim", foreground="#6c7086")
        self.preview_text.tag_configure("val", foreground=PREVIEW_FG)
        self.preview_text.tag_configure("muted", foreground="#585b70",
                                        font=("Cascadia Code", 9, "italic"))

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
                                structure=self.json_structure.get(),
                                key_field=self.json_key_field.get(),
                                val_field=self.json_val_field.get(),
                                encoding=enc)
            elif fmt == "xml":
                write_xml_file(self.merged_data, path,
                               item_tag=self.xml_item_tag.get(),
                               key_attr=self.xml_key_attr.get(),
                               val_attr=self.xml_val_attr.get(),
                               encoding=enc)

            self.status_label.config(text=f"💾  บันทึกแล้ว: {path}")
            messagebox.showinfo("บันทึกสำเร็จ",
                                f"บันทึกแล้ว:\n{path}\n\n"
                                f"📊 {len(self.merged_data):,} keys")
        except Exception as e:
            messagebox.showerror("บันทึกไม่สำเร็จ", f"{type(e).__name__}:\n{e}")
            self.status_label.config(text=f"❌ บันทึกไม่สำเร็จ: {e}")


# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyMatcherApp(root)
    root.mainloop()
