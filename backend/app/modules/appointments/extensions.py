"""Extension point: other modules add their own facts to appointment listings without this module importing them.

The voice receptionist registers the call transcript this way; billing could add an invoice status, the lab a
pending-orders flag. A provider gets the appointment ids being listed and returns {appointment_id: {field: value}}.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

DetailProvider = Callable[[Session, list[int]], dict[int, dict[str, Any]]]
_providers: list[DetailProvider] = []


def register_detail_provider(provider: DetailProvider) -> None:
    if provider not in _providers:
        _providers.append(provider)


def details_for(db: Session, appointment_ids: list[int]) -> dict[int, dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {i: {} for i in appointment_ids}
    for provider in _providers:
        for appointment_id, fields in provider(db, appointment_ids).items():
            merged.setdefault(appointment_id, {}).update(fields)
    return merged
