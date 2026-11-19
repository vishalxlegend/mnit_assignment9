"""Alembic entry point shared by application startup and migration tests."""
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent


def migration_config(database):
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_path"] = str(Path(database).resolve())
    return config


def upgrade_database(database):
    command.upgrade(migration_config(database), "head")
