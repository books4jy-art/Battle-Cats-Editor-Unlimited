"""Daily site passwords.

The same rules run here and in each protected editor site (its gate.py), so the
sites never have to talk to each other: a site only knows its own SITE_KEY, and
the password maker derives every SITE_KEY from one MASTER_KEY.

Passwords change every day at 6 PM Korea time (UTC+9, no daylight saving).
"""
from __future__ import annotations

import hashlib
import hmac
import time

CHANGE_HOUR = 18        # 6 PM ...
UTC_OFFSET_HOURS = 9    # ... Korea time
LENGTH = 16
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"  # no I, O, l: easy to read and type
DIGITS = "23456789"                                             # no 0, 1
ALPHABET = LETTERS + DIGITS
DAY = 24 * 3600
_SHIFT = (CHANGE_HOUR - UTC_OFFSET_HOURS) * 3600


def period(now: float | None = None) -> int:
    """Number of the 24-hour window (6 PM to 6 PM) that `now` falls in."""
    return int(((time.time() if now is None else now) - _SHIFT) // DAY)


def period_start(p: int) -> int:
    """Unix time when window `p` starts (6 PM Korea time)."""
    return p * DAY + _SHIFT


def site_key(master_key: str, site_id: str) -> str:
    """The SITE_KEY a protected site needs, derived from the password maker's MASTER_KEY."""
    return hmac.new(master_key.encode(), f"site:{site_id}".encode(), hashlib.sha256).hexdigest()


def password(key: str, p: int) -> str:
    """16 letters and numbers (always at least one of each) for window `p`."""
    d = hmac.new(key.encode(), f"password:{p}".encode(), hashlib.sha512).digest()
    chars = [ALPHABET[b % len(ALPHABET)] for b in d[:LENGTH]]
    if not any(c in DIGITS for c in chars):
        chars[d[LENGTH] % LENGTH] = DIGITS[d[LENGTH + 1] % len(DIGITS)]
    if not any(c in LETTERS for c in chars):
        chars[d[LENGTH + 2] % LENGTH] = LETTERS[d[LENGTH + 3] % len(LETTERS)]
    return "".join(chars)
