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
    new_id = copy_entry(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "id": new_id, "item": _item_public(new_id, data[new_id])}


@app.post("/api/groups/{item_id}/copy")
def api_copy_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    new_id = copy_entry(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "id": new_id, "item": _item_public(new_id, data[new_id])}


@app.post("/api/robots/{item_id}/disable")
def api_disable_robot(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_delete(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/robots/{item_id}/enable")
def api_enable_robot(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_restore(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/groups/{item_id}/disable")
def api_disable_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_delete(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}


@app.post("/api/groups/{item_id}/enable")
def api_enable_group(item_id: str) -> dict:
    data = load_data()
    if item_id not in data:
        raise HTTPException(404, "Not found")
    soft_restore(data, item_id)
    save_data(data)
    data = load_data()
    return {"ok": True, "item": _item_public(item_id, data[item_id])}
