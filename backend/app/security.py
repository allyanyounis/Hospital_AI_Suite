"""Staff sign-in: scrypt password hashes, signed expiring session cookies, lockout, and role checks.

Built so a hospital identity provider (SSO via OIDC / SAML) can replace the password check later:
everything downstream depends only on `current_user`.
"""

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, WebSocket

from .config import get_settings
from .database import SessionLocal
from .models import User as UserRow

COOKIE_NAME = "hospital_ai_session"
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 10

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_failed_logins: dict[str, list[float]] = {}


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def as_dict(self) -> dict:
        return {"username": self.username, "display_name": self.display_name, "role": self.role}


# --- Passwords ---------------------------------------------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(candidate.hex(), digest)


# --- Session tokens ----------------------------------------------------------------------------------------------


def _sign(payload: str) -> str:
    key = get_settings().session_secret.encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def issue_token(username: str) -> str:
    expires = int(time.time()) + get_settings().session_hours * 3600
    payload = base64.urlsafe_b64encode(f"{username}|{expires}".encode()).decode()
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> str | None:
    payload, _, signature = token.partition(".")
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        username, expires = base64.urlsafe_b64decode(payload).decode().rsplit("|", 1)
    except ValueError:
        return None
    return username if int(expires) > time.time() else None


# --- Authentication ----------------------------------------------------------------------------------------------


def is_locked_out(username: str) -> bool:
    recent = [t for t in _failed_logins.get(username, []) if time.time() - t < LOCKOUT_SECONDS]
    _failed_logins[username] = recent
    return len(recent) >= MAX_FAILED_LOGINS


def _load_active(username: str) -> User | None:
    with SessionLocal() as db:
        row = db.get(UserRow, username)
    if row is None or not row.active:
        return None
    return User(row.username, row.display_name, row.role)


def authenticate(username: str, password: str) -> User | None:
    with SessionLocal() as db:
        row = db.get(UserRow, username)
    if row and row.active and verify_password(password, row.password_hash):
        _failed_logins.pop(username, None)
        return User(row.username, row.display_name, row.role)
    _failed_logins.setdefault(username, []).append(time.time())
    return None


def user_from_cookies(cookies: dict[str, str]) -> User | None:
    """Resolve the signed-in user from cookies; shared by HTTP routes and WebSockets."""
    username = read_token(cookies.get(COOKIE_NAME, ""))
    return _load_active(username) if username else None


def websocket_user(ws: WebSocket) -> User | None:
    """The signed-in user for a WebSocket, or None. Browsers don't apply CORS to WebSockets, so the Origin is
    checked here too (blocks cross-site socket hijacking)."""
    origin = ws.headers.get("origin")
    allowed = bool(origin) and (origin in get_settings().cors_origins or urlparse(origin).hostname == ws.url.hostname)
    return user_from_cookies(ws.cookies) if allowed else None


def current_user(request: Request) -> User:
    user = user_from_cookies(request.cookies)
    if user is None:
        raise HTTPException(401, "Please sign in")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admins only")
    return user
