import logging

from ..config import get_settings
from ..module import Module
from . import router, vapi

log = logging.getLogger("hospital_ai")


def _warn_if_webhooks_open() -> None:
    if not get_settings().vapi_secret:
        log.warning("VAPI_SECRET is not set; the public VAPI webhooks accept requests from anyone")


module = Module(
    name="reception",
    routers=[router.router, vapi.router],  # public webhooks last: vapi owns "POST /"
    on_startup=[_warn_if_webhooks_open],
)
