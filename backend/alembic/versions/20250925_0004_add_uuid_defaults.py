"""add uuid defaults

Revision ID: 20250925_0004
Revises: 20250925_0003
Create Date: 2025-09-25 05:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250925_0004"
down_revision: Union[str, None] = "20250925_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: We rely on the uuid-ossp extension (enabled in init.sql) providing uuid_generate_v4().
# We choose uuid_generate_v4() instead of gen_random_uuid() to avoid requiring pgcrypto.
TARGET_TABLES = [
    "roles",
    "users",
    "customers",
    "suppliers",
    "inventory_items",
    "orders",
    "invoices",
]


def upgrade() -> None:
    for table in TARGET_TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT uuid_generate_v4();")


def downgrade() -> None:
    for table in TARGET_TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT;")
