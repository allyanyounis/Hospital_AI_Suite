"""The feature modules that make up the suite. Adding a module = a new package with a module.py + one line here.

Order matters: routers are included in this order, and the receptionist stays last because its public VAPI
webhooks own "POST /".
"""

from .module import Module
from .reception.module import module as reception
from .schedule.module import module as schedule
from .scribe.module import module as scribe

MODULES: tuple[Module, ...] = (schedule, scribe, reception)
