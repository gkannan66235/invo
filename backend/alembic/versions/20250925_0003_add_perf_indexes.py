"""add performance indexes for invoices

Revision ID: 20250925_0003
Revises: 20250924_0002
Create Date: 2025-09-25 00:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250925_0003'
down_revision: Union[str, None] = '20250924_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite / partial indexes to speed common queries:
    # 1. Listing invoices: filter is_deleted = false and order by created_at DESC with limit.
    #    Partial index on created_at where is_deleted=false supports this.
    # 2. Generating invoice numbers: query counts invoices for current day using invoice_date >= start_of_day.
    #    Simple index on invoice_date helps range scans.
    # NOTE: Partial indexes are PostgreSQL specific; safe no-op if applied only to Postgres.
    op.create_index(
        'idx_invoice_created_active', 'invoices', ['created_at'],
        postgresql_where=sa.text('is_deleted = false')
    )
    op.create_index(
        'idx_invoice_date_only', 'invoices', ['invoice_date']
    )


def downgrade() -> None:
    op.drop_index('idx_invoice_date_only', table_name='invoices')
    op.drop_index('idx_invoice_created_active', table_name='invoices')
