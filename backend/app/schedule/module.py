from ..module import Module
from . import router

module = Module(name="schedule", routers=[router.router])
