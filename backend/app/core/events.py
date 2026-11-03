"""Live dashboard updates: a tiny pub/sub over WebSocket so open pages refresh when data changes (any module)."""

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

    async def publish(self, event: str, **data) -> None:
        """Send an event (e.g. "appointment_booked", or "theatre_updated" with day="2026-11-03") to every open
        dashboard as {"type": event, **data}; drop dead connections. Data holds ids and dates, never clinical text."""
        for ws in list(self._clients):
            try:
                await ws.send_json({"type": event, **data})
            except Exception:  # client went away mid-send
                self.disconnect(ws)


broadcaster = Broadcaster()
