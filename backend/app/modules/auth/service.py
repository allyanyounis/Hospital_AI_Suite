"""Account management shared by the admin API and the command line. Every change is audited."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.patients import resolve_patient

from .models import User as Account
from .permissions import ROLES
from .security import MIN_PASSWORD_LENGTH, hash_password, verify_password


class AccountError(HTTPException):
    """A rule violation the caller can fix; carries an HTTP status for the API."""


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(422, f"Password must be at least {MIN_PASSWORD_LENGTH} characters")


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise AccountError(422, f"Role must be one of {', '.join(ROLES)}")


def list_accounts(db: Session) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.role, Account.username)))


def get_account(db: Session, username: str) -> Account:
    account = db.get(Account, username)
    if account is None:
        raise AccountError(404, "No such account")
    return account


def create_account(
    db: Session,
    actor: str | None,
    username: str,
    display_name: str,
    role: str,
    password: str,
    *,
    mrn: str = "",
    dob: date | None = None,
    sex: str = "",
) -> Account:
    """A new account. Patient accounts are linked to the patient record with that MRN (or a new one)."""
    _check_role(role)
    _check_password(password)
    if db.get(Account, username) is not None:
        raise AccountError(409, "That username is taken")
    account = Account(username=username, display_name=display_name, role=role, password_hash=hash_password(password))
    if role == "patient":
        patient = resolve_patient(db, None, display_name, mrn, sex, dob)
        patient.registered = True  # a patient with an account is a permanent hospital record
        db.flush()
        if db.scalar(select(Account.username).where(Account.patient_id == patient.id)):
            raise AccountError(409, "That patient already has an account")
        account.patient = patient
    db.add(account)
    db.flush()
    audit(actor, "user.created", db=db, user=username, role=role)
    return account


def update_account(
    db: Session,
    actor: str | None,
    account: Account,
    *,
    display_name: str | None = None,
    role: str | None = None,
    active: bool | None = None,
) -> Account:
    """Rename, change role (staff roles only), enable or disable. Role changes and disabling end all sessions."""
    if role is not None and role != account.role:
        _check_role(role)
        if "patient" in (role, account.role):
            raise AccountError(422, "Patient accounts can't change to a staff role or back; create a new account")
        if account.username == actor:
            raise AccountError(422, "You can't change your own role")
        account.role = role
        account.session_version += 1
    if active is not None and active != account.active:
        if account.username == actor and not active:
            raise AccountError(422, "You can't disable your own account")
        account.active = active
        account.session_version += 1
    if display_name is not None:
        account.display_name = display_name
    audit(actor, "user.updated", db=db, user=account.username, role=account.role, active=account.active)
    return account


def reset_password(db: Session, actor: str | None, account: Account, password: str) -> None:
    """Set a new password (admin or CLI) and sign the user out everywhere."""
    _check_password(password)
    account.password_hash = hash_password(password)
    account.session_version += 1
    audit(actor, "user.password_reset", db=db, user=account.username)


def change_own_password(db: Session, account: Account, current: str, new: str) -> None:
    """The user's own change; other sessions end, the caller is issued a fresh cookie."""
    if not verify_password(current, account.password_hash):
        raise AccountError(400, "Current password is wrong")
    _check_password(new)
    account.password_hash = hash_password(new)
    account.session_version += 1
    audit(account.username, "user.password_changed", db=db)
