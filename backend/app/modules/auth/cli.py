"""Manage accounts from the command line (there is no open sign-up page; admins can also use /admin/users).

    python -m app users add drrahman --name "Dr. Rahman" [--role admin|doctor]
    python -m app users add ali --name "Ali Khan" --role patient [--mrn MRN-001] [--dob 1980-01-31] [--sex Male]
    python -m app users reset-password drrahman
    python -m app users disable drrahman | enable drrahman
    python -m app users list

The password is prompted for; when stdin is not a terminal (scripts, CI) it is read from the first line of stdin.
"""

import argparse
import getpass
import sys
from datetime import date

from app.core.database import init_db, session_scope

from . import service
from .permissions import ROLES
from .security import MIN_PASSWORD_LENGTH


def _read_password() -> str:
    if sys.stdin.isatty():
        password = getpass.getpass(f"Password (min {MIN_PASSWORD_LENGTH} characters): ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("Passwords did not match")
    else:
        password = sys.stdin.readline().rstrip("\r\n")
    return password


def save_user(
    username: str, display_name: str, role: str, password: str, *, mrn: str = "", dob: date | None = None, sex: str = ""
) -> None:
    """Create an account, or update an existing one (name, staff role, password) and re-enable it."""
    with session_scope() as db:
        account = db.get(service.Account, username)
        if account is None:
            service.create_account(db, None, username, display_name, role, password, mrn=mrn, dob=dob, sex=sex)
            return
        service.update_account(db, None, account, display_name=display_name, role=role, active=True)
        service.reset_password(db, None, account, password)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app users")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="Create or update an account")
    add.add_argument("username")
    add.add_argument("--name", required=True, help='Display name, e.g. "Dr. Rahman" (a patient\'s full name)')
    add.add_argument("--role", choices=ROLES, default="doctor")
    add.add_argument("--mrn", default="", help="patient accounts: link to the patient with this MRN")
    add.add_argument("--dob", type=date.fromisoformat, help="patient accounts: date of birth, YYYY-MM-DD")
    add.add_argument("--sex", default="", choices=["", "Female", "Male", "Other", "Not stated"])
    for command in ("reset-password", "disable", "enable"):
        sub.add_parser(command).add_argument("username")
    sub.add_parser("list")
    args = parser.parse_args(argv)

    init_db()
    try:
        if args.command == "add":
            save_user(args.username, args.name, args.role, _read_password(), mrn=args.mrn, dob=args.dob, sex=args.sex)
            print(f"Saved {args.username} ({args.role})")
            return
        with session_scope() as db:
            if args.command == "list":
                for a in service.list_accounts(db):
                    linked = f"patient #{a.patient_id}" if a.patient_id else ""
                    status = "active" if a.active else "disabled"
                    print(f"{a.username:<20} {a.display_name:<25} {a.role:<8} {status:<9} {linked}")
                return
            account = service.get_account(db, args.username)
            if args.command == "reset-password":
                service.reset_password(db, None, account, _read_password())
            else:
                service.update_account(db, None, account, active=args.command == "enable")
    except service.AccountError as e:
        sys.exit(e.detail)
    print(f"{args.command} done for {args.username}")


if __name__ == "__main__":
    main()
