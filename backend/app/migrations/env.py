"""Alembic environment: migrates the app's database using the app's own engine and table definitions."""

from alembic import context

from app import modules  # noqa: F401  (registers every module's tables)
from app.database import Base, engine

target_metadata = Base.metadata


def run_migrations() -> None:
    # init_db() passes its open connection; the alembic CLI does not, so connect here
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
    else:
        with engine.begin() as conn:
            _run(conn)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
