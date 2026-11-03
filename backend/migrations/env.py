"""Alembic environment: migrates the app's own engine, comparing against the models in app/models.py."""

from alembic import context

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.core.database import Base, engine

config = context.config


def run_migrations() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported; run against a database")
run_migrations()
