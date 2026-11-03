"""Database migrations (Alembic). The backend applies them on start; see README "Changing the database"."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

# The first migration: the schema as it was before migrations were introduced
BASELINE = "0001"


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    return config


def upgrade_to_head(engine: Engine) -> None:
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        tables = inspect(connection).get_table_names()
        if "alembic_version" not in tables and "users" in tables:
            # Database created before migrations existed: its tables already match the baseline
            command.stamp(config, BASELINE)
        command.upgrade(config, "head")
