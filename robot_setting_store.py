#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load / save / migrate master robot_setting.yaml (does not touch source file)."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
SOURCE_ROBOT_SETTING = (
    BASE_DIR.parent / "robot_data" / "user0" / "robot_setting.yaml"
)
MASTER_ROBOT_SETTING = BASE_DIR / "robot_setting.yaml"

HEADER_COMMENT = (
    "# Robot Ethernet setting: 192.168.2.64, sub mask 255.255.255.0, "
    "gate 192.168.2.1\n"
)


class FlowList(list):
    """YAML list dumped in flow style, e.g. ['robot11', 'robot12']."""


def _represent_flow_list(dumper: yaml.Dumper, data: FlowList):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    )


yaml.add_representer(FlowList, _represent_flow_list)


def is_group_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if key.startswith("group"):
        return True
    return "robots" in value


def is_robot_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if is_group_entry(key, value):
        return False
    return key.startswith("robot")


def _with_visible_last(data: dict[str, Any], visible: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k == "visible":
            continue
        if k == "robots" and isinstance(v, list):
            out[k] = FlowList(v)
        else:
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
        if "robots" in item and isinstance(item["robots"], list):
            item["robots"] = FlowList(list(item["robots"]))
        result[key] = _with_visible_last(item, bool(visible))
    return result


def migrate_from_source(force: bool = False) -> Path:
    """Copy all entries from source into master file; add visible at end."""
    if MASTER_ROBOT_SETTING.exists() and not force:
        return MASTER_ROBOT_SETTING
    if not SOURCE_ROBOT_SETTING.exists():
        raise FileNotFoundError(f"Source not found: {SOURCE_ROBOT_SETTING}")

    with SOURCE_ROBOT_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Source robot_setting.yaml root must be a mapping")

    migrated: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            migrated[key] = _with_visible_last(value, True)
        else:
            migrated[key] = value

    save_data(migrated)
    return MASTER_ROBOT_SETTING


def ensure_master_file() -> Path:
    return migrate_from_source(force=False)


def load_data() -> dict[str, Any]:
    ensure_master_file()
    with MASTER_ROBOT_SETTING.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("Master robot_setting.yaml root must be a mapping")
    return _normalize_loaded(raw)


def save_data(data: dict[str, Any]) -> None:
    normalized = _normalize_loaded(data)
    # Keep robots then groups order roughly: robots first by number, then groups.
    robot_keys = sorted(
        [k for k, v in normalized.items() if is_robot_entry(k, v)],
        key=_id_sort_key,
    )
    group_keys = sorted(
        [k for k, v in normalized.items() if is_group_entry(k, v)],
        key=_id_sort_key,
    )
    other_keys = [
        k
        for k in normalized
        if k not in robot_keys and k not in group_keys
    ]
    ordered = {k: normalized[k] for k in robot_keys + group_keys + other_keys}

    text = yaml.dump(
        ordered,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    MASTER_ROBOT_SETTING.write_text(HEADER_COMMENT + text, encoding="utf-8")


def _id_sort_key(key: str) -> tuple[str, int]:
    m = re.match(r"^([a-zA-Z_]+)(\d+)$", key)
    if not m:
        return (key, 0)
    return (m.group(1), int(m.group(2)))


def list_robot_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_robot_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def list_group_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_group_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def next_id(data: dict[str, Any], prefix: str) -> str:
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
    src = data[key]
    if is_group_entry(key, src):
        new_key = next_id(data, "group")
    else:
        new_key = next_id(data, "robot")
    cloned = copy.deepcopy(src)
    cloned = _with_visible_last(cloned, True)
    data[new_key] = cloned
    return new_key


def upsert_robot(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    visible = fields.get("visible", True)
    clean = {k: v for k, v in fields.items() if k != "visible" and v is not None}
    # Drop empty optional strings but keep payload 0 / False carefully
    cleaned: dict[str, Any] = {}
    for k, v in clean.items():
        if isinstance(v, str) and v.strip() == "" and k not in {"ip", "maker"}:
            continue
        cleaned[k] = v
    data[key] = _with_visible_last(cleaned, bool(visible))


def upsert_group(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    visible = fields.get("visible", True)
    maker = fields.get("maker", "robot_team")
    robots = fields.get("robots") or []
    if isinstance(robots, str):
        robots = [x.strip() for x in robots.split(",") if x.strip()]
    data[key] = _with_visible_last(
        {"maker": maker, "robots": FlowList(list(robots))},
        bool(visible),
    )
