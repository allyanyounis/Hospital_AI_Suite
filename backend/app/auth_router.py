"""Sign-in, sign-out, the current user, and the public app configuration."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from .audit import audit
from .config import get_settings
from .scribe.notes import NoteGenerationError, get_note_generator
from .scribe.notes.ollama import OllamaNoteGenerator
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


@router.get("/config")
async def config():
    """Public, non-secret settings the UI needs before sign-in (banner, which AI services are configured)."""
    try:
        generator = get_note_generator(settings)
        if isinstance(generator, OllamaNoteGenerator):
            note_model, notes_ready = f"{generator.model} (local)", await generator.is_ready()
        else:
            note_model, notes_ready = generator.model, True
    except NoteGenerationError:
        note_model, notes_ready = settings.note_model, False
    return {
        "environment_banner": settings.environment_banner,
        "retention_days": settings.retention_days,
        "clinic_timezone": settings.clinic_timezone,
        "transcriber": settings.transcriber,
        "transcriber_ready": bool(settings.deepgram_api_key),
        "note_model": note_model,
        "notes_ready": notes_ready,
    }
