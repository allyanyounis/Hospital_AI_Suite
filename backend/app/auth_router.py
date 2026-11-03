"""Sign-in, sign-out and the current user."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from .audit import audit
from .config import get_settings
from .security import COOKIE_NAME, User, authenticate, current_user, is_locked_out, issue_token, user_from_cookies

router = APIRouter(prefix="/api", tags=["session"])
settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest, response: Response):
    username = req.username.strip()
    if is_locked_out(username):
        audit(username, "login.locked_out")
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = authenticate(username, req.password)
    if user is None:
        audit(username, "login.failed")
        raise HTTPException(401, "Wrong username or password")
    response.set_cookie(
        COOKIE_NAME,
        issue_token(user.username),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )
    audit(user.username, "login")
    return user.as_dict()


@router.post("/logout")
def logout(response: Response, user: User = Depends(current_user)):
    response.delete_cookie(COOKIE_NAME)
    audit(user.username, "logout")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user.as_dict()


@router.get("/session")
def session(request: Request):
    """The signed-in user, or null. Unlike /me this never returns 401, so the UI can check quietly on page load."""
    user = user_from_cookies(request.cookies)
    return {"user": user.as_dict() if user else None}
