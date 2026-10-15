#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load / save welding_param_<id>.yaml files (does not touch source dir)."""

from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent / "robot_data" / "user0"
MASTER_DIR = BASE_DIR

WELDING_ID_RE = re.compile(r"^welding_param_(\d+)$")
WELDING_FILE_RE = re.compile(r"^welding_param_(\d+)\.yaml$", re.IGNORECASE)

FORM_SCALAR_KEYS = (
    "description",
    "weld_length",
    "weld_speed",
    "safe_height",
    "executor_type",
)

DEFAULT_NEW_ITEM: dict[str, Any] = {
    "description": "",
    "weld_length": 900.0,
    "weld_speed": 1.5,
    "safe_height": 30.0,
    "actions_offset": [0, 0],
    "actions": [],
    "executor_type": "point_pairs",
}


class FlowList(list):
    """YAML list dumped in flow style, e.g. [0, 0]."""


def _represent_flow_list(dumper: yaml.Dumper, data: FlowList):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    )


yaml.add_representer(FlowList, _represent_flow_list)


def is_welding_entry(key: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(WELDING_ID_RE.match(key))


def validate_welding_id(key: str) -> str:
    text = (key or "").strip()
    if not WELDING_ID_RE.match(text):
        raise ValueError("ID must be welding_param_<number>")
    return text


def _with_visible_last(data: dict[str, Any], visible: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k == "visible":
            continue
        out[k] = v
    out["visible"] = bool(visible)
    return out


def _maybe_flow_list(value: Any) -> Any:
    if (
        isinstance(value, list)
        and not isinstance(value, FlowList)
        and len(value) <= 8
        and all(not isinstance(x, (list, dict)) for x in value)
    ):
        return FlowList(value)
    return value


def _prepare_for_dump(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in item.items():
        if key == "visible":
            continue
        if isinstance(value, dict):
            nested: dict[str, Any] = {}
            for nk, nv in value.items():
                if isinstance(nv, list) and all(
                    not isinstance(x, (list, dict)) for x in nv
                ):
                    nested[nk] = _maybe_flow_list(nv)
                else:
                    nested[nk] = nv
            out[key] = nested
        elif isinstance(value, list):
            out[key] = _maybe_flow_list(value)
        else:
            out[key] = value
    out["visible"] = bool(item.get("visible", True))
    return out


def _normalize_loaded(raw: dict[str, Any]) -> dict[str, Any]:
    visible = raw.get("visible", True)
    if isinstance(visible, str):
        visible = visible.strip().lower() not in {"false", "0", "no"}
    item = {k: v for k, v in raw.items() if k != "visible"}
    return _with_visible_last(item, bool(visible))


def _id_sort_key(key: str) -> tuple[str, int]:
    m = WELDING_ID_RE.match(key)
    if not m:
        return (key, 0)
    return ("welding_param_", int(m.group(1)))


def _master_files() -> list[Path]:
    return sorted(
        [
            p
            for p in MASTER_DIR.glob("welding_param_*.yaml")
            if WELDING_FILE_RE.match(p.name)
        ],
        key=lambda p: int(WELDING_FILE_RE.match(p.name).group(1)),  # type: ignore[union-attr]
    )


def migrate_from_source(force: bool = False) -> None:
    """Copy welding_param_*.yaml from source when master has none (or force)."""
    master_files = _master_files()
    if master_files and not force:
        return
    if not SOURCE_DIR.is_dir():
        return
    for src in sorted(SOURCE_DIR.glob("welding_param_*.yaml")):
        if not WELDING_FILE_RE.match(src.name):
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
        m = WELDING_FILE_RE.match(path.name)
        if not m:
            continue
        key = f"welding_param_{m.group(1)}"
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"{path.name} root must be a mapping")
        result[key] = _normalize_loaded(raw)
    return result


def write_entry(key: str, item: dict[str, Any]) -> None:
    """Write a single welding_param_<id>.yaml file."""
    key = validate_welding_id(key)
    if not isinstance(item, dict):
        raise ValueError("welding entry must be a mapping")
    path = MASTER_DIR / f"{key}.yaml"
    prepared = _prepare_for_dump(_normalize_loaded(item))
    text = yaml.dump(
        prepared,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    path.write_text(text, encoding="utf-8")


def remove_entry_file(key: str) -> None:
    key = validate_welding_id(key)
    (MASTER_DIR / f"{key}.yaml").unlink(missing_ok=True)


def save_data(data: dict[str, Any]) -> None:
    """Full sync: write all welding entries; remove master files no longer present."""
    keep: set[Path] = set()
    for key, value in data.items():
        if not is_welding_entry(key, value):
            continue
        write_entry(key, value)
        keep.add((MASTER_DIR / f"{key}.yaml").resolve())

    for path in _master_files():
        if path.resolve() not in keep:
            path.unlink(missing_ok=True)


def list_welding_ids(data: dict[str, Any], *, include_hidden: bool = False) -> list[str]:
    ids = []
    for key, value in data.items():
        if not is_welding_entry(key, value):
            continue
        if not include_hidden and not value.get("visible", True):
            continue
        ids.append(key)
    return sorted(ids, key=_id_sort_key)


def next_id(data: dict[str, Any], prefix: str = "welding_param_") -> str:
    nums = []
    for key in data:
        m = WELDING_ID_RE.match(key)
        if m:
            nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 1
    return f"welding_param_{n}"


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


def _parse_scalar(name: str, val: Any) -> Any | None:
    if val is None:
        return None
    if isinstance(val, str):
        text = val.strip()
        if text == "":
            return None
        if name in ("weld_length", "weld_speed", "safe_height"):
            try:
                return float(text)
            except ValueError as exc:
                raise ValueError(f"{name} must be a number") from exc
        return text
    if name in ("weld_length", "weld_speed", "safe_height"):
        return float(val)
    return val


def _dump_yaml_rest(rest: dict[str, Any]) -> str:
    if not rest:
        return ""
    prepared: dict[str, Any] = {}
    for key, value in rest.items():
        if isinstance(value, list):
            prepared[key] = _maybe_flow_list(value)
        elif isinstance(value, dict):
            nested: dict[str, Any] = {}
            for nk, nv in value.items():
                nested[nk] = _maybe_flow_list(nv) if isinstance(nv, list) else nv
            prepared[key] = nested
        else:
            prepared[key] = value
    return yaml.dump(
        prepared,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    ).rstrip() + "\n"


def _parse_yaml_rest(text: str) -> dict[str, Any]:
    raw = yaml.safe_load(text or "") or {}
    if raw == "":
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("YAML body must be a mapping of extra fields")
    return raw


def upsert_welding(data: dict[str, Any], key: str, fields: dict[str, Any]) -> None:
    """Replace one welding entry from form fields; preserve unknown keys via yaml_rest."""
    key = validate_welding_id(key)
    visible = fields.get("visible", True)
    item: dict[str, Any] = {}

    rest = _parse_yaml_rest(str(fields.get("yaml_rest", "") or ""))
    for rk, rv in rest.items():
        if rk in FORM_SCALAR_KEYS or rk == "visible":
            continue
        item[rk] = rv

    for name in FORM_SCALAR_KEYS:
        parsed = _parse_scalar(name, fields.get(name, ""))
        if parsed is None:
            continue
        item[name] = parsed

    data[key] = _with_visible_last(item, bool(visible))


def welding_to_public(key: str, item: dict[str, Any]) -> dict[str, Any]:
    rest = {
        k: v
        for k, v in item.items()
        if k not in FORM_SCALAR_KEYS and k != "visible"
    }
    out: dict[str, Any] = {
        "id": key,
        "visible": bool(item.get("visible", True)),
        "description": item.get("description", "") or "",
        "weld_length": item.get("weld_length", "")
        if item.get("weld_length") is not None
        else "",
        "weld_speed": item.get("weld_speed", "")
        if item.get("weld_speed") is not None
        else "",
        "safe_height": item.get("safe_height", "")
        if item.get("safe_height") is not None
        else "",
        "executor_type": item.get("executor_type", "") or "",
        "yaml_rest": _dump_yaml_rest(rest),
    }
    return out


def default_public_new(next_key: str) -> dict[str, Any]:
    return welding_to_public(next_key, _with_visible_last(copy.deepcopy(DEFAULT_NEW_ITEM), True))
