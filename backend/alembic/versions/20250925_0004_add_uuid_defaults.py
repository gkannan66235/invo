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

# Simplified strategy: use gen_random_uuid() from pgcrypto for all UUID defaults.
# We create pgcrypto extension if it isn't already present (harmless if it is).
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
    conn = op.get_bind()
    try:  # noqa: BLE001
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS pgcrypto;')
    except Exception:  # noqa: BLE001
        pass
    for table in TARGET_TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid();")


def downgrade() -> None:
    for table in TARGET_TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT;")
