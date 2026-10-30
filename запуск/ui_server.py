#!/usr/bin/env python3
"""Панель Сверх.Рой: отдаёт сайт и принимает план/позицию/находки с двух OrangePi."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import mission_log as mlog

HERE = Path(__file__).resolve().parent
_HTML_CANDIDATES = (
    HERE / "index-v2.html",
    HERE / "saytik__tutor" / "index-v2.html",
)
HTML_PATH = next((p for p in _HTML_CANDIDATES if p.is_file()), HERE / "index-v2.html")
HOST = "0.0.0.0"
PORT = 8080

_lock = threading.Lock()
STATE = {
    "live": False,
    "matrix": None,
    "drone1": [0, 0],
    "drone2": [4, 0],
    "route1": [],
    "route2": [],
    "region1": [],
    "region2": [],
    "gaps": [],
    "assignment": {},
    "split": {},
    "batteries": {},
    "events": [],
    "event_id": 0,
}


def snapshot():
    with _lock:
        return json.loads(json.dumps(STATE))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        line = fmt % args
        if "GET /api/state" in line:
            return
        mlog.info("%s %s", self.address_string(), line)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            data = HTML_PATH.read_bytes()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/state":
            body = json.dumps(snapshot()).encode("utf-8")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            mlog.error("битый JSON на %s от %s", path, self.address_string())
            self.send_error(400, "bad json")
            return

        with _lock:
            if path == "/api/plan":
                STATE["live"] = True
                for key in ("matrix", "drone1", "drone2", "route1", "route2",
                            "region1", "region2", "gaps", "assignment", "split"):
                    if key in data:
                        STATE[key] = data[key]
                mlog.info(
                    "план: дрон1=%s дрон2=%s маршрут1=%s маршрут2=%s назначение=%s",
                    data.get("drone1"), data.get("drone2"),
                    len(data.get("route1") or []), len(data.get("route2") or []),
                    data.get("assignment"),
                )
            elif path == "/api/telemetry":
                STATE["live"] = True
                drone_id = int(data.get("drone_id", 0))
                xy = [data.get("x", 0), data.get("y", 0)]
                if drone_id == 1:
                    STATE["drone1"] = xy
                elif drone_id == 2:
                    STATE["drone2"] = xy
                if data.get("battery") is not None:
                    STATE["batteries"][str(drone_id)] = data["battery"]
                mlog.info("телеметрия дрон%s -> %s батарея=%s", drone_id, xy, data.get("battery"))
            elif path == "/api/vision":
                STATE["live"] = True
                STATE["event_id"] += 1
                event = dict(data)
                event["id"] = STATE["event_id"]
                STATE["events"].append(event)
                STATE["events"] = STATE["events"][-80:]
                mlog.info(
                    "находка дрон%s %s в (%s,%s)",
                    event.get("drone_id"), event.get("color"), event.get("x"), event.get("y"),
                )
            else:
                mlog.warning("неизвестный POST %s", path)
                self.send_error(404)
                return

        body = b'{"ok":true}'
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    log_file = mlog.setup(name="ui_server", filename="ui_server.log")
    if not HTML_PATH.is_file():
        mlog.error("Нет файла сайта: %s", HTML_PATH)
        raise SystemExit(f"Нет файла сайта: {HTML_PATH}")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    mlog.info("Панель http://127.0.0.1:%s/  лог %s", PORT, log_file)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        mlog.info("панель остановлена")
    except Exception:
        mlog.exception("панель упала")
        raise


if __name__ == "__main__":
    main()
