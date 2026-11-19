"""Adopt the Part 1 products table, or initialize a fresh catalog."""
from pathlib import Path
import sqlite3

from alembic import op
import sqlalchemy as sa

revision = "0001_products"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("products"):
        required = {"id", "name", "description", "price_paise", "image_url", "stock"}
        if not required.issubset({c["name"] for c in inspector.get_columns("products")}):
            raise RuntimeError("The existing products table does not match the Part 1 schema.")
        return  # Never reseed or alter existing product records.
    # Frozen seed snapshot: later edits to schema.sql cannot change this revision.
    source = Path(__file__).resolve().parents[1] / "data/part1_products.sql"
    statement = ""
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.get_bind().exec_driver_sql(statement)
            statement = ""


def downgrade():
    raise RuntimeError("Downgrade would remove product data; restore a database backup instead.")
