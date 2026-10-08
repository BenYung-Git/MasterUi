#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZiYan Master UI — web entrypoint."""

from __future__ import annotations

import webbrowser
from threading import Timer

import uvicorn


HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    url = f"http://{HOST}:{PORT}/"
    Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Master UI (web): {url}")
    uvicorn.run("web_app:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
