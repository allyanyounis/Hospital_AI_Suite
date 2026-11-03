"""Hospital AI Suite API: one FastAPI app serving every feature module listed in app/modules.py.

Run:  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth_router, system_router
from .config import DEV_SESSION_SECRET, get_settings
from .database import init_db
from .modules import MODULES

settings = get_settings()
log = logging.getLogger("hospital_ai")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    for module in MODULES:
        for task in module.on_startup:
            task()
    if settings.session_secret == DEV_SESSION_SECRET:
        log.warning("SESSION_SECRET is the development default; set a random value before any pilot use")
    yield


app = FastAPI(title="Hospital AI Suite", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(system_router.router)
app.include_router(auth_router.router)
for module in MODULES:
    for router in module.routers:
        app.include_router(router)
