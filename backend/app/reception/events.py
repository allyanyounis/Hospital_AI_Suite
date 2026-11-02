"""Live dashboard updates: a tiny pub/sub over WebSocket so open pages refresh when a call books or cancels."""

import logging

from fastapi import WebSocket

log = logging.getLogger("hospital_ai.events")


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def publish(self, event: str) -> None:
        """Send an event name (e.g. "appointment_booked") to every open dashboard; drop dead connections."""
        for ws in list(self._clients):
            try:
                await ws.send_json({"type": event})
            except Exception:  # client went away mid-send
                self.disconnect(ws)


broadcaster = Broadcaster()
