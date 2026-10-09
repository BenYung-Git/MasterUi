#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load / save / migrate master vision_setting.yaml (does not touch source file)."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
SOURCE_VISION_SETTING = (
    BASE_DIR.parent / "robot_data" / "user0" / "vision_setting.yaml"
)
MASTER_VISION_SETTING = BASE_DIR / "vision_setting.yaml"

HEADER_COMMENT = "# Vision settings (master copy; source is not modified)\n"

VISION_ID_RE = re.compile(r"^vision(\d+)$")


def is_vision_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(VISION_ID_RE.match(key))


def _with_visible_last(data: dict[str, Any], visible: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k == "visible":
            continue
        out[k] = v
    out["visible"] = bool(visible)
    return out


def _normalize_loaded(raw: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            result[key] = value
            continue
        visible = value.get("visible", True)
        if isinstance(visible, str):
            visible = visible.strip().lower() not in {"false", "0", "no"}
        item = {k: v for k, v in value.items() if k != "visible"}
        result[key] = _with_visible_last(item, bool(visible))
    return result


def migrate_from_source(force: bool = False) -> Path:
    """Copy all entries from source into master file; add visible at end."""
    if MASTER_VISION_SETTING.exists() and not force:
        return MASTER_VISION_SETTING
    if not SOURCE_VISION_SETTING.exists():
        raise FileNotFoundError(f"Source not found: {SOURCE_VISION_SETTING}")

    with SOURCE_VISION_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Source vision_setting.yaml root must be a mapping")

    migrated: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            migrated[key] = _with_visible_last(value, True)
        else:
            migrated[key] = value

    save_data(migrated)
    return MASTER_VISION_SETTING


def ensure_master_file() -> Path:
    return migrate_from_source(force=False)


def load_data() -> dict[str, Any]:
    ensure_master_file()
    with MASTER_VISION_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Master vision_setting.yaml root must be a mapping")
    return _normalize_loaded(raw)


def _id_sort_key(key: str) -> tuple[str, int]:
    m = re.match(r"^([a-zA-Z_]+)(\d+)$", key)
    if not m:
        return (key, 0)
    return (m.group(1), int(m.group(2)))


def save_data(data: dict[str, Any]) -> None:
    normalized = _normalize_loaded(data)
    vision_keys = sorted(
        [k for k, v in normalized.items() if is_vision_entry(k, v)],
        key=_id_sort_key,
    )
    other_keys = [k for k in normalized.keys() if k not in vision_keys]
    ordered = {k: normalized[k] for k in vision_keys + other_keys}

    text = yaml.dump(
        ordered,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    MASTER_VISION_SETTING.write_text(HEADER_COMMENT + text, encoding="utf-8")


def list_vision_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_vision_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def next_id(data: dict[str, Any], prefix: str = "vision") -> str:
    nums = []
    for key in data:
        m = re.match(rf"^{re.escape(prefix)}(\d+)$", key)
        if m:
            nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 1
    return f"{prefix}{n}"


def soft_delete(data: dict[str, Any], key: str) -> None:
    if key not in data or not isinstance(data[key], dict):
        raise KeyError(key)
    item = {k: v for k, v in data[key].items() if k != "visible"}
    data[key] = _with_visible_last(item, False)


def soft_restore(data: dict[str, Any], key: str) -> None:
    if key not in data or not isinstance(data[key], dict):
        raise KeyError(key)
    item = {k: v for k, v in data[key].items() if k != "visible"}
    data[key] = _with_visible_last(item, True)


def copy_entry(data: dict[str, Any], key: str) -> str:
    if key not in data or not isinstance(data[key], dict):
        raise KeyError(key)
    new_key = next_id(data, "vision")
    cloned = copy.deepcopy(data[key])
    cloned = _with_visible_last(cloned, True)
    data[new_key] = cloned
    return new_key


def mode_to_text(mode: Any) -> str:
    if not isinstance(mode, dict):
        return ""
    lines = []
    for k, v in mode.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def parse_mode_text(text: str) -> dict[str, Any]:
    """Parse textarea lines 'KEY: value' into mode mapping."""
    mode: dict[str, Any] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid mode line: {raw_line}")
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not key:
            raise ValueError(f"Invalid mode line: {raw_line}")
        if val == "":
            mode[key] = ""
            continue
        try:
            if "." in val:
                mode[key] = float(val)
            else:
                mode[key] = int(val)
        except ValueError:
            mode[key] = val
    return mode


def upsert_vision(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    visible = fields.get("visible", True)
    item: dict[str, Any] = {}

    for name in ("product_id", "product_typename", "ip"):
        val = fields.get(name, "")
        if isinstance(val, str) and val.strip() != "":
            item[name] = val.strip()
        elif val not in ("", None) and not isinstance(val, str):
            item[name] = val

    mode_raw = fields.get("mode", "")
    if isinstance(mode_raw, dict):
        if mode_raw:
            item["mode"] = mode_raw
    else:
        mode = parse_mode_text(str(mode_raw or ""))
        if mode:
            item["mode"] = mode

    data[key] = _with_visible_last(item, bool(visible))


def vision_to_public(key: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": key,
        "visible": bool(item.get("visible", True)),
        "product_id": item.get("product_id", "") or "",
        "product_typename": item.get("product_typename", "") or "",
        "ip": item.get("ip", "") or "",
        "mode": mode_to_text(item.get("mode")),
    }
