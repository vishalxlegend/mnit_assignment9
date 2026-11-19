"""Add users and private carts; adopt tables created by the earlier SQL setup."""
from alembic import op
import sqlalchemy as sa

revision = "0002_users_and_carts"
down_revision = "0001_products"
branch_labels = None
depends_on = None


def existing_table(name, columns):
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(name):
        return False
    if not set(columns).issubset({c["name"] for c in inspector.get_columns(name)}):
        raise RuntimeError(f"Existing {name} table has an incompatible schema; migration stopped.")
    return True


def upgrade():
    if not existing_table("users", ["id", "name", "username", "password_hash", "created_at"]):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.Text, nullable=False),
            sa.Column("username", sa.Text(collation="NOCASE"), nullable=False, unique=True),
            sa.Column("password_hash", sa.Text, nullable=False),
            sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("length(name) BETWEEN 1 AND 100", name="ck_users_name_length"),
        )
    if not existing_table("carts", ["id", "user_id"]):
        op.create_table(
            "carts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, unique=True),
        )
    if not existing_table("cart_items", ["cart_id", "product_id", "quantity"]):
        op.create_table(
            "cart_items",
            sa.Column("cart_id", sa.Integer, sa.ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("quantity", sa.Integer, nullable=False),
            sa.CheckConstraint("quantity BETWEEN 1 AND 99", name="ck_cart_items_quantity"),
        )


def downgrade():
    raise RuntimeError("Downgrade would remove users and carts; restore a database backup instead.")
