"""Add day_invoice_sequences table for deterministic daily invoice numbering

Revision ID: 20250926_0006_day_seq_table
Revises: 20250925_0005
Create Date: 2025-09-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250926_0006_day_seq_table'
down_revision = '20250925_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'day_invoice_sequences',
        sa.Column('date_key', sa.String(length=8),
                  primary_key=True, nullable=False),
        sa.Column('last_seq', sa.Integer(), nullable=False,
                  server_default=sa.text('0')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('length(date_key) = 8', name='ck_day_seq_date_len'),
        sa.CheckConstraint('last_seq >= 0', name='ck_day_seq_non_negative'),
    )


def downgrade() -> None:
    op.drop_table('day_invoice_sequences')
