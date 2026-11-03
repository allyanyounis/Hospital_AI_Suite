"""PostgreSQL connection: SQLAlchemy engine, sessions, the declarative base and schema migrations."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class Base(DeclarativeBase):
    # Predictable constraint names, so migrations can refer to them
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def one_of(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint limiting a column to a fixed set of values (NULL passes)."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def now_column(**kw) -> Mapped[datetime]:
    """A timestamptz column defaulting to the database's now()."""
    return mapped_column(DateTime(timezone=True), server_default=func.now(), **kw)


def _normalise_url(url: str) -> str:
    """Accept plain postgres:// URLs (Heroku/Neon/Supabase style) and route them to the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


engine = create_engine(_normalise_url(get_settings().database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed by the route when it writes."""
    with SessionLocal() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session that commits on success; for background tasks, the CLI and the audit log."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def alembic_config():
    """Alembic settings: backend/alembic.ini, with the migrations folder resolved from this package."""
    from alembic.config import Config

    config = Config(str(MIGRATIONS_DIR.parent / "alembic.ini"))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def init_db() -> None:
    """Bring the schema up to the latest migration. Safe to run on every start."""
    from alembic import command

    command.upgrade(alembic_config(), "head")
