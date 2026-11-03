"""Auth module: staff accounts, password sign-in, session cookies, roles, and the account CLI.

Other modules protect routes with `require("<permission>")` (or `current_user` for any signed-in user) and
`websocket_user(ws, "<permission>")`, and receive a `User`. Roles and their permissions: permissions.py.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User as Account
from .permissions import ROLES, STAFF_ROLES, Permission, Role
from .security import User, current_user, require, websocket_user
from .service import create_account


def display_names(db: Session) -> dict[str, str]:
    """username -> display name, for reports."""
    return dict(db.execute(select(Account.username, Account.display_name)).all())


__all__ = [
    "ROLES",
    "STAFF_ROLES",
    "Account",
    "Permission",
    "Role",
    "User",
    "create_account",
    "current_user",
    "display_names",
    "require",
    "websocket_user",
]
