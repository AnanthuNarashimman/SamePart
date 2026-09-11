"""Who is at the keyboard, proven rather than declared.

One account per seat: the four CPSE stewards and the national approver. Logging in *is*
choosing the seat, and every request afterwards carries a token the server signed, so the
role a decision is ruled on comes from the login and never from the request body. This is the
smallest thing that stops a public URL from accepting writes from whoever finds it.

Credentials come from the environment (`SAMEPART_USERS="bpcl:secret,national:secret"`), never
from source. Development defaults exist so a fresh checkout runs, and their use is announced at
start-up, because a deployment that forgot to set them should not be quiet about it.

Tokens are HMAC-signed, not encrypted: they carry the username and an expiry in the clear and
a signature nobody without `SAMEPART_SECRET` can produce. That secret must be set on a host, or
every restart signs with a fresh random key and logs everyone out.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

DEFAULT_USERS = {
    "bpcl": "meridian-bpcl", "cpcl": "meridian-cpcl", "iocl": "meridian-iocl",
    "ntpc": "meridian-ntpc", "national": "meridian-national",
}
TOKEN_TTL_SECONDS = 12 * 60 * 60


@dataclass(frozen=True)
class Principal:
    username: str
    role: str                 # steward | national_approver
    org: str | None           # the steward's CPSE; None for the national approver

    @property
    def actor_name(self) -> str:
        return f"{self.org}-steward" if self.role == "steward" else "national-approver"

    @property
    def label(self) -> str:
        return (f"CPSE Data Steward · {self.org}" if self.role == "steward"
                else "National Codification Approver")


def _users() -> dict[str, str]:
    raw = os.getenv("SAMEPART_USERS", "").strip()
    if not raw:
        return dict(DEFAULT_USERS)
    users: dict[str, str] = {}
    for entry in raw.split(","):
        if ":" not in entry:
            continue
        name, _, password = entry.strip().partition(":")
        if name and password:
            users[name.lower()] = password
    return users or dict(DEFAULT_USERS)


def using_default_credentials() -> bool:
    return not os.getenv("SAMEPART_USERS", "").strip()


_RANDOM_SECRET = secrets.token_hex(32)


def _secret() -> bytes:
    return (os.getenv("SAMEPART_SECRET") or _RANDOM_SECRET).encode()


def principal_for(username: str) -> Principal:
    if username == "national":
        return Principal(username, "national_approver", None)
    return Principal(username, "steward", username.upper())


def login(username: str, password: str) -> str | None:
    """A signed token for a correct password, None otherwise. Constant-time compare."""
    users = _users()
    expected = users.get(username.lower())
    if expected is None or not hmac.compare_digest(expected.encode(), password.encode()):
        return None
    return issue(username.lower())


def issue(username: str, ttl: int = TOKEN_TTL_SECONDS) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"u": username, "exp": int(time.time()) + ttl}).encode()).decode().rstrip("=")
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify(token: str) -> Principal | None:
    """The principal a token names, or None if it was forged, altered or has expired."""
    try:
        payload, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    if data.get("exp", 0) < time.time():
        return None
    username = data.get("u")
    if username not in _users():
        return None
    return principal_for(username)


def announce() -> None:
    if using_default_credentials():
        log.warning("SAMEPART_USERS is not set; using development credentials. "
                    "Set it before exposing this service.")
    if not os.getenv("SAMEPART_SECRET"):
        log.warning("SAMEPART_SECRET is not set; tokens will not survive a restart.")
