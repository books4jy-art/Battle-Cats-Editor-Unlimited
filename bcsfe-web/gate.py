"""Password gate: the editor only opens with today's password from the password maker.

Set SITE_KEY (from the password maker's "Site keys" section) in this service's
environment. Without it the site stays locked. A login lasts until the password
changes at the next 6 PM (Korea time).
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import time

from flask import Flask, jsonify, make_response, redirect, request

import passwords as pw
import shield

LANG = "en"
TEXT = {
    "en": {
        "title": "Password required", "lead": "This editor is private. Enter today's password to open it.",
        "label": "Password", "button": "Open the editor",
        "hint": "The password changes every day at 6:00 PM (Korea time).",
        "wrong": "Wrong password. It may have changed at 6 PM.",
        "locked": "Too many wrong passwords. This device is blocked for 1 hour.",
        "unset": "Password protection isn't set up yet: add SITE_KEY to this site in Render.",
        "api": "The password changed or your login ended. Reload the page and enter the new password.",
        "brand": "Battle Cats Unlimited",
    },
    "ko": {
        "title": "비밀번호가 필요해요", "lead": "이 에디터는 비공개예요. 오늘의 비밀번호를 입력하세요.",
        "label": "비밀번호", "button": "에디터 열기",
        "hint": "비밀번호는 매일 오후 6시(한국 시간)에 바뀌어요.",
        "wrong": "비밀번호가 틀렸어요. 오후 6시에 바뀌었을 수 있어요.",
        "locked": "비밀번호를 너무 많이 틀렸어요. 이 기기는 1시간 동안 차단돼요.",
        "unset": "비밀번호 보호가 아직 설정되지 않았어요: Render에서 이 사이트에 SITE_KEY를 추가하세요.",
        "api": "비밀번호가 바뀌었거나 로그인이 끝났어요. 페이지를 새로고침하고 새 비밀번호를 입력하세요.",
        "brand": "세이브 에디터",
    },
}[LANG]

SITE_KEY = os.environ.get("SITE_KEY", "").strip()
TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
COOKIE = "editor_pass"
OPEN_PATHS = {"/gate", "/robots.txt"}


def _ip() -> str:
    if TRUST_PROXY:
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _token(p: int) -> str:
    return hmac.new(SITE_KEY.encode(), f"session:{p}".encode(), hashlib.sha256).hexdigest()[:40]


def _authed() -> bool:
    return bool(SITE_KEY) and hmac.compare_digest(request.cookies.get(COOKIE, ""), _token(pw.period()))


def _page(error: str = "", status: int = 200):
    t = {k: html.escape(v) for k, v in TEXT.items()}
    note = TEXT["unset"] if not SITE_KEY else error
    body = PAGE.format(lang=LANG, error=f'<div class="err">{html.escape(note)}</div>' if note else "",
                       disabled="disabled" if not SITE_KEY else "", **t)
    response = make_response(body, status)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def install(app: Flask) -> None:
    shield.install(app)  # bot blocking + security headers, with or without a password
    @app.before_request
    def require_password():
        if request.path in OPEN_PATHS or _authed():
            return None
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": TEXT["api"]}), 401
        return _page()

    @app.post("/gate")
    def gate_login():
        if not SITE_KEY:
            return _page(status=503)
        ip = _ip()
        if shield.locked(ip):
            return _page(TEXT["locked"], 429)
        given = (request.form.get("password") or "").strip()
        if not hmac.compare_digest(given.encode(), pw.password(SITE_KEY, pw.period()).encode()):
            shield.failed(ip)
            return _page(TEXT["wrong"], 401)
        p = pw.period()
        response = redirect("/", code=303)
        response.set_cookie(COOKIE, _token(p), max_age=max(60, pw.period_start(p + 1) - int(time.time())),
                            httponly=True, samesite="Lax",
                            secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https")
        return response


PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<title>{title}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230b0d12'/%3E%3Cpath d='M8 12 L8 6 L13 10 M24 12 L24 6 L19 10' stroke='%237dd3fc' stroke-width='2' fill='none' stroke-linejoin='round'/%3E%3Cellipse cx='16' cy='18' rx='9' ry='8' stroke='%237dd3fc' stroke-width='2' fill='none'/%3E%3C/svg%3E" />
<style>
  :root {{ --bg: #0b0d12; --sky-300: #7dd3fc; --sky-400: #38bdf8; --w-10: rgba(255,255,255,.10); --w-15: rgba(255,255,255,.15);
          --w-30: rgba(255,255,255,.30); --w-40: rgba(255,255,255,.40); --w-45: rgba(255,255,255,.45); --w-60: rgba(255,255,255,.60);
          --font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; background: var(--bg); color: #fff; font-family: var(--font); -webkit-font-smoothing: antialiased; }}
  header {{ display: flex; align-items: center; gap: 10px; padding: 20px 24px; }}
  header svg {{ width: 40px; height: 40px; }}
  .eyebrow {{ font-size: 14px; font-weight: 500; letter-spacing: .2em; text-transform: uppercase; color: var(--w-40); }}
  main {{ max-width: 420px; margin: 0 auto; padding: 48px 24px; }}
  .lock {{ width: 44px; height: 44px; color: var(--sky-300); }}
  h1 {{ font-weight: 300; font-size: 28px; letter-spacing: -.02em; margin: 16px 0 0; }}
  .lead {{ margin: 10px 0 0; font-size: 14px; line-height: 1.65; color: var(--w-45); }}
  .card {{ margin-top: 28px; border: 1px solid var(--w-10); background: rgba(255,255,255,.02); border-radius: 16px; padding: 24px; }}
  label span {{ display: block; font-size: 12px; color: var(--w-60); margin-bottom: 6px; }}
  input {{ width: 100%; height: 42px; padding: 0 12px; background: transparent; border: 1px solid var(--w-15); border-radius: 6px; color: #fff;
          font: 16px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: .06em; outline: none; }}
  input:focus {{ border-color: rgba(56,189,248,.6); box-shadow: 0 0 0 3px rgba(56,189,248,.12); }}
  button {{ margin-top: 14px; width: 100%; height: 40px; border: 0; border-radius: 6px; background: var(--sky-400); color: #0f172a;
           font: 500 14px var(--font); cursor: pointer; }}
  button:hover {{ background: var(--sky-300); }}
  button:disabled {{ opacity: .5; cursor: not-allowed; }}
  .err {{ margin-top: 14px; border: 1px solid rgba(248,113,113,.2); background: rgba(248,113,113,.05); color: #fca5a5;
         border-radius: 12px; padding: 10px 14px; font-size: 12px; line-height: 1.6; }}
  .hint {{ margin: 14px 0 0; font-size: 11px; line-height: 1.6; color: var(--w-30); }}
</style>
</head>
<body>
<header>
  <svg viewBox="0 0 40 40" aria-hidden="true">
    <rect x="1" y="1" width="38" height="38" rx="10" fill="rgba(255,255,255,.03)" stroke="rgba(255,255,255,.1)"/>
    <path d="M11 16 L11 9 L17 13.5 M29 16 L29 9 L23 13.5" stroke="#7dd3fc" stroke-width="1.8" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
    <ellipse cx="20" cy="22" rx="10.5" ry="9" stroke="#7dd3fc" stroke-width="1.8" fill="none"/>
    <circle cx="16" cy="21" r="1.2" fill="#7dd3fc"/><circle cx="24" cy="21" r="1.2" fill="#7dd3fc"/>
    <path d="M18.5 25 q1.5 1.2 3 0" stroke="#7dd3fc" stroke-width="1.4" fill="none" stroke-linecap="round"/>
  </svg>
  <span class="eyebrow">{brand}</span>
</header>
<main>
  <svg class="lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
  <h1>{title}</h1>
  <p class="lead">{lead}</p>
  <form class="card" method="post" action="/gate">
    <label><span>{label}</span><input name="password" type="password" autocomplete="current-password" autocapitalize="off" spellcheck="false" required autofocus {disabled} /></label>
    <button type="submit" {disabled}>{button}</button>
    {error}
    <p class="hint">{hint}</p>
  </form>
</main>
</body>
</html>
"""
