"""Keyset pagination for long, newest-first lists (lab results, vitals, reports, waiting lists).

A page is `{"items": [...], "next_cursor": "..." | null}`. The cursor is an opaque token holding the sort key and id
of the last row sent, so the next page starts strictly after it and never skips or repeats rows while new ones arrive.
"""

import base64
from datetime import date, datetime

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, or_

MAX_LIMIT = 200


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


def encode_cursor(key: datetime | date, row_id: int) -> str:
    return base64.urlsafe_b64encode(f"{key.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str, kind: type[datetime] | type[date] = datetime) -> tuple[datetime | date, int]:
    try:
        key, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().rsplit("|", 1)
        return kind.fromisoformat(key), int(row_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(422, "Invalid cursor") from exc


def after_cursor(key_column, id_column, cursor: str | None, kind=datetime) -> ColumnElement[bool] | None:
    """The WHERE clause for rows after `cursor` in (key DESC, id DESC) order, or None on the first page."""
    if not cursor:
        return None
    key, row_id = decode_cursor(cursor, kind)
    return or_(key_column < key, and_(key_column == key, id_column < row_id))


def clamp(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def page_of(rows: list, limit: int, key, out) -> dict:
    """Build a page from up to `limit + 1` rows: the extra row only tells whether another page exists."""
    items = rows[:limit]
    more = len(rows) > limit
    return {
        "items": [out(r) for r in items],
        "next_cursor": encode_cursor(key(items[-1]), items[-1].id) if more and items else None,
    }
