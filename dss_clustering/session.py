"""Signed session token so a sign-in outlives the Google credential.

The sign-in button returns a Google ID token that expires after about an hour
and carries no refresh token, so it cannot serve as the session: when it lapsed,
the wizard fell back to the sign-in gate mid-analysis. Once Google has verified
who the user is, we mint our own token instead — ``<user_id>.<expiry>.<hmac>``.

The HMAC is the part that makes this safe to hand to the browser. A plain user
id in storage could be edited to impersonate another account and read their
saved groups; a forged id fails signature verification here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

SESSION_COOKIE_NAME = "dss_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def session_secret() -> str:
    """Key used to sign session tokens.

    Falls back to the OAuth client secret because it is already configured and,
    crucially, stable across restarts — a per-process random key would sign
    everyone out on every deploy.
    """
    explicit = os.environ.get("DSS_SESSION_SECRET", "").strip()
    if explicit:
        return explicit
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def _signature(payload: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_session(user_id: int, *, max_age: int = SESSION_MAX_AGE_SECONDS) -> str:
    """Mint a signed token for ``user_id``, or "" when signing is unavailable."""
    secret = session_secret()
    if not secret or int(user_id) <= 0:
        return ""
    payload = f"{int(user_id)}.{int(time.time()) + int(max_age)}"
    return f"{payload}.{_signature(payload, secret)}"


def read_session(token: str) -> int:
    """Return the user id carried by a valid, unexpired token, else 0."""
    secret = session_secret()
    if not secret or not token:
        return 0
    parts = token.split(".")
    if len(parts) != 3:
        return 0
    user_part, expiry_part, signature = parts
    if not hmac.compare_digest(signature, _signature(f"{user_part}.{expiry_part}", secret)):
        return 0
    try:
        if int(expiry_part) <= time.time():
            return 0
        return int(user_part)
    except ValueError:
        return 0
