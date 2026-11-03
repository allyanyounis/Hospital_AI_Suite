"""Sign-in for staff and patients: scrypt password hashes, signed expiring session cookies tied to a per-user
session version, lockout, and permission checks (see permissions.py).

Built so a hospital identity provider (SSO via OIDC / SAML) can replace the password check later:
everything downstream depends only on `current_user` / `require(...)`.
"""

import base64
import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, WebSocket

from app.core.config import get_settings
from app.core.database import SessionLocal

from .models import User as UserRow
from .permissions import Permission, permissions_for

COOKIE_NAME = "hospital_ai_session"
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 10

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_failed_logins: dict[str, list[float]] = {}


@dataclass(frozen=True)
class User:
    """The signed-in user, as every route sees it."""

    username: str
    display_name: str
    role: str
    patient_id: int | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    def as_dict(self) -> dict:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "permissions": sorted(self.permissions),
            "patient_id": self.patient_id,
        }

    @classmethod
    def from_row(cls, row: UserRow) -> "User":
        return cls(row.username, row.display_name, row.role, row.patient_id, permissions_for(row.role))


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


def issue_token(username: str, session_version: int) -> str:
    """Signed "username|session_version|expiry". A token stops working when it expires or the version moves on."""
    expires = int(time.time()) + get_settings().session_hours * 3600
    payload = base64.urlsafe_b64encode(f"{username}|{session_version}|{expires}".encode()).decode()
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> tuple[str, int] | None:
    payload, _, signature = token.partition(".")
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        username, version, expires = base64.urlsafe_b64decode(payload).decode().rsplit("|", 2)
        if int(expires) <= time.time():
            return None
        return username, int(version)
    except ValueError:
        return None


# --- Authentication ----------------------------------------------------------------------------------------------


def is_locked_out(username: str) -> bool:
    recent = [t for t in _failed_logins.get(username, []) if time.time() - t < LOCKOUT_SECONDS]
    _failed_logins[username] = recent
    return len(recent) >= MAX_FAILED_LOGINS


def authenticate(username: str, password: str) -> tuple[User, int] | None:
    """The user and their current session version, if the password is right and the account is active."""
    with SessionLocal() as db:
        row = db.get(UserRow, username)
    if row and row.active and verify_password(password, row.password_hash):
        _failed_logins.pop(username, None)
        return User.from_row(row), row.session_version
    _failed_logins.setdefault(username, []).append(time.time())
    return None


def user_from_cookies(cookies: dict[str, str]) -> User | None:
    """Resolve the signed-in user from cookies; shared by HTTP routes and WebSockets. Role, permissions and the
    active flag are read fresh on every request, so changes apply immediately."""
    token = read_token(cookies.get(COOKIE_NAME, ""))
    if token is None:
        return None
    username, version = token
    with SessionLocal() as db:
        row = db.get(UserRow, username)
    if row is None or not row.active or row.session_version != version:
        return None
    return User.from_row(row)


def current_user(request: Request) -> User:
    """Any signed-in user (staff or patient)."""
    user = user_from_cookies(request.cookies)
    if user is None:
        raise HTTPException(401, "Please sign in")
    return user


def require(permission: Permission) -> Callable[..., User]:
    """Route dependency: the signed-in user, who must hold `permission` (401 if signed out, 403 if not allowed)."""

    def dependency(user: User = Depends(current_user)) -> User:
        if not user.can(permission):
            raise HTTPException(403, "You don't have access to this")
        return user

    dependency.__name__ = f"require_{permission.replace('.', '_')}"
    return dependency


def websocket_user(ws: WebSocket, permission: Permission) -> User | None:
    """The signed-in user for a WebSocket if they hold `permission`, else None. Browsers don't apply CORS to
    WebSockets, so the Origin is checked here too (blocks cross-site socket hijacking)."""
    origin = ws.headers.get("origin")
    allowed = bool(origin) and (origin in get_settings().cors_origins or urlparse(origin).hostname == ws.url.hostname)
    user = user_from_cookies(ws.cookies) if allowed else None
    return user if user is not None and user.can(permission) else None
