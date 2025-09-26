"""add invoice soft delete column

Revision ID: 20250924_0002
Revises: 20250924_0001
Create Date: 2025-09-24 00:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250924_0002'
down_revision: Union[str, None] = '20250924_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_deleted column with default false (soft delete flag for invoices)
    op.add_column('invoices', sa.Column('is_deleted', sa.Boolean(),
                  nullable=False, server_default=sa.text('false')))
    # Optional: if existing rows should be explicitly set false (server_default handles new rows)
    # No backfill data manipulation needed as default applied.


def downgrade() -> None:
    op.drop_column('invoices', 'is_deleted')
