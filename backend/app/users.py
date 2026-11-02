"""Manage staff accounts from the command line (there is no open sign-up page).

    python -m app.users add drrahman --name "Dr. Rahman" [--role admin]
    python -m app.users reset-password drrahman
    python -m app.users disable drrahman | enable drrahman
    python -m app.users list

The password is prompted for; when stdin is not a terminal (scripts, CI) it is read from the first line of stdin.
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from .audit import audit
from .database import init_db, session_scope
from .models import User
from .security import MIN_PASSWORD_LENGTH, hash_password


def _read_password() -> str:
    if sys.stdin.isatty():
        password = getpass.getpass(f"Password (min {MIN_PASSWORD_LENGTH} characters): ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("Passwords did not match")
    else:
        password = sys.stdin.readline().rstrip("\r\n")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return password


def save_user(username: str, display_name: str, role: str, password: str) -> None:
    """Create or update an account (re-enables it)."""
    with session_scope() as db:
        user = db.get(User, username) or User(username=username)
        user.display_name, user.role, user.active = display_name, role, True
        user.password_hash = hash_password(password)
        db.add(user)
        audit(None, "user.saved", db=db, user=username, role=role)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.users")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="Create or update an account")
    add.add_argument("username")
    add.add_argument("--name", required=True, help='Display name, e.g. "Dr. Rahman"')
    add.add_argument("--role", choices=["clinician", "admin"], default="clinician")
    for command in ("reset-password", "disable", "enable"):
        sub.add_parser(command).add_argument("username")
    sub.add_parser("list")
    args = parser.parse_args()

    init_db()
    if args.command == "add":
        save_user(args.username, args.name, args.role, _read_password())
        print(f"Saved {args.username} ({args.role})")
        return

    with session_scope() as db:
        if args.command == "list":
            for u in db.scalars(select(User).order_by(User.username)):
                print(f"{u.username:<20} {u.display_name:<25} {u.role:<10} {'active' if u.active else 'disabled'}")
            return
        user = db.get(User, args.username) or sys.exit(f"No user '{args.username}'")
        if args.command == "reset-password":
            user.password_hash = hash_password(_read_password())
            audit(None, "user.password_reset", db=db, user=user.username)
        else:
            user.active = args.command == "enable"
            audit(None, f"user.{args.command}d", db=db, user=user.username)
    print(f"{args.command} done for {args.username}")


if __name__ == "__main__":
    main()
