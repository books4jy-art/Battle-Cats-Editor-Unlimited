"""Extra protection for every page of this site.

- Bot blocking: visits from scripts and automated tools (curl, Python, headless browsers,
  crawlers, ...) are refused, and every form or API post must come from this site's own page.
- Embedding protection: security headers stop other websites from showing this site inside
  theirs, and stop the page from loading scripts or sending data anywhere else.
- Stricter lockout: 8 wrong passwords within 15 minutes block that device for 1 hour.
- Email alerts: the owner gets an email when a device is blocked, or when many wrong
  passwords come in from different devices.

Environment (set by the password maker's "Set site keys" workflow):
  SMTP_USER / SMTP_PASSWORD  Gmail address and app password that send the alerts
  ALERT_TO                   optional; who gets the alerts (default: SMTP_USER)
  SMTP_HOST / SMTP_PORT      optional; default smtp.gmail.com:465
Without SMTP_USER / SMTP_PASSWORD the alerts are only written to the log.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from urllib.parse import urlsplit

from flask import Flask, jsonify, request

TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
ALERT_TO = os.environ.get("ALERT_TO", "").strip() or SMTP_USER
SMTP_HOST, SMTP_PORT = os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))

MAX_FAILURES, FAILURE_WINDOW, LOCK_SECONDS = 8, 15 * 60, 60 * 60
SITE_WIDE_ALERT = 30        # wrong passwords within an hour, from all devices together
MAX_ALERTS_PER_DAY = 20     # so an attack can't flood the inbox
KST = dt.timezone(dt.timedelta(hours=9))

# Tools and crawlers that name themselves in their User-Agent. Real browsers never match.
BOT_AGENTS = re.compile(
    r"curl|wget|python|httpx|aiohttp|go-http|java/|okhttp|libwww|perl|ruby|php|node-fetch|axios|undici"
    r"|postman|insomnia|scrapy|headless|phantomjs|selenium|puppeteer|playwright|powershell|winhttp"
    r"|httpclient|crawl|spider|slurp|scanner|nmap|nikto|sqlmap|zgrab|yeti/|facebookexternalhit"
    r"|bot[/;)]|bot \(|robot|bot$", re.I)
# Uptime checkers and Render's own health check may still load the front page.
MONITOR_AGENTS = re.compile(r"render|uptime|cron-job|statuscake|pingdom|freshping|hetrix|go-http", re.I)
BLOCKED = "Access blocked. Open this site in a normal web browser. / 접근이 차단되었어요. 일반 웹 브라우저로 열어 주세요."

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

log = logging.getLogger("shield")
_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}
_all_failures: list[float] = []
_alerts_sent: list[float] = []
_last_site_alert = 0.0


def client_ip() -> str:
    if TRUST_PROXY:
        # Cloudflare (in front of Render) sets CF-Connecting-IP to the real address; the first
        # X-Forwarded-For entry is whatever the visitor's browser sent, so it can be faked.
        real = request.headers.get("CF-Connecting-IP") or request.headers.get("True-Client-IP")
        if real:
            return real.strip()
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ---- stricter lockout + alerts ----

def locked(ip: str) -> bool:
    with _lock:
        return _locked_until.get(ip, 0) > time.time()


def failed(ip: str, what: str = "editor password") -> None:
    """Count one wrong password from this device; block it and email the owner when it's too many."""
    now = time.time()
    alerts = []
    with _lock:
        recent = [t for t in _failures.get(ip, []) if now - t < FAILURE_WINDOW] + [now]
        _failures[ip] = recent
        _all_failures[:] = [t for t in _all_failures if now - t < 3600] + [now]
        if len(recent) >= MAX_FAILURES and _locked_until.get(ip, 0) <= now:
            _locked_until[ip] = now + LOCK_SECONDS
            _failures.pop(ip, None)
            alerts.append((f"a device was blocked after {MAX_FAILURES} wrong passwords",
                           f"The device at IP address {ip} typed a wrong {what} {MAX_FAILURES} times within "
                           f"{FAILURE_WINDOW // 60} minutes, so it is blocked for {LOCK_SECONDS // 60} minutes."))
        global _last_site_alert
        if len(_all_failures) >= SITE_WIDE_ALERT and now - _last_site_alert > 3600:
            _last_site_alert = now
            alerts.append(("many wrong passwords",
                           f"{len(_all_failures)} wrong {what}s were typed in the last hour, from different "
                           f"devices. Someone may be trying to guess it."))
        if len(_failures) > 5000 or len(_locked_until) > 5000:  # keep memory small
            for d in (_failures, _locked_until):
                d.clear()
    for subject, text in alerts:
        alert(subject, text)


def alert(subject: str, text: str) -> None:
    """Email the owner (in the background) about something suspicious on this site."""
    site = request.host if request else "editor"
    when = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    agent = request.headers.get("User-Agent", "-") if request else "-"
    body = (f"{text}\n\nSite: https://{site}\nTime: {when}\nBrowser: {agent}\n\n"
            "Nothing needs to be done: the site already blocks the device. If this keeps happening, "
            "consider changing the password (change MASTER_KEY and run Set site keys).")
    log.warning("ALERT %s: %s", subject, text)
    now = time.time()
    with _lock:
        _alerts_sent[:] = [t for t in _alerts_sent if now - t < 86400]
        if len(_alerts_sent) >= MAX_ALERTS_PER_DAY:
            return
        _alerts_sent.append(now)
    if not (SMTP_USER and SMTP_PASSWORD and ALERT_TO):
        return
    msg = EmailMessage()
    msg["Subject"] = f"⚠ Security alert: {subject} ({site.split('.')[0]})"
    msg["From"], msg["To"] = SMTP_USER, ALERT_TO
    msg.set_content(body)
    threading.Thread(target=_send, args=(msg,), daemon=True).start()


def _send(msg: EmailMessage) -> None:
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=30) as smtp:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception:  # noqa: BLE001 - an alert must never break the site
        log.exception("couldn't send the alert email")


# ---- bot blocking + embedding protection ----

def _is_bot() -> bool:
    if not request.headers.get("X-Forwarded-For"):
        return False  # not from the internet (Render's health check, or running on your own computer)
    agent = request.headers.get("User-Agent", "")
    if request.method in ("GET", "HEAD") and request.path in ("/", "/robots.txt") and (
            not agent or MONITOR_AGENTS.search(agent)):
        return False
    return not agent or bool(BOT_AGENTS.search(agent))


def _foreign_post() -> bool:
    """Forms and API calls must be sent by this site's own page, not another site or a script."""
    if request.method != "POST":
        return False
    source = request.headers.get("Origin") or request.headers.get("Referer") or ""
    return urlsplit(source).netloc.lower() != request.host.lower()


def install(app: Flask) -> None:
    @app.before_request
    def shield_check():
        if _is_bot() or _foreign_post():
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": BLOCKED}), 403
            return app.response_class(BLOCKED, status=403, mimetype="text/plain")
        return None

    @app.after_request
    def security_headers(response):
        headers = response.headers
        headers.setdefault("Content-Security-Policy", CSP)
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response
