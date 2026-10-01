"""Traffic reports for the password maker's Traffic page.

Visits (page loads) and edits are collected in memory and sent in small signed batches to the
password maker (TRAFFIC_URL), which turns them into daily totals. The visitor's IP address is only
used there to find the country and to count unique visitors with a daily-changing hash; it is
never stored. Without TRAFFIC_URL and TRAFFIC_KEY (set by the password maker's "Set site keys"),
nothing is sent.
"""
from __future__ import annotations

import atexit
import hashlib
import hmac
import json
import logging
import os
import signal
import threading
import time
import urllib.request

from flask import Flask, request

TRAFFIC_URL = os.environ.get("TRAFFIC_URL", "").strip().rstrip("/")
TRAFFIC_KEY = os.environ.get("TRAFFIC_KEY", "").strip()
SEND_EVERY = 120  # seconds between batches
MAX_QUEUE = 5000

log = logging.getLogger("traffic")
_queue: list[dict] = []
_lock = threading.Lock()


def _ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() if fwd else (request.remote_addr or "")


def _record(kind: str, extra: dict | None = None) -> None:
    event = {"t": int(time.time()), "kind": kind, "host": request.host.lower(), "ip": _ip(),
             "ua": request.headers.get("User-Agent", "")[:300], "ref": request.headers.get("Referer", "")[:300],
             "lang": request.headers.get("Accept-Language", "")[:40]}
    if extra:
        event.update(extra)
    with _lock:
        if len(_queue) < MAX_QUEUE:
            _queue.append(event)


def _send() -> None:
    with _lock:
        batch = _queue[:]
        _queue.clear()
    if not batch:
        return
    body = json.dumps({"events": batch}).encode()
    sig = hmac.new(TRAFFIC_KEY.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(TRAFFIC_URL + "/api/traffic/ingest", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-Traffic-Sig": sig,
                                          "User-Agent": "Mozilla/5.0 (editor traffic report)"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            resp.read()
    except Exception as e:  # noqa: BLE001 - put them back and try again later
        log.warning("traffic report failed (%s); will retry", e)
        with _lock:
            _queue[:0] = batch[: MAX_QUEUE - len(_queue)]


def _loop() -> None:
    while True:
        time.sleep(SEND_EVERY)
        _send()


def install(app: Flask) -> None:
    if not (TRAFFIC_URL and TRAFFIC_KEY):
        return

    @app.after_request
    def count(response):
        try:
            if request.method == "GET" and request.path == "/" and response.status_code < 400:
                _record("visit")
            elif request.method == "POST" and request.path == "/api/edit":
                ok = response.status_code < 400
                if ok and response.is_json:
                    ok = bool((response.get_json(silent=True) or {}).get("ok", True))
                _record("edit", {"mode": (request.form.get("mode") or "")[:20], "ok": ok})
        except Exception:  # noqa: BLE001 - counting must never break the site
            log.exception("couldn't count a request")
        return response

    threading.Thread(target=_loop, daemon=True).start()
    atexit.register(_send)
    # Render stops idle sites with SIGTERM (which skips atexit): send what's left first.
    try:
        previous = signal.getsignal(signal.SIGTERM)

        def on_term(signum, frame):
            _send()
            if callable(previous):
                previous(signum, frame)
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, on_term)
    except ValueError:  # not the main thread (e.g. tests)
        pass
