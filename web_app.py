#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI web app for Master UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from robot_setting_store import (
    copy_entry as copy_robot_entry,
    list_group_ids,
    list_robot_ids,
    load_data,
    next_id,
    save_data,
    soft_delete as soft_delete_robot,
    soft_restore as soft_restore_robot,
    upsert_group,
    upsert_robot,
)
from tool_setting_store import (
    copy_entry as copy_tool_entry,
    list_tool_ids,
    load_data as load_tool_data,
    next_id as next_tool_id,
    save_data as save_tool_data,
    soft_delete as soft_delete_tool,
    soft_restore as soft_restore_tool,
    tool_to_public,
    upsert_tool,
)

BASE_DIR = Path(__file__).resolve().parent
I18N_PATH = BASE_DIR / "i18n.json"
STATIC_DIR = BASE_DIR / "static"

ROBOT_FIELDS = (
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

app = FastAPI(title="Master UI", version="1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class RobotPayload(BaseModel):
    id: str = Field(..., min_length=1)
    original_id: str | None = None
    ip: str = ""
    maker: str = ""
    product: str = ""
    arm: str = ""
    cab: str = ""
    version_scb: str = ""
    version_controller: str = ""
    version_servo: str = ""
    payload: Any = ""
    visible: bool = True


class GroupPayload(BaseModel):
    id: str = Field(..., min_length=1)
    original_id: str | None = None
    maker: str = "robot_team"
    robots: str = ""
    visible: bool = True


class ToolPayload(BaseModel):
    id: str = Field(..., min_length=1)
    original_id: str | None = None
    description: str = ""
    note: str = ""
    vision_id: str = ""
    gripper_port: str = ""
    tool_x: Any = ""
    tool_y: Any = ""
    tool_z: Any = ""
    tool_r: Any = ""
    tool_p: Any = ""
    tool_yaw: Any = ""
    vision_x: Any = ""
    vision_y: Any = ""
    vision_z: Any = ""
    vision_r: Any = ""
    vision_p: Any = ""
    vision_yaw: Any = ""
    ref_x: Any = ""
    ref_y: Any = ""
    ref_z: Any = ""
    visible: bool = True


def _load_i18n() -> dict:
    with I18N_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _item_public(key: str, item: dict[str, Any]) -> dict[str, Any]:
    out = {"id": key, "visible": bool(item.get("visible", True))}
    for k, v in item.items():
        if k == "visible":
            continue
        if k == "robots" and isinstance(v, list):
            out[k] = ", ".join(str(x) for x in v)
        else:
            out[k] = v
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/i18n")
def api_i18n() -> dict:
    return _load_i18n()


@app.get("/api/robots")
def api_robots() -> dict:
    data = load_data()
    ids = list_robot_ids(data, include_hidden=True)
    items = [_item_public(i, data[i]) for i in ids]
    return {"ids": ids, "items": items, "next_id": next_id(data, "robot")}


@app.get("/api/groups")
def api_groups() -> dict:
    data = load_data()
    ids = list_group_ids(data, include_hidden=True)
    items = [_item_public(i, data[i]) for i in ids]
    return {"ids": ids, "items": items, "next_id": next_id(data, "group")}


@app.post("/api/robots")
def api_save_robot(payload: RobotPayload) -> dict:
    data = load_data()
    key = payload.id.strip()
    if not key:
        raise HTTPException(400, "ID required")
    old = (payload.original_id or "").strip() or None
    if old is None and key in data:
        raise HTTPException(400, "ID exists")
    if old and old != key:
        if key in data:
            raise HTTPException(400, "ID exists")
        if old in data:
            del data[old]
    fields: dict[str, Any] = {"visible": payload.visible}
    for name in ROBOT_FIELDS:
        val = getattr(payload, name)
        if name == "payload" and val != "" and val is not None:
            if isinstance(val, str):
                text = val.strip()
                if text == "":
                    continue
                try:
                    fields[name] = float(text) if "." in text else int(text)
                except ValueError:
                    fields[name] = text
            else:
                fields[name] = val
        elif isinstance(val, str):
            if val.strip() != "":
                fields[name] = val.strip()
        elif val is not None and val != "":
            fields[name] = val
    upsert_robot(data, key, fields)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(key, data[key])}


@app.post("/api/groups")
def api_save_group(payload: GroupPayload) -> dict:
    data = load_data()
    key = payload.id.strip()
    if not key:
        raise HTTPException(400, "ID required")
    old = (payload.original_id or "").strip() or None
    if old is None and key in data:
        raise HTTPException(400, "ID exists")
    if old and old != key:
        if key in data:
            raise HTTPException(400, "ID exists")
        if old in data:
            del data[old]
    upsert_group(
        data,
        key,
        {
            "maker": payload.maker.strip() or "robot_team",
            "robots": payload.robots,
            "visible": payload.visible,
        },
    )
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(key, data[key])}


