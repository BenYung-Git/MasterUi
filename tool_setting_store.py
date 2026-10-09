#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load / save / migrate master tool_setting.yaml (does not touch source file)."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
SOURCE_TOOL_SETTING = BASE_DIR.parent / "robot_data" / "user0" / "tool_setting.yaml"
MASTER_TOOL_SETTING = BASE_DIR / "tool_setting.yaml"

HEADER_COMMENT = "# Tool settings (master copy; source is not modified)\n"

TOOL_ID_RE = re.compile(r"^tool(\d+)$")


def is_tool_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(TOOL_ID_RE.match(key))


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
    if MASTER_TOOL_SETTING.exists() and not force:
        return MASTER_TOOL_SETTING
    if not SOURCE_TOOL_SETTING.exists():
        raise FileNotFoundError(f"Source not found: {SOURCE_TOOL_SETTING}")

    with SOURCE_TOOL_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Source tool_setting.yaml root must be a mapping")

    migrated: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            migrated[key] = _with_visible_last(value, True)
        else:
            migrated[key] = value

    save_data(migrated)
    return MASTER_TOOL_SETTING


def ensure_master_file() -> Path:
    return migrate_from_source(force=False)


def load_data() -> dict[str, Any]:
    ensure_master_file()
    with MASTER_TOOL_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Master tool_setting.yaml root must be a mapping")
    return _normalize_loaded(raw)


def _id_sort_key(key: str) -> tuple[str, int]:
    m = re.match(r"^([a-zA-Z_]+)(\d+)$", key)
    if not m:
        return (key, 0)
    return (m.group(1), int(m.group(2)))


def save_data(data: dict[str, Any]) -> None:
    normalized = _normalize_loaded(data)
    tool_keys = sorted(
        [k for k, v in normalized.items() if is_tool_entry(k, v)],
        key=_id_sort_key,
    )
    other_keys = [k for k in normalized if k not in tool_keys]
    # Preserve relative order of non-tool keys (e.g. tool_group1).
    other_ordered = [k for k in normalized.keys() if k in other_keys]
    ordered = {k: normalized[k] for k in tool_keys + other_ordered}

    text = yaml.dump(
        ordered,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    MASTER_TOOL_SETTING.write_text(HEADER_COMMENT + text, encoding="utf-8")


def list_tool_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_tool_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def next_id(data: dict[str, Any], prefix: str = "tool") -> str:
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
    new_key = next_id(data, "tool")
    cloned = copy.deepcopy(data[key])
    cloned = _with_visible_last(cloned, True)
    data[new_key] = cloned
    return new_key


def _parse_number_list(values: list[Any]) -> list[float | int] | None:
    """Return list of numbers if complete; None if all empty; raise if invalid."""
    if not values or all(str(v).strip() == "" for v in values):
        return None
    out: list[float | int] = []
    for v in values:
        text = str(v).strip()
        if text == "":
            raise ValueError("xyz / RPY require complete numeric values")
        try:
            num: float | int = float(text) if "." in text else int(text)
        except ValueError as exc:
            raise ValueError("xyz / RPY accept numbers only") from exc
        out.append(num)
    return out


def upsert_tool(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    """Replace one tool entry from flat form fields (robot-style overwrite)."""
    visible = fields.get("visible", True)
    item: dict[str, Any] = {}

    for name in ("description", "note", "vision_id"):
        val = fields.get(name, "")
        if isinstance(val, str) and val.strip() != "":
            item[name] = val.strip()
        elif val not in ("", None) and not isinstance(val, str):
            item[name] = val

    gripper_port = fields.get("gripper_port", "")
    if isinstance(gripper_port, str) and gripper_port.strip() != "":
        item["gripper"] = {"port": gripper_port.strip()}

    tool_pose = _parse_number_list(
        [fields.get(f"tool_{n}", "") for n in ("x", "y", "z", "r", "p", "yaw")]
    )
    vision_pose = _parse_number_list(
        [fields.get(f"vision_{n}", "") for n in ("x", "y", "z", "r", "p", "yaw")]
    )
    ref_pose = _parse_number_list(
        [fields.get(f"ref_{n}", "") for n in ("x", "y", "z")]
    )

    calibration: dict[str, Any] = {}
    if tool_pose is not None:
        calibration["tool"] = tool_pose
    if ref_pose is not None:
        calibration["tool_ref_point"] = ref_pose
    if vision_pose is not None:
        calibration["vision"] = vision_pose
    if calibration:
        item["calibration"] = calibration

    data[key] = _with_visible_last(item, bool(visible))


def tool_to_public(key: str, item: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested tool YAML for web form (same response style as robots)."""
    out: dict[str, Any] = {
        "id": key,
        "visible": bool(item.get("visible", True)),
        "description": item.get("description", "") or "",
        "note": item.get("note", "") or "",
        "vision_id": item.get("vision_id", "") or "",
        "gripper_port": "",
    }
    gripper = item.get("gripper")
    if isinstance(gripper, dict) and gripper.get("port") is not None:
        out["gripper_port"] = str(gripper.get("port"))

    for prefix in ("tool", "vision", "ref"):
        for n in ("x", "y", "z", "r", "p", "yaw"):
            if prefix == "ref" and n in ("r", "p", "yaw"):
                continue
            out[f"{prefix}_{n}"] = ""

    cal = item.get("calibration")
    if isinstance(cal, dict):
        tool = cal.get("tool")
        if isinstance(tool, list):
            for i, n in enumerate(("x", "y", "z", "r", "p", "yaw")):
                if i < len(tool) and tool[i] is not None:
                    out[f"tool_{n}"] = tool[i]
        vision = cal.get("vision")
        if isinstance(vision, list):
            for i, n in enumerate(("x", "y", "z", "r", "p", "yaw")):
                if i < len(vision) and vision[i] is not None:
                    out[f"vision_{n}"] = vision[i]
        ref = cal.get("tool_ref_point")
        if isinstance(ref, list):
            for i, n in enumerate(("x", "y", "z")):
                if i < len(ref) and ref[i] is not None:
                    out[f"ref_{n}"] = ref[i]
    return out
