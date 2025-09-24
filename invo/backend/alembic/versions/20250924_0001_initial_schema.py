"""initial schema

Revision ID: 20250924_0001
Revises: 
Create Date: 2025-09-24 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250924_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: This initial migration assumes a fresh database. If database already has tables,
    # generate a revision with --autogenerate instead of applying this directly.
    op.create_table('roles',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('name', sa.String(length=50),
                              nullable=False, unique=True),
                    sa.Column('description', sa.Text()),
                    sa.Column('permissions', postgresql.JSONB(),
                              server_default=sa.text("'[]'::jsonb")),
                    sa.Column('is_active', sa.Boolean(), nullable=False,
                              server_default=sa.text('true')),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )

    op.create_table('users',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('username', sa.String(length=50),
                              nullable=False, unique=True),
                    sa.Column('email', sa.String(length=255),
                              nullable=False, unique=True),
                    sa.Column('password_hash', sa.String(
                        length=255), nullable=False),
                    sa.Column('full_name', sa.String(
                        length=100), nullable=False),
                    sa.Column('is_active', sa.Boolean(), nullable=False,
                              server_default=sa.text('true')),
                    sa.Column('is_admin', sa.Boolean(), nullable=False,
                              server_default=sa.text('false')),
                    sa.Column('last_login', sa.DateTime(timezone=True)),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )
    op.create_index('idx_users_username_active',
                    'users', ['username', 'is_active'])

    op.create_table('roles_users',
                    sa.Column('user_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('role_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    )

    op.create_table('customers',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('email', sa.String(length=255)),
                    sa.Column('phone', sa.String(length=15)),
                    sa.Column('gst_number', sa.String(length=15)),
                    sa.Column('pan_number', sa.String(length=10)),
                    sa.Column('customer_type', sa.String(length=20),
                              nullable=False, server_default=sa.text("'individual'")),
                    sa.Column('address', postgresql.JSONB(),
                              server_default=sa.text("'{}'::jsonb")),
                    sa.Column('credit_limit', sa.Numeric(
                        15, 2), server_default=sa.text('0')),
                    sa.Column('outstanding_amount', sa.Numeric(
                        15, 2), server_default=sa.text('0')),
                    sa.Column('is_active', sa.Boolean(), nullable=False,
                              server_default=sa.text('true')),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )
    op.create_index('idx_customer_gst_number', 'customers', ['gst_number'])

    op.create_table('suppliers',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('email', sa.String(length=255)),
                    sa.Column('phone', sa.String(length=15)),
                    sa.Column('gst_number', sa.String(length=15)),
                    sa.Column('pan_number', sa.String(length=10)),
                    sa.Column('address', postgresql.JSONB(),
                              server_default=sa.text("'{}'::jsonb")),
                    sa.Column('is_active', sa.Boolean(), nullable=False,
                              server_default=sa.text('true')),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )

    op.create_table('inventory_items',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('product_code', sa.String(length=50),
                              nullable=False, unique=True),
                    sa.Column('description', sa.Text(), nullable=False),
                    sa.Column('hsn_code', sa.String(
                        length=10), nullable=False),
                    sa.Column('gst_rate', sa.Numeric(5, 2), nullable=False),
                    sa.Column('current_stock', sa.Integer(),
                              nullable=False, server_default=sa.text('0')),
                    sa.Column('minimum_stock_level', sa.Integer(),
                              nullable=False, server_default=sa.text('0')),
                    sa.Column('maximum_stock_level', sa.Integer()),
                    sa.Column('reorder_quantity', sa.Integer(),
                              server_default=sa.text('0')),
                    sa.Column('purchase_price', sa.Numeric(
                        10, 2), server_default=sa.text('0')),
                    sa.Column('selling_price', sa.Numeric(
                        10, 2), nullable=False),
                    sa.Column('mrp', sa.Numeric(10, 2)),
                    sa.Column('category', sa.String(length=20), nullable=False,
                              server_default=sa.text("'spare_part'")),
                    sa.Column('brand', sa.String(length=50)),
                    sa.Column('model', sa.String(length=50)),
                    sa.Column('specifications', postgresql.JSONB(),
                              server_default=sa.text("'{}'::jsonb")),
                    sa.Column('supplier_id', postgresql.UUID(as_uuid=True)),
                    sa.Column('is_active', sa.Boolean(), nullable=False,
                              server_default=sa.text('true')),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )

    op.create_table('orders',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('order_number', sa.String(length=50),
                              nullable=False, unique=True),
                    sa.Column('order_type', sa.String(length=20),
                              nullable=False, server_default=sa.text("'sale'")),
                    sa.Column('status', sa.String(length=20), nullable=False,
                              server_default=sa.text("'draft'")),
                    sa.Column('customer_id', postgresql.UUID(as_uuid=True)),
                    sa.Column('order_date', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('expected_delivery_date',
                              sa.DateTime(timezone=True)),
                    sa.Column('actual_delivery_date',
                              sa.DateTime(timezone=True)),
                    sa.Column('subtotal', sa.Numeric(15, 2),
                              nullable=False, server_default=sa.text('0')),
                    sa.Column('discount_amount', sa.Numeric(
                        15, 2), server_default=sa.text('0')),
                    sa.Column('gst_amount', sa.Numeric(15, 2),
                              nullable=False, server_default=sa.text('0')),
                    sa.Column('total_amount', sa.Numeric(15, 2),
                              nullable=False, server_default=sa.text('0')),
                    sa.Column('gst_treatment', sa.String(length=20),
                              server_default=sa.text("'taxable'")),
                    sa.Column('place_of_supply', sa.String(length=50)),
                    sa.Column('payment_terms', sa.String(length=50)),
                    sa.Column('payment_status', sa.String(length=20),
                              server_default=sa.text("'pending'")),
                    sa.Column('notes', sa.Text()),
                    sa.Column('internal_notes', sa.Text()),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('created_by', postgresql.UUID(as_uuid=True))
                    )

    op.create_table('invoices',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), primary_key=True),
                    sa.Column('invoice_number', sa.String(
                        length=50), nullable=False, unique=True),
                    sa.Column('order_id', postgresql.UUID(as_uuid=True)),
                    sa.Column('customer_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('invoice_date', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('due_date', sa.DateTime(timezone=True)),
                    sa.Column('subtotal', sa.Numeric(15, 2), nullable=False),
                    sa.Column('discount_amount', sa.Numeric(
                        15, 2), server_default=sa.text('0')),
                    sa.Column('gst_amount', sa.Numeric(15, 2), nullable=False),
                    sa.Column('total_amount', sa.Numeric(
                        15, 2), nullable=False),
                    sa.Column('paid_amount', sa.Numeric(15, 2),
                              server_default=sa.text('0')),
                    sa.Column('gst_rate', sa.Numeric(5, 2)),
                    sa.Column('service_type', sa.String(length=100)),
                    sa.Column('place_of_supply', sa.String(
                        length=50), nullable=False),
                    sa.Column('gst_treatment', sa.String(length=20),
                              server_default=sa.text("'taxable'")),
                    sa.Column('reverse_charge', sa.Boolean(),
                              server_default=sa.text('false')),
                    sa.Column('payment_status', sa.String(length=20),
                              server_default=sa.text("'pending'")),
                    sa.Column('notes', sa.Text()),
                    sa.Column('terms_and_conditions', sa.Text()),
                    sa.Column('is_cancelled', sa.Boolean(),
                              server_default=sa.text('false')),
                    sa.Column('cancelled_at', sa.DateTime(timezone=True)),
                    sa.Column('created_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True),
                              server_default=sa.text('now()'), nullable=False)
                    )


def downgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('orders')
    op.drop_table('inventory_items')
    op.drop_table('suppliers')
    op.drop_table('customers')
    op.drop_table('roles_users')
    op.drop_table('users')
    op.drop_table('roles')
