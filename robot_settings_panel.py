#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robot settings tab: robots + groups CRUD / Copy (soft delete / restore)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from robot_setting_store import (
    copy_entry,
    list_group_ids,
    list_robot_ids,
    load_data,
    next_id,
    save_data,
    soft_delete,
    soft_restore,
    upsert_group,
    upsert_robot,
)

LISTBOX_ROWS = 5
FORM_COLUMNS = 2  # field pairs per row (label+entry units)

ROBOT_FIELD_KEYS = (
    "ip",
    "maker",
    "product",
    "arm",
    "cab",
    "version_scb",
    "version_controller",
    "version_servo",
    "payload",
)

BUTTON_I18N = {
    "robot_btn_new": "btn_new",
    "robot_btn_save": "btn_save",
    "robot_btn_copy": "btn_copy",
    "robot_btn_cancel": "btn_cancel",
    "robot_btn_disable": "btn_disable",
    "robot_btn_enable": "btn_enable",
    "group_btn_new": "btn_new",
    "group_btn_save": "btn_save",
    "group_btn_copy": "btn_copy",
    "group_btn_cancel": "btn_cancel",
    "group_btn_disable": "btn_disable",
    "group_btn_enable": "btn_enable",
}


class RobotSettingsPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, t: Callable[[str], str], **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.t = t
        self.data = load_data()
        self.font_size = 12
        self._robot_form_vars: dict[str, tk.StringVar] = {}
        self._group_form_vars: dict[str, tk.StringVar] = {}
        self._i18n_widgets: dict[str, object] = {}
        self._robot_field_labels: dict[str, ttk.Label] = {}
        self._group_field_labels: dict[str, ttk.Label] = {}
        self._robot_keys: list[str] = []
        self._group_keys: list[str] = []
        self._current_robot_key: str | None = None
        self._current_group_key: str | None = None
        self._robot_before_new: str | None = None
        self._group_before_new: str | None = None
        self._robot_is_new = False
        self._group_is_new = False
        self._form_entries: list[tk.Entry] = []
        self.robot_visible_var = tk.BooleanVar(value=True)
        self.group_visible_var = tk.BooleanVar(value=True)
        self._build()
        self.refresh_lists()
        self._select_first_records()

    def apply_language(self) -> None:
        for key, widget in self._i18n_widgets.items():
            text_key = BUTTON_I18N.get(key, key)
            if key in ("field_id", "group_field_id"):
                text_key = "field_id"
            if key in ("field_visible", "group_field_visible"):
                text_key = "field_visible"
            if key in ("robot_visible_value", "group_visible_value"):
                continue
            text = self.t(text_key)
            if isinstance(widget, ttk.LabelFrame):
                widget.configure(text=text)
            elif isinstance(widget, (ttk.Label, ttk.Button)):
                widget.configure(text=text)
        for field, label in self._robot_field_labels.items():
            label.configure(text=self.t(f"field_{field}"))
        for field, label in self._group_field_labels.items():
            label.configure(text=self.t(f"field_{field}"))
        self._refresh_visible_labels()
        self.refresh_lists(keep_selection=True)

    def apply_font_size(self, size: int) -> None:
        self.font_size = size
        font = ("Segoe UI", size)
        for lb in (self.robot_list, self.group_list):
            lb.configure(font=font, height=LISTBOX_ROWS)
        for entry in self._form_entries:
            entry.configure(font=font)

    def _refresh_visible_labels(self) -> None:
        robot_val = self._i18n_widgets.get("robot_visible_value")
        if isinstance(robot_val, ttk.Label):
            robot_val.configure(text=self._visible_text(self.robot_visible_var.get()))
        group_val = self._i18n_widgets.get("group_visible_value")
        if isinstance(group_val, ttk.Label):
            group_val.configure(text=self._visible_text(self.group_visible_var.get()))
        self._sync_visible_action_buttons()

    def _sync_visible_action_buttons(self) -> None:
        """Enabled -> only Disable; Disabled -> only Enable."""
        pairs = (
            (self.robot_visible_var.get(), "robot_btn_enable", "robot_btn_disable"),
            (self.group_visible_var.get(), "group_btn_enable", "group_btn_disable"),
        )
        for enabled, enable_key, disable_key in pairs:
            btn_enable = self._i18n_widgets.get(enable_key)
            btn_disable = self._i18n_widgets.get(disable_key)
            if not isinstance(btn_enable, ttk.Button) or not isinstance(
                btn_disable, ttk.Button
            ):
                continue
            if enabled:
                btn_enable.pack_forget()
                if not btn_disable.winfo_ismapped():
                    btn_disable.pack(side=tk.LEFT)
            else:
                btn_disable.pack_forget()
                if not btn_enable.winfo_ismapped():
                    btn_enable.pack(side=tk.LEFT)

    def _visible_text(self, visible: bool) -> str:
        return self.t("visible_true") if visible else self.t("visible_false")

    def _build(self) -> None:
        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(body, padding=4)
        right = ttk.Frame(body, padding=4)
        body.add(left, weight=1)
        body.add(right, weight=1)
        self._build_robot_section(left)
        self._build_group_section(right)

    def _build_list_and_top_buttons(
        self,
        frame: ttk.Frame,
        *,
        list_attr: str,
        on_select,
        button_specs: list[tuple[str, Callable]],
    ) -> None:
        list_row = ttk.Frame(frame)
        list_row.pack(fill=tk.X)
        lb = tk.Listbox(list_row, height=LISTBOX_ROWS, exportselection=False)
        lb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lb.bind("<<ListboxSelect>>", on_select)
        sb = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=sb.set)
        setattr(self, list_attr, lb)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, pady=(8, 8))
        for wkey, cmd in button_specs:
            b = ttk.Button(btns, command=cmd)
            b.pack(side=tk.LEFT, padx=(0, 6))
            self._i18n_widgets[wkey] = b

    def _place_fields_grid(
        self,
        form: ttk.Frame,
        fields: tuple[str, ...],
        vars_dict: dict[str, tk.StringVar],
        labels_dict: dict[str, ttk.Label],
        start_row: int = 0,
    ) -> int:
        """Place fields in multi-column grid. Returns next free row."""
        cols = FORM_COLUMNS
        for idx, field in enumerate(fields):
            row = start_row + idx // cols
            col_unit = idx % cols
            base_col = col_unit * 2
            lab = ttk.Label(form)
            lab.grid(row=row, column=base_col, sticky=tk.W, pady=4, padx=(0, 6))
            labels_dict[field] = lab
            var = tk.StringVar()
            vars_dict[field] = var
            # tk.Entry: avoid ttk quirks that may block '.' in IP-like text.
            entry = tk.Entry(form, textvariable=var, width=18)
            entry.grid(
                row=row, column=base_col + 1, sticky=tk.EW, pady=4, padx=(0, 12)
            )
            self._form_entries.append(entry)
        for c in range(cols * 2):
            form.columnconfigure(c, weight=1 if c % 2 == 1 else 0)
        used_rows = (len(fields) + cols - 1) // cols
        return start_row + used_rows

    def _build_visible_row(
        self,
        form: ttk.Frame,
        row: int,
        *,
        label_key: str,
        value_key: str,
        enable_key: str,
        disable_key: str,
        enable_cmd,
        disable_cmd,
    ) -> None:
        lab = ttk.Label(form)
        lab.grid(row=row, column=0, sticky=tk.W, pady=8, padx=(0, 6))
        self._i18n_widgets[label_key] = lab

        val = ttk.Label(form)
        val.grid(row=row, column=1, sticky=tk.W, pady=8, padx=(0, 12))
        self._i18n_widgets[value_key] = val

        actions = ttk.Frame(form)
        actions.grid(row=row, column=2, columnspan=2, sticky=tk.W, pady=8)
        # Both created; visibility toggled so only one shows at a time.
        btn_enable = ttk.Button(actions, command=enable_cmd)
        self._i18n_widgets[enable_key] = btn_enable
        btn_disable = ttk.Button(actions, command=disable_cmd)
        self._i18n_widgets[disable_key] = btn_disable
        btn_disable.pack(side=tk.LEFT)

    def _build_robot_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        self._i18n_widgets["section_robots"] = frame

        self._build_list_and_top_buttons(
            frame,
            list_attr="robot_list",
            on_select=self._on_robot_select,
            button_specs=[
                ("robot_btn_new", self._robot_new),
                ("robot_btn_save", self._robot_save),
                ("robot_btn_copy", self._robot_copy),
                ("robot_btn_cancel", self._robot_cancel),
            ],
        )

        form = ttk.Frame(frame)
        form.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        id_label = ttk.Label(form)
        id_label.grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 6))
        self._i18n_widgets["field_id"] = id_label
        self.robot_id_var = tk.StringVar()
        id_entry = tk.Entry(form, textvariable=self.robot_id_var, width=18)
        id_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(0, 12))
        self._form_entries.append(id_entry)

        next_row = self._place_fields_grid(
            form,
            ROBOT_FIELD_KEYS,
            self._robot_form_vars,
            self._robot_field_labels,
            start_row=1,
        )
        self._build_visible_row(
            form,
            next_row,
            label_key="field_visible",
            value_key="robot_visible_value",
            enable_key="robot_btn_enable",
            disable_key="robot_btn_disable",
            enable_cmd=self._robot_restore,
            disable_cmd=self._robot_delete,
        )
        self._refresh_visible_labels()

    def _build_group_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        self._i18n_widgets["section_groups"] = frame

        self._build_list_and_top_buttons(
            frame,
            list_attr="group_list",
            on_select=self._on_group_select,
            button_specs=[
                ("group_btn_new", self._group_new),
                ("group_btn_save", self._group_save),
                ("group_btn_copy", self._group_copy),
                ("group_btn_cancel", self._group_cancel),
            ],
        )

        form = ttk.Frame(frame)
        form.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        id_label = ttk.Label(form)
        id_label.grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 6))
        self._i18n_widgets["group_field_id"] = id_label
        self.group_id_var = tk.StringVar()
        id_entry = tk.Entry(form, textvariable=self.group_id_var, width=18)
        id_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(0, 12))
        self._form_entries.append(id_entry)

        # Group has few fields; use one field per row (robots list is long).
        for i, field in enumerate(("maker", "robots"), start=1):
            lab = ttk.Label(form)
            lab.grid(row=i, column=0, sticky=tk.NW, pady=4, padx=(0, 6))
            self._group_field_labels[field] = lab
            var = tk.StringVar()
            self._group_form_vars[field] = var
            width = 48 if field == "robots" else 28
            entry = tk.Entry(form, textvariable=var, width=width)
            entry.grid(
                row=i, column=1, columnspan=3, sticky=tk.EW, pady=4, padx=(0, 12)
            )
            self._form_entries.append(entry)
        form.columnconfigure(1, weight=1)

        hint = ttk.Label(form, wraplength=420)
        hint.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(2, 4))
        self._i18n_widgets["hint_group_robots"] = hint

        self._build_visible_row(
            form,
            4,
            label_key="group_field_visible",
            value_key="group_visible_value",
            enable_key="group_btn_enable",
            disable_key="group_btn_disable",
            enable_cmd=self._group_restore,
            disable_cmd=self._group_delete,
        )
        self._refresh_visible_labels()

    def _format_list_item(self, key: str) -> str:
        visible = bool((self.data.get(key) or {}).get("visible", True))
        return f"{key}  [{self._visible_text(visible)}]"

    def _select_first_records(self) -> None:
        """Select first robot and first group so both forms show data immediately."""
        if self._robot_keys:
            key = self._robot_keys[0]
            self._select_key(self.robot_list, self._robot_keys, key)
            self._load_robot_form(key)
        if self._group_keys:
            key = self._group_keys[0]
            self._select_key(self.group_list, self._group_keys, key)
            self._load_group_form(key)

    def refresh_lists(self, keep_selection: bool = False) -> None:
        robot_sel = self._current_robot_key if keep_selection else None
        group_sel = self._current_group_key if keep_selection else None
        if not keep_selection:
            rsel = self.robot_list.curselection()
            if rsel and rsel[0] < len(self._robot_keys):
                robot_sel = self._robot_keys[rsel[0]]
            gsel = self.group_list.curselection()
            if gsel and gsel[0] < len(self._group_keys):
                group_sel = self._group_keys[gsel[0]]

        self._robot_keys = list_robot_ids(self.data, include_hidden=True)
        self.robot_list.delete(0, tk.END)
        for rid in self._robot_keys:
            self.robot_list.insert(tk.END, self._format_list_item(rid))

        self._group_keys = list_group_ids(self.data, include_hidden=True)
        self.group_list.delete(0, tk.END)
        for gid in self._group_keys:
            self.group_list.insert(tk.END, self._format_list_item(gid))

        if robot_sel and robot_sel in self._robot_keys:
            self._select_key(self.robot_list, self._robot_keys, robot_sel)
            self._load_robot_form(robot_sel)
        elif self._robot_keys and self._current_robot_key is None:
            self._select_key(self.robot_list, self._robot_keys, self._robot_keys[0])
            self._load_robot_form(self._robot_keys[0])

        if group_sel and group_sel in self._group_keys:
            self._select_key(self.group_list, self._group_keys, group_sel)
            self._load_group_form(group_sel)
        elif self._group_keys and self._current_group_key is None:
            self._select_key(self.group_list, self._group_keys, self._group_keys[0])
            self._load_group_form(self._group_keys[0])

    def _on_robot_select(self, _event=None) -> None:
        sel = self.robot_list.curselection()
        if not sel or sel[0] >= len(self._robot_keys):
            return
        self._load_robot_form(self._robot_keys[sel[0]])

    def _on_group_select(self, _event=None) -> None:
        sel = self.group_list.curselection()
        if not sel or sel[0] >= len(self._group_keys):
            return
        self._load_group_form(self._group_keys[sel[0]])

    def _load_robot_form(self, key: str) -> None:
        item = self.data.get(key) or {}
        self._current_robot_key = key
        self._robot_is_new = False
        self.robot_id_var.set(key)
        for field in ROBOT_FIELD_KEYS:
            val = item.get(field, "")
            self._robot_form_vars[field].set("" if val is None else str(val))
        self.robot_visible_var.set(bool(item.get("visible", True)))
        self._refresh_visible_labels()

    def _load_group_form(self, key: str) -> None:
        item = self.data.get(key) or {}
        self._current_group_key = key
        self._group_is_new = False
        self.group_id_var.set(key)
        self._group_form_vars["maker"].set(str(item.get("maker", "")))
        robots = item.get("robots") or []
        self._group_form_vars["robots"].set(", ".join(str(x) for x in robots))
        self.group_visible_var.set(bool(item.get("visible", True)))
        self._refresh_visible_labels()

    def _clear_robot_form(self, new_id: str = "") -> None:
        self._current_robot_key = None
        self.robot_id_var.set(new_id)
        for var in self._robot_form_vars.values():
            var.set("")
        self.robot_visible_var.set(True)
        self._refresh_visible_labels()

    def _clear_group_form(self, new_id: str = "") -> None:
        self._current_group_key = None
        self.group_id_var.set(new_id)
        self._group_form_vars["maker"].set("robot_team")
        self._group_form_vars["robots"].set("")
        self.group_visible_var.set(True)
        self._refresh_visible_labels()

    def _robot_new(self) -> None:
        self._robot_before_new = self._current_robot_key or (
            self._robot_keys[0] if self._robot_keys else None
        )
        self._robot_is_new = True
        self.robot_list.selection_clear(0, tk.END)
        self._clear_robot_form(next_id(self.data, "robot"))

    def _group_new(self) -> None:
        self._group_before_new = self._current_group_key or (
            self._group_keys[0] if self._group_keys else None
        )
        self._group_is_new = True
        self.group_list.selection_clear(0, tk.END)
        self._clear_group_form(next_id(self.data, "group"))

    def _robot_cancel(self) -> None:
        target = self._robot_before_new if self._robot_is_new else self._current_robot_key
        self._robot_is_new = False
        self._robot_before_new = None
        if target and target in self.data:
            self._select_key(self.robot_list, self._robot_keys, target)
            self._load_robot_form(target)
        elif self._robot_keys:
            self._select_key(self.robot_list, self._robot_keys, self._robot_keys[0])
            self._load_robot_form(self._robot_keys[0])
        else:
            self._clear_robot_form()

    def _group_cancel(self) -> None:
        target = self._group_before_new if self._group_is_new else self._current_group_key
        self._group_is_new = False
        self._group_before_new = None
        if target and target in self.data:
            self._select_key(self.group_list, self._group_keys, target)
            self._load_group_form(target)
        elif self._group_keys:
            self._select_key(self.group_list, self._group_keys, self._group_keys[0])
            self._load_group_form(self._group_keys[0])
        else:
            self._clear_group_form()

    def _robot_collect(self) -> tuple[str, dict]:
        key = self.robot_id_var.get().strip()
        if not key:
            raise ValueError(self.t("msg_id_required"))
        fields: dict = {"visible": bool(self.robot_visible_var.get())}
        for field, var in self._robot_form_vars.items():
            text = var.get().strip()
            if field == "payload" and text != "":
                try:
                    fields[field] = float(text) if "." in text else int(text)
                except ValueError:
                    fields[field] = text
            elif text != "":
                fields[field] = text
        return key, fields

    def _group_collect(self) -> tuple[str, dict]:
        key = self.group_id_var.get().strip()
        if not key:
            raise ValueError(self.t("msg_id_required"))
        robots = [
            x.strip()
            for x in self._group_form_vars["robots"].get().split(",")
            if x.strip()
        ]
        return key, {
            "maker": self._group_form_vars["maker"].get().strip() or "robot_team",
            "robots": robots,
            "visible": bool(self.group_visible_var.get()),
        }

    def _robot_save(self) -> None:
        try:
            key, fields = self._robot_collect()
            old = self._current_robot_key
            if old is None and key in self.data:
                raise ValueError(self.t("msg_id_exists"))
            if old and old != key:
                if key in self.data:
                    raise ValueError(self.t("msg_id_exists"))
                del self.data[old]
            upsert_robot(self.data, key, fields)
            save_data(self.data)
            self.data = load_data()
            self._robot_is_new = False
            self._robot_before_new = None
            self.refresh_lists()
            self._select_key(self.robot_list, self._robot_keys, key)
            self._load_robot_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_saved"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _group_save(self) -> None:
        try:
            key, fields = self._group_collect()
            old = self._current_group_key
            if old is None and key in self.data:
                raise ValueError(self.t("msg_id_exists"))
            if old and old != key:
                if key in self.data:
                    raise ValueError(self.t("msg_id_exists"))
                del self.data[old]
            upsert_group(self.data, key, fields)
            save_data(self.data)
            self.data = load_data()
            self._group_is_new = False
            self._group_before_new = None
            self.refresh_lists()
            self._select_key(self.group_list, self._group_keys, key)
            self._load_group_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_saved"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _robot_copy(self) -> None:
        key = self._selected_key(self.robot_list, self._robot_keys, self._current_robot_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        try:
            new_key = copy_entry(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.robot_list, self._robot_keys, new_key)
            self._load_robot_form(new_key)
            messagebox.showinfo(
                self.t("msg_title_info"), self.t("msg_copied").format(id=new_key)
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _group_copy(self) -> None:
        key = self._selected_key(self.group_list, self._group_keys, self._current_group_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        try:
            new_key = copy_entry(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.group_list, self._group_keys, new_key)
            self._load_group_form(new_key)
            messagebox.showinfo(
                self.t("msg_title_info"), self.t("msg_copied").format(id=new_key)
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _robot_delete(self) -> None:
        key = self._selected_key(self.robot_list, self._robot_keys, self._current_robot_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        if not messagebox.askyesno(
            self.t("msg_title_confirm"),
            self.t("msg_confirm_soft_delete").format(id=key),
        ):
            return
        try:
            soft_delete(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.robot_list, self._robot_keys, key)
            self._load_robot_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_soft_deleted"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _group_delete(self) -> None:
        key = self._selected_key(self.group_list, self._group_keys, self._current_group_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        if not messagebox.askyesno(
            self.t("msg_title_confirm"),
            self.t("msg_confirm_soft_delete").format(id=key),
        ):
            return
        try:
            soft_delete(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.group_list, self._group_keys, key)
            self._load_group_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_soft_deleted"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _robot_restore(self) -> None:
        key = self._selected_key(self.robot_list, self._robot_keys, self._current_robot_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        try:
            soft_restore(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.robot_list, self._robot_keys, key)
            self._load_robot_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_restored"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    def _group_restore(self) -> None:
        key = self._selected_key(self.group_list, self._group_keys, self._current_group_key)
        if not key:
            messagebox.showwarning(self.t("msg_title_warn"), self.t("msg_select_first"))
            return
        try:
            soft_restore(self.data, key)
            save_data(self.data)
            self.data = load_data()
            self.refresh_lists()
            self._select_key(self.group_list, self._group_keys, key)
            self._load_group_form(key)
            messagebox.showinfo(self.t("msg_title_info"), self.t("msg_restored"))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(self.t("msg_title_error"), str(exc))

    @staticmethod
    def _selected_key(
        listbox: tk.Listbox, keys: list[str], current: str | None
    ) -> str | None:
        sel = listbox.curselection()
        if sel and sel[0] < len(keys):
            return keys[sel[0]]
        return current

    @staticmethod
    def _select_key(listbox: tk.Listbox, keys: list[str], key: str) -> None:
        if key in keys:
            idx = keys.index(key)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.see(idx)
