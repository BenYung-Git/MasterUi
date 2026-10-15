#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load / save welding_state_<id>.json files (does not touch source dir)."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent / "robot_data" / "user0"
MASTER_DIR = BASE_DIR

STATE_ID_RE = re.compile(r"^welding_state_(\d+)$")
STATE_FILE_RE = re.compile(r"^welding_state_(\d+)\.json$", re.IGNORECASE)

DF_DICT_KEYS = ("x", "y", "z", "type", "rev_idx")

DEFAULT_NEW_ITEM: dict[str, Any] = {
    "df_dict": {
        "x": [],
        "y": [],
        "z": [],
        "type": [],
        "rev_idx": [],
    },
    "target_rt_rev_list": [],
    "safe_return_rt": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
}


def is_state_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(STATE_ID_RE.match(key))


def validate_state_id(key: str) -> str:
    text = (key or "").strip()
    if not text:
        raise ValueError("ID required")
    if not STATE_ID_RE.match(text):
        raise ValueError("ID must be welding_state_<number>")
    return text


def work_id_from_key(key: str) -> int:
    m = STATE_ID_RE.match(validate_state_id(key))
    assert m is not None
    return int(m.group(1))


def _with_visible_last(data: dict[str, Any], visible: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k == "visible":
            continue
        out[k] = v
    out["visible"] = bool(visible)
    return out


def _normalize_loaded(raw: dict[str, Any]) -> dict[str, Any]:
    visible = raw.get("visible", True)
    if isinstance(visible, str):
        visible = visible.strip().lower() not in {"false", "0", "no"}
    item = {k: v for k, v in raw.items() if k != "visible"}
    return _with_visible_last(item, bool(visible))


def _id_sort_key(key: str) -> tuple[str, int]:
    m = STATE_ID_RE.match(key)
    if not m:
        return (key, 0)
    return ("welding_state_", int(m.group(1)))


def _master_files() -> list[Path]:
    return sorted(
        [
            p
            for p in MASTER_DIR.glob("welding_state_*.json")
            if STATE_FILE_RE.match(p.name)
        ],
        key=lambda p: int(STATE_FILE_RE.match(p.name).group(1)),  # type: ignore[union-attr]
    )


def migrate_from_source(force: bool = False) -> None:
    master_files = _master_files()
    if master_files and not force:
        return
    if not SOURCE_DIR.is_dir():
        return
    for src in sorted(SOURCE_DIR.glob("welding_state_*.json")):
        if not STATE_FILE_RE.match(src.name):
            continue
        dst = MASTER_DIR / src.name
        if dst.exists() and not force:
            continue
        shutil.copy2(src, dst)


def ensure_master_files() -> None:
    migrate_from_source(force=False)


def load_data() -> dict[str, Any]:
    ensure_master_files()
    result: dict[str, Any] = {}
    for path in _master_files():
        m = STATE_FILE_RE.match(path.name)
        if not m:
            continue
        key = f"welding_state_{m.group(1)}"
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError(f"{path.name} root must be a JSON object")
        result[key] = _normalize_loaded(raw)
    return result


def _content_without_visible(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k != "visible"}


def write_entry(key: str, item: dict[str, Any]) -> None:
    key = validate_state_id(key)
    if not isinstance(item, dict):
        raise ValueError("state entry must be a JSON object")
    normalized = _normalize_loaded(item)
    validate_state_content(normalized)
    path = MASTER_DIR / f"{key}.json"
    payload = _with_visible_last(_content_without_visible(normalized), bool(normalized.get("visible", True)))
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def remove_entry_file(key: str) -> None:
    key = validate_state_id(key)
    (MASTER_DIR / f"{key}.json").unlink(missing_ok=True)


def list_state_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_state_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def next_id(data: dict[str, Any], prefix: str = "welding_state_") -> str:
    nums = []
    for key in data:
        m = STATE_ID_RE.match(key)
        if m:
            nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 1
    return f"welding_state_{n}"


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
    new_key = next_id(data)
    cloned = copy.deepcopy(data[key])
    cloned = _with_visible_last(cloned, True)
    data[new_key] = cloned
    return new_key


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_state_content(item: dict[str, Any]) -> None:
    """Validate optional known fields when present; do not invent missing keys."""
    if not isinstance(item, dict):
        raise ValueError("JSON root must be an object")

    if "df_dict" in item:
        df = item["df_dict"]
        if not isinstance(df, dict):
            raise ValueError("df_dict must be an object")
        lengths: list[int] = []
        for name in DF_DICT_KEYS:
            if name not in df:
                raise ValueError(f"df_dict missing key: {name}")
            arr = df[name]
            if not isinstance(arr, list):
                raise ValueError(f"df_dict.{name} must be an array")
            lengths.append(len(arr))
        if lengths and len(set(lengths)) != 1:
            raise ValueError("df_dict x/y/z/type/rev_idx length mismatch")

    if "target_rt_rev_list" in item:
        tr = item["target_rt_rev_list"]
        if not isinstance(tr, list):
            raise ValueError("target_rt_rev_list must be an array")
        for i, row in enumerate(tr):
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError(f"target_rt_rev_list[{i}] must have 6 numbers")
            if not all(_is_number(x) for x in row):
                raise ValueError(f"target_rt_rev_list[{i}] must have 6 numbers")

    if "safe_return_rt" in item:
        sr = item["safe_return_rt"]
        if not isinstance(sr, list) or len(sr) != 6:
            raise ValueError("safe_return_rt must have 6 numbers")
        if not all(_is_number(x) for x in sr):
            raise ValueError("safe_return_rt must have 6 numbers")


def parse_json_text(text: str) -> dict[str, Any]:
    raw_text = text if text is not None else ""
    try:
        raw = json.loads(raw_text) if str(raw_text).strip() != "" else {}
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")
    # Ignore accidental visible inside editor body; Master UI owns visibility.
    raw = {k: v for k, v in raw.items() if k != "visible"}
    validate_state_content(raw)
    return raw


def upsert_state(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    key = validate_state_id(key)
    visible = fields.get("visible", True)
    body = parse_json_text(str(fields.get("json_text", "") or ""))
    data[key] = _with_visible_last(body, bool(visible))


def _summary_from_item(item: dict[str, Any]) -> dict[str, Any]:
    df_points: int | None = None
    df = item.get("df_dict")
    if isinstance(df, dict) and isinstance(df.get("x"), list):
        df_points = len(df["x"])

    target_count: int | None = None
    tr = item.get("target_rt_rev_list")
    if isinstance(tr, list):
        target_count = len(tr)

    safe_return = ""
    sr = item.get("safe_return_rt")
    if isinstance(sr, list):
        safe_return = json.dumps(sr, ensure_ascii=False)

    keys = [k for k in item.keys() if k != "visible"]
    return {
        "df_points": df_points,
        "target_rt_count": target_count,
        "safe_return_rt": safe_return,
        "top_keys": keys,
    }


def state_to_public(key: str, item: dict[str, Any]) -> dict[str, Any]:
    body = _content_without_visible(item)
    summary = _summary_from_item(item)
    return {
        "id": key,
        "visible": bool(item.get("visible", True)),
        "filename": f"{key}.json",
        "work_id": work_id_from_key(key),
        "json_text": json.dumps(body, ensure_ascii=False, indent=4) + "\n",
        "df_points": summary["df_points"],
        "target_rt_count": summary["target_rt_count"],
        "safe_return_rt": summary["safe_return_rt"],
        "top_keys": summary["top_keys"],
    }


def default_public_new(next_key: str) -> dict[str, Any]:
    return state_to_public(
        next_key, _with_visible_last(copy.deepcopy(DEFAULT_NEW_ITEM), True)
    )
