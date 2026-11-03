"""Hospital AI Suite API: the hospital management system's backend, one FastAPI app for every module.

Run:  uvicorn app.main:app --reload --port 8000     (from backend/; settings come from backend/.env)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import DEV_SESSION_SECRET, get_settings
from app.core.database import init_db
from app.core.modules import load_modules
from app.modules.scribe.repository import purge_expired_content, recover_interrupted_drafts

log = logging.getLogger("hospital_ai")

# The hospital's modules, mounted in this order. Add a new module (its package has a module.py) here.
# The voice receptionist goes last: its public webhooks own "POST /".
INSTALLED_MODULES = [
    "system",
    "auth",
    "organization",
    "staff",
    "patients",
    "scheduling",
    "appointments",
    "scribe",
    "clinical",
    "theatre",
    "portal",
    "reception",
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    init_db()
    recover_interrupted_drafts()
    purge_expired_content(settings.retention_days)
    if settings.session_secret == DEV_SESSION_SECRET:
        log.warning("SESSION_SECRET is the development default; set a random value before any pilot use")
    if not settings.vapi_secret:
        log.warning("VAPI_SECRET is not set; the public VAPI webhooks accept requests from anyone")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.hospital_name} API", version="2.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    for module in load_modules(INSTALLED_MODULES):
        for router in module.routers:
            app.include_router(router)
    return app


app = create_app()
