#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZiYan master UI: source data settings center."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from robot_settings_panel import RobotSettingsPanel

BASE_DIR = Path(__file__).resolve().parent
I18N_PATH = BASE_DIR / "i18n.json"
DEFAULT_LANG = "zh-TW"
DEFAULT_FONT_SIZE = 12
FONT_SIZES = (10, 11, 12, 14, 16, 18, 20)
LANG_ORDER = ("zh-TW", "en", "zh-CN")
LANG_LABEL_KEYS = {
    "zh-TW": "lang_zh_tw",
    "en": "lang_en",
    "zh-CN": "lang_zh_cn",
}


class MasterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.i18n = self._load_i18n()
        self.lang = DEFAULT_LANG if DEFAULT_LANG in self.i18n else next(iter(self.i18n))
        self.font_size = DEFAULT_FONT_SIZE
        self.style = ttk.Style(self)
        self._widgets: dict[str, object] = {}
        self._lang_label_to_code: dict[str, str] = {}

        self.geometry("1100x720")
        self.minsize(800, 520)

        self._build_ui()
        self.apply_font_size()
        self.apply_language()

    def _load_i18n(self) -> dict:
        with I18N_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data:
            raise RuntimeError(f"Invalid i18n file: {I18N_PATH}")
        return data

    def t(self, key: str) -> str:
        return self.i18n.get(self.lang, {}).get(key, key)

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(12, 12, 12, 4))
        header.pack(fill=tk.X)
        form_header = ttk.Label(header, style="Header.TLabel")
        form_header.pack(side=tk.LEFT)
        self._widgets["form_header"] = form_header

        version_label = ttk.Label(header, style="Header.TLabel")
        version_label.pack(side=tk.LEFT, padx=(12, 0))
        self._widgets["app_version"] = version_label

        top = ttk.Frame(self, padding=(12, 6, 12, 6))
        top.pack(fill=tk.X)

        lang_label = ttk.Label(top)
        lang_label.pack(side=tk.LEFT)
        self._widgets["lang_label"] = lang_label

        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(
            top,
            textvariable=self.lang_var,
            state="readonly",
            width=12,
        )
        self.lang_combo.pack(side=tk.LEFT, padx=(6, 16))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        fontsize_label = ttk.Label(top)
        fontsize_label.pack(side=tk.LEFT)
        self._widgets["fontsize_label"] = fontsize_label

        self.fontsize_var = tk.StringVar(value=str(self.font_size))
        self.fontsize_combo = ttk.Combobox(
            top,
            textvariable=self.fontsize_var,
            values=[str(n) for n in FONT_SIZES],
            state="readonly",
            width=6,
        )
        self.fontsize_combo.pack(side=tk.LEFT, padx=(6, 0))
        self.fontsize_combo.bind("<<ComboboxSelected>>", self._on_fontsize_change)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.tab_robot = ttk.Frame(self.notebook, padding=8)
        self.tab_tool = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_robot, text="")
        self.notebook.add(self.tab_tool, text="")

        self.robot_panel = RobotSettingsPanel(self.tab_robot, t=self.t)
        self.robot_panel.pack(fill=tk.BOTH, expand=True)

        tool_hint = ttk.Label(self.tab_tool, anchor=tk.CENTER)
        tool_hint.pack(expand=True)
        self._widgets["placeholder_tool"] = tool_hint

    def _refresh_lang_combo(self) -> None:
        labels = []
        self._lang_label_to_code.clear()
        for code in LANG_ORDER:
            if code not in self.i18n:
                continue
            label = self.t(LANG_LABEL_KEYS[code])
            labels.append(label)
            self._lang_label_to_code[label] = code
        self.lang_combo.configure(values=labels)
        current_label = self.t(LANG_LABEL_KEYS.get(self.lang, "lang_zh_tw"))
        self.lang_var.set(current_label)

    def _on_lang_change(self, _event=None) -> None:
        code = self._lang_label_to_code.get(self.lang_var.get())
        if code and code in self.i18n:
            self.lang = code
            self.apply_language()

    def _on_fontsize_change(self, _event=None) -> None:
        try:
            size = int(self.fontsize_var.get())
        except ValueError:
            size = DEFAULT_FONT_SIZE
            self.fontsize_var.set(str(size))
        self.font_size = size
        self.apply_font_size()

    def apply_font_size(self) -> None:
        size = self.font_size
        base = ("Segoe UI", size)
        header = ("Segoe UI", size + 4, "bold")
        self.option_add("*Font", base)
        self.style.configure(".", font=base)
        self.style.configure("TLabel", font=base)
        self.style.configure("TButton", font=base)
        self.style.configure("TRadiobutton", font=base)
        self.style.configure("TCheckbutton", font=base)
        self.style.configure("TCombobox", font=base)
        self.style.configure("TEntry", font=base)
        self.style.configure("TNotebook.Tab", font=base)
        self.style.configure("TLabelframe.Label", font=base)
        self.style.configure("Header.TLabel", font=header)
        # Grow window with font so content is less likely to be clipped.
        width = max(1100, 900 + (size - 12) * 40)
        height = max(720, 600 + (size - 12) * 36)
        self.geometry(f"{width}x{height}")
        if hasattr(self, "robot_panel"):
            self.robot_panel.apply_font_size(size)

    def apply_language(self) -> None:
        self.title(self.t("app_title"))
        self._widgets["form_header"].configure(text=self.t("form_header"))
        self._widgets["app_version"].configure(text=self.t("app_version"))
        self._widgets["lang_label"].configure(text=self.t("lang_label"))
        self._widgets["fontsize_label"].configure(text=self.t("fontsize_label"))
        self._refresh_lang_combo()
        self.notebook.tab(0, text=self.t("tab_robot"))
        self.notebook.tab(1, text=self.t("tab_tool"))
        self._widgets["placeholder_tool"].configure(text=self.t("placeholder_tool"))
        self.robot_panel.apply_language()


def main() -> None:
    app = MasterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