@app.post("/api/robots/{item_id}/copy")
def api_copy_robot(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    new_id = copy_robot_entry(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "id": new_id, "item": _item_public(new_id, data[new_id])}


@app.post("/api/groups/{item_id}/copy")
def api_copy_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    new_id = copy_robot_entry(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "id": new_id, "item": _item_public(new_id, data[new_id])}


@app.post("/api/robots/{item_id}/disable")
def api_disable_robot(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_delete_robot(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/robots/{item_id}/enable")
def api_enable_robot(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_restore_robot(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/groups/{item_id}/disable")
def api_disable_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_delete_robot(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/groups/{item_id}/enable")
def api_enable_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_restore_robot(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.get("/api/tools")
def api_tools() -> dict:
    data = load_tool_data()
    ids = list_tool_ids(data, include_hidden=True)
    items = [tool_to_public(i, data[i]) for i in ids]
    return {"ids": ids, "items": items, "next_id": next_tool_id(data, "tool")}


@app.post("/api/tools")
def api_save_tool(payload: ToolPayload) -> dict:
    data = load_tool_data()
    key = payload.id.strip()
    if not key:
        raise HTTPException(400, "ID required")
    old = (payload.original_id or "").strip() or None
    if old is None and key in data:
        raise HTTPException(400, "ID exists")
    if old and old != key:
        if key in data:
            raise HTTPException(400, "ID exists")
        if old in data:
            del data[old]
    fields = payload.model_dump()
    upsert_tool(data, key, fields)
    save_tool_data(data)
    data = load_tool_data()
    return {"ok": True, "item": tool_to_public(key, data[key])}


@app.post("/api/tools/{item_id}/copy")
def api_copy_tool(item_id: str) -> dict:
    data = load_tool_data()
    if item_id not in data or item_id not in list_tool_ids(data, include_hidden=True):
        raise HTTPException(404, "Not found")
    new_id = copy_tool_entry(data, item_id)
    save_tool_data(data)
    data = load_tool_data()
    return {"ok": True, "id": new_id, "item": tool_to_public(new_id, data[new_id])}


@app.post("/api/tools/{item_id}/disable")
def api_disable_tool(item_id: str) -> dict:
    data = load_tool_data()
    if item_id not in data or item_id not in list_tool_ids(data, include_hidden=True):
        raise HTTPException(404, "Not found")
    soft_delete_tool(data, item_id)
    save_tool_data(data)
    data = load_tool_data()
    return {"ok": True, "item": tool_to_public(item_id, data[item_id])}


@app.post("/api/tools/{item_id}/enable")
def api_enable_tool(item_id: str) -> dict:
    data = load_tool_data()
    if item_id not in data or item_id not in list_tool_ids(data, include_hidden=True):
        raise HTTPException(404, "Not found")
    soft_restore_tool(data, item_id)
    save_tool_data(data)
    data = load_tool_data()
    return {"ok": True, "item": tool_to_public(item_id, data[item_id])}
