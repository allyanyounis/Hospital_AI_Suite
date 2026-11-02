"""Hospital AI Suite API: one FastAPI app serving the AI medical scribe and the AI voice receptionist.

Run:  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth_router
from .config import DEV_SESSION_SECRET, get_settings
from .database import init_db
from .reception import router as reception_router
from .reception import vapi
from .schedule import router as schedule_router
from .scribe import live_router
from .scribe import router as scribe_router
from .scribe.repository import purge_expired_content, recover_interrupted_drafts

settings = get_settings()
log = logging.getLogger("hospital_ai")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    recover_interrupted_drafts()
    purge_expired_content(settings.retention_days)
    if settings.session_secret == DEV_SESSION_SECRET:
        log.warning("SESSION_SECRET is the development default; set a random value before any pilot use")
    if not settings.vapi_secret:
        log.warning("VAPI_SECRET is not set; the public VAPI webhooks accept requests from anyone")
    yield


app = FastAPI(title="Hospital AI Suite", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/api/health", tags=["session"])
def health():
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(schedule_router.router)
app.include_router(scribe_router.router)
app.include_router(live_router.router)
app.include_router(reception_router.router)
app.include_router(vapi.router)  # public webhooks last: it owns "POST /"
