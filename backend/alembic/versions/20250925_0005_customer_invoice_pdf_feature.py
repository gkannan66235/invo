"""customer & invoice pdf feature schema additions

Revision ID: 20250925_0005
Revises: 20250925_0004
Create Date: 2025-09-25 06:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250925_0005"
down_revision: Union[str, None] = "20250925_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add customer mobile_normalized column (nullable for existing rows) & index
    if not _column_exists("customers", "mobile_normalized"):
        op.add_column(
            "customers",
            sa.Column("mobile_normalized", sa.String(
                length=10), nullable=True),
        )
    op.create_index(
        "idx_customer_mobile",
        "customers",
        ["mobile_normalized"],
        unique=False,
    )

    # 2. Add snapshot columns to invoices if absent
    if not _column_exists("invoices", "branding_snapshot"):
        op.add_column(
            "invoices",
            sa.Column(
                "branding_snapshot",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,  # temporarily nullable; service layer will enforce
            ),
        )
    if not _column_exists("invoices", "gst_rate_snapshot"):
        op.add_column(
            "invoices",
            sa.Column("gst_rate_snapshot", sa.Numeric(5, 2), nullable=True),
        )
    if not _column_exists("invoices", "settings_snapshot"):
        op.add_column(
            "invoices",
            sa.Column(
                "settings_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
        )

    # Create index on invoices.customer_id only (even if composite exists) per spec
    op.create_index(
        "idx_invoice_customer",
        "invoices",
        ["customer_id"],
        unique=False,
    )

    # 3. Create invoice_lines table (line items snapshot separate from orders)
    op.create_table(
        "invoice_lines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2),
                  nullable=False, server_default="1.00"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"], unique=False
    )

    # 4. Create invoice_download_audit table
    op.create_table(
        "invoice_download_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=10),
                  nullable=False),  # print | pdf
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('print','pdf')", name="ck_invoice_download_action_valid"
        ),
    )
    op.create_index(
        "idx_audit_invoice", "invoice_download_audit", ["invoice_id"], unique=False
    )
    op.create_index(
        "idx_audit_user", "invoice_download_audit", ["user_id"], unique=False
    )

    # 5. (Optional) Backfill mobile_normalized from phone if column exists
    #    We keep logic simple and only copy digits if exactly 10 after stripping +91/91.
    op.execute(
        """
        UPDATE customers
        SET mobile_normalized = REGEXP_REPLACE(phone, '[^0-9]', '', 'g')
        WHERE phone IS NOT NULL
          AND mobile_normalized IS NULL
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) = 10;
        """
    )

    # 6. Leave new invoice snapshot columns nullable for existing rows; future invoices must populate.


def downgrade() -> None:
    # Drop audit indexes & table
    op.drop_index("idx_audit_user", table_name="invoice_download_audit")
    op.drop_index("idx_audit_invoice", table_name="invoice_download_audit")
    op.drop_table("invoice_download_audit")

    # Drop invoice lines indexes & table
    op.drop_index("idx_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")

    # Drop added invoice indexes
    op.drop_index("idx_invoice_customer", table_name="invoices")

    # Drop snapshot columns if they exist
    if _column_exists("invoices", "settings_snapshot"):
        op.drop_column("invoices", "settings_snapshot")
    if _column_exists("invoices", "gst_rate_snapshot"):
        op.drop_column("invoices", "gst_rate_snapshot")
    if _column_exists("invoices", "branding_snapshot"):
        op.drop_column("invoices", "branding_snapshot")

    # Drop customer mobile index & column
    op.drop_index("idx_customer_mobile", table_name="customers")
    if _column_exists("customers", "mobile_normalized"):
        op.drop_column("customers", "mobile_normalized")


def _column_exists(table_name: str, column_name: str) -> bool:
    """Utility: check if a column exists using Alembic inspector (runtime)."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols
