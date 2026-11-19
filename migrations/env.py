"""Use the same SQLite database as Flask, with transactional schema upgrades."""
import os
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent.parent
config = context.config
path = config.attributes.get("database_path") or os.environ.get("DATABASE_PATH") or ROOT / "products.db"

if context.is_offline_mode():
    raise RuntimeError("These migrations inspect existing tables; use online upgrade head, without --sql.")

engine = create_engine(URL.create("sqlite", database=str(Path(path).resolve())), poolclass=NullPool)
try:
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        connection.commit()
        # Explicit BEGIN makes SQLite DDL and the revision marker atomic, including
        # on Python versions whose sqlite3 driver uses legacy transaction control.
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            context.configure(connection=connection, target_metadata=None, transactional_ddl=True)
            with context.begin_transaction():
                context.run_migrations()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
finally:
    engine.dispose()
