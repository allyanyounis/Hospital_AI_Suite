"""Sign-in, sign-out, the current user and their password, plus account management for admins."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import get_settings
from app.core.database import get_db

from . import service
from .schemas import AccountCreate, AccountOut, AccountUpdate, LoginRequest, PasswordChange, PasswordReset
from .security import (
    COOKIE_NAME,
    User,
    authenticate,
    current_user,
    is_locked_out,
    issue_token,
    require,
    user_from_cookies,
)

router = APIRouter(prefix="/api", tags=["session"])
settings = get_settings()
manage_users = require("users.manage")


def _set_session_cookie(response: Response, username: str, session_version: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        issue_token(username, session_version),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )


# --- Session -----------------------------------------------------------------------------------------------------


@router.post("/login")
def login(req: LoginRequest, response: Response):
    username = req.username.strip()
    if is_locked_out(username):
        audit(username, "login.locked_out")
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    result = authenticate(username, req.password)
    if result is None:
        audit(username, "login.failed")
        raise HTTPException(401, "Wrong username or password")
    user, session_version = result
    _set_session_cookie(response, user.username, session_version)
    audit(user.username, "login", role=user.role)
    return user.as_dict()


@router.post("/logout")
def logout(response: Response, user: User = Depends(current_user)):
    response.delete_cookie(COOKIE_NAME)
    audit(user.username, "logout")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    """The signed-in user with their permissions; the UI shows only what these allow."""
    return user.as_dict()


@router.get("/session")
def session(request: Request):
    """The signed-in user (with permissions), or null. Unlike /me this never returns 401, so the UI can check
    quietly on page load."""
    user = user_from_cookies(request.cookies)
    return {"user": user.as_dict() if user else None}


@router.post("/me/password")
def change_password(
    req: PasswordChange, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    account = service.get_account(db, user.username)
    service.change_own_password(db, account, req.current_password, req.new_password)
    db.commit()
    _set_session_cookie(response, account.username, account.session_version)  # this device stays signed in
    return {"ok": True}


# --- Accounts (admin) --------------------------------------------------------------------------------------------


@router.get("/users", response_model=list[AccountOut], tags=["users"])
def list_users(db: Session = Depends(get_db), _: User = Depends(manage_users)):
    return [AccountOut.of(a) for a in service.list_accounts(db)]


@router.post("/users", response_model=AccountOut, status_code=201, tags=["users"])
def create_user(req: AccountCreate, db: Session = Depends(get_db), admin: User = Depends(manage_users)):
    if req.role == "patient" and req.patient is None:
        raise HTTPException(422, "Patient details are required for a patient account")
    patient = req.patient if req.role == "patient" else None
    account = service.create_account(
        db,
        admin.username,
        req.username,
        req.display_name.strip(),
        req.role,
        req.password,
        mrn=patient.mrn.strip() if patient else "",
        dob=patient.dob if patient else None,
        sex=patient.sex if patient else "",
    )
    db.commit()
    return AccountOut.of(account)


@router.patch("/users/{username}", response_model=AccountOut, tags=["users"])
def update_user(username: str, req: AccountUpdate, db: Session = Depends(get_db), admin: User = Depends(manage_users)):
    account = service.get_account(db, username)
    display_name = req.display_name.strip() if req.display_name else None
    service.update_account(db, admin.username, account, display_name=display_name, role=req.role, active=req.active)
    db.commit()
    return AccountOut.of(account)


@router.post("/users/{username}/password", tags=["users"])
def reset_user_password(
    username: str, req: PasswordReset, db: Session = Depends(get_db), admin: User = Depends(manage_users)
):
    service.reset_password(db, admin.username, service.get_account(db, username), req.password)
    db.commit()
    return {"ok": True}
