"""App-wide endpoints that need no sign-in: health check and the public configuration."""

from fastapi import APIRouter

from .config import get_settings
from .modules import MODULES

router = APIRouter(prefix="/api", tags=["session"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config")
async def config():
    """Public, non-secret settings the UI needs before sign-in (banner, which AI services are configured)."""
    settings = get_settings()
    result = {"environment_banner": settings.environment_banner, "clinic_timezone": settings.clinic_timezone}
    for module in MODULES:
        if module.public_config:
            result.update(await module.public_config())
    return result
