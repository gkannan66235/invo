"""
Database models for the GST Compliant Service Center Management System.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from sqlalchemy import (
    Boolean, DateTime, Integer, String, Text, Numeric,
    ForeignKey, Table, Column, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func


Base = declarative_base()


class CustomerType(str, Enum):
    """Customer type enumeration."""
    INDIVIDUAL = "individual"
    BUSINESS = "business"


class OrderType(str, Enum):
    """Order type enumeration."""
    SALE = "sale"
    PURCHASE = "purchase"
    SERVICE = "service"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"


class ItemCategory(str, Enum):
    """Inventory item category enumeration."""
    PUMP = "pump"
    MOTOR = "motor"
    SPARE_PART = "spare_part"
    SERVICE = "service"


class GSTTreatment(str, Enum):
    """GST treatment enumeration."""
    TAXABLE = "taxable"
    EXEMPT = "exempt"
    ZERO_RATED = "zero_rated"


# Association table for user roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', PostgresUUID(as_uuid=True),
           ForeignKey('users.id'), primary_key=True),
    Column('role_id', PostgresUUID(as_uuid=True),
           ForeignKey('roles.id'), primary_key=True)
)


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        return email.lower()


class Role(Base):
    """Role model for authorization."""
    __tablename__ = 'roles'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")


class Customer(Base):
    """Customer model for managing customer information."""
    __tablename__ = 'customers'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), index=True)
    phone = Column(String(15), index=True)
    gst_number = Column(String(15), index=True)
    pan_number = Column(String(10))
    customer_type = Column(String(20), nullable=False,
                           default=CustomerType.INDIVIDUAL.value)

    # Address information (embedded JSON)
    address = Column(JSONB, default=dict)

    # Financial information
    credit_limit = Column(Numeric(15, 2), default=0)
    outstanding_amount = Column(Numeric(15, 2), default=0)

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")

    # Constraints
    __table_args__ = (
        CheckConstraint('credit_limit >= 0',
                        name='check_credit_limit_positive'),
        CheckConstraint('outstanding_amount >= 0',
                        name='check_outstanding_positive'),
        CheckConstraint("customer_type IN ('individual', 'business')",
                        name='check_valid_customer_type'),
        Index('idx_customer_gst_number', 'gst_number'),
        Index('idx_customer_name_type', 'name', 'customer_type'),
    )

    @validates('gst_number')
    def validate_gst_number(self, key, gst_number):
        """Validate GST number format for Indian businesses."""
        if gst_number and self.customer_type == CustomerType.BUSINESS.value:
            import re
            # GST format: 2 digits state code + 10 chars PAN + 1 entity number + 1 default 'Z' + 1 check digit
            pattern = r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][Z][0-9A-Z]$'
            if not re.match(pattern, gst_number):
                raise ValueError(f"Invalid GST number format: {gst_number}")
        return gst_number

    @validates('phone')
    def validate_phone(self, key, phone):
        """Validate phone number format."""
        if phone:
            import re
            # Indian phone number validation
            pattern = r'^(\+91|91)?[6-9]\d{9}$'
            cleaned = re.sub(r'[^\d+]', '', phone)
            if not re.match(pattern, cleaned):
                raise ValueError(f"Invalid phone number format: {phone}")
            return cleaned
        return phone


class Supplier(Base):
    """Supplier model for managing supplier information."""
    __tablename__ = 'suppliers'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), index=True)
    phone = Column(String(15), index=True)
    gst_number = Column(String(15), index=True)
    pan_number = Column(String(10))

    # Address information (embedded JSON)
    address = Column(JSONB, default=dict)

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")

    @validates('gst_number')
    def validate_gst_number(self, key, gst_number):
        """Validate GST number format."""
        if gst_number:
            import re
            pattern = r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][Z][0-9A-Z]$'
            if not re.match(pattern, gst_number):
                raise ValueError(f"Invalid GST number format: {gst_number}")
        return gst_number


class InventoryItem(Base):
    """Inventory item model for managing products and services."""
    __tablename__ = 'inventory_items'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    product_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    # Harmonized System of Nomenclature
    hsn_code = Column(String(10), nullable=False, index=True)
    gst_rate = Column(Numeric(5, 2), nullable=False)  # GST rate percentage

    # Inventory tracking
    current_stock = Column(Integer, default=0, nullable=False)
    minimum_stock_level = Column(Integer, default=0, nullable=False)
    maximum_stock_level = Column(Integer)
    reorder_quantity = Column(Integer, default=0)

    # Pricing
    purchase_price = Column(Numeric(10, 2), default=0)
    selling_price = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2))  # Maximum Retail Price

    # Categorization
    category = Column(String(20), nullable=False,
                      default=ItemCategory.SPARE_PART.value)
    brand = Column(String(50))
    model = Column(String(50))
    specifications = Column(JSONB, default=dict)

    # Supplier information
    supplier_id = Column(PostgresUUID(as_uuid=True),
                         ForeignKey('suppliers.id'), index=True)

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="inventory_items")
    order_items = relationship("OrderItem", back_populates="inventory_item")

    # Constraints
    __table_args__ = (
        CheckConstraint('current_stock >= 0',
                        name='check_current_stock_positive'),
        CheckConstraint('minimum_stock_level >= 0',
                        name='check_minimum_stock_positive'),
        CheckConstraint('selling_price > 0',
                        name='check_selling_price_positive'),
        CheckConstraint('gst_rate >= 0 AND gst_rate <= 100',
                        name='check_gst_rate_valid'),
        CheckConstraint(
            "category IN ('pump', 'motor', 'spare_part', 'service')", name='check_valid_category'),
        Index('idx_inventory_category_active', 'category', 'is_active'),
        Index('idx_inventory_stock_level',
              'current_stock', 'minimum_stock_level'),
    )

    @property
    def is_low_stock(self) -> bool:
        """Check if item is below minimum stock level."""
        return self.current_stock <= self.minimum_stock_level

    @validates('hsn_code')
    def validate_hsn_code(self, key, hsn_code):
        """Validate HSN code format."""
        if hsn_code:
            import re
            # HSN codes can be 4, 6, or 8 digits
            pattern = r'^\d{4}(\d{2})?(\d{2})?$'
            if not re.match(pattern, hsn_code):
                raise ValueError(f"Invalid HSN code format: {hsn_code}")
        return hsn_code


class Order(Base):
    """Order model for managing sales and purchase orders."""
    __tablename__ = 'orders'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    order_type = Column(String(20), nullable=False,
                        default=OrderType.SALE.value)
    status = Column(String(20), nullable=False,
                    default=OrderStatus.DRAFT.value)

    # Customer/Supplier information
    customer_id = Column(PostgresUUID(as_uuid=True),
                         ForeignKey('customers.id'), index=True)

    # Order details
    order_date = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    expected_delivery_date = Column(DateTime(timezone=True))
    actual_delivery_date = Column(DateTime(timezone=True))

    # Amounts and calculations
    subtotal = Column(Numeric(15, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(15, 2), default=0)
    gst_amount = Column(Numeric(15, 2), default=0, nullable=False)
    total_amount = Column(Numeric(15, 2), default=0, nullable=False)

    # GST and compliance
    gst_treatment = Column(String(20), default=GSTTreatment.TAXABLE.value)
    place_of_supply = Column(String(50))  # State/UT for GST calculation

    # Payment information
    # e.g., "net_30", "immediate", "advance"
    payment_terms = Column(String(50))
    payment_status = Column(String(20), default=PaymentStatus.PENDING.value)

    # Additional information
    notes = Column(Text)
    internal_notes = Column(Text)

    # Status and metadata
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="order")
    created_by_user = relationship("User")

    # Constraints
    __table_args__ = (
        CheckConstraint('subtotal >= 0', name='check_subtotal_positive'),
        CheckConstraint('total_amount >= 0', name='check_total_positive'),
        CheckConstraint(
            "order_type IN ('sale', 'purchase', 'service')", name='check_valid_order_type'),
        CheckConstraint(
            "status IN ('draft', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled')", name='check_valid_status'),
        CheckConstraint("gst_treatment IN ('taxable', 'exempt', 'zero_rated')",
                        name='check_valid_gst_treatment'),
        Index('idx_order_date_status', 'order_date', 'status'),
        Index('idx_order_customer_date', 'customer_id', 'order_date'),
    )

    def generate_order_number(self) -> str:
        """Generate unique order number based on type and date."""
        from datetime import datetime
        prefix = {
            OrderType.SALE.value: "SO",
            OrderType.PURCHASE.value: "PO",
            OrderType.SERVICE.value: "SV"
        }.get(self.order_type, "OR")

        today = datetime.now().strftime("%Y%m%d")
        return f"{prefix}{today}{str(self.id)[-6:].upper()}"


class OrderItem(Base):
    """Order item model for individual line items in orders."""
    __tablename__ = 'order_items'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    order_id = Column(PostgresUUID(as_uuid=True), ForeignKey(
        'orders.id'), nullable=False, index=True)
    inventory_item_id = Column(PostgresUUID(as_uuid=True), ForeignKey(
        'inventory_items.id'), nullable=False)

    # Item details
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)

    # Calculated amounts
    line_total = Column(Numeric(15, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    gst_amount = Column(Numeric(15, 2), nullable=False)
    final_amount = Column(Numeric(15, 2), nullable=False)

    # Item description (snapshot at time of order)
    item_description = Column(Text, nullable=False)
    hsn_code = Column(String(10), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    inventory_item = relationship(
        "InventoryItem", back_populates="order_items")

    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('unit_price >= 0', name='check_unit_price_positive'),
        CheckConstraint('discount_percentage >= 0 AND discount_percentage <= 100',
                        name='check_discount_percentage_valid'),
        CheckConstraint('gst_rate >= 0 AND gst_rate <= 100',
                        name='check_item_gst_rate_valid'),
        Index('idx_order_item_order', 'order_id'),
    )


class Invoice(Base):
    """Invoice model for billing and compliance."""
    __tablename__ = 'invoices'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    invoice_number = Column(String(50), unique=True,
                            nullable=False, index=True)
    order_id = Column(PostgresUUID(as_uuid=True),
                      ForeignKey('orders.id'), index=True)
    customer_id = Column(PostgresUUID(as_uuid=True), ForeignKey(
        'customers.id'), nullable=False, index=True)

    # Invoice details
    invoice_date = Column(DateTime(timezone=True),
                          server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True))

    # Amounts
    subtotal = Column(Numeric(15, 2), nullable=False)
    discount_amount = Column(Numeric(15, 2), default=0)
    gst_amount = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    paid_amount = Column(Numeric(15, 2), default=0)

    # GST compliance
    place_of_supply = Column(String(50), nullable=False)
    gst_treatment = Column(String(20), default=GSTTreatment.TAXABLE.value)
    reverse_charge = Column(Boolean, default=False)

    # Status
    payment_status = Column(String(20), default=PaymentStatus.PENDING.value)

    # Additional information
    notes = Column(Text)
    terms_and_conditions = Column(Text)

    # Status and metadata
    is_cancelled = Column(Boolean, default=False)
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")

    # Constraints
    __table_args__ = (
        CheckConstraint('subtotal >= 0',
                        name='check_invoice_subtotal_positive'),
        CheckConstraint('total_amount >= 0',
                        name='check_invoice_total_positive'),
        CheckConstraint('paid_amount >= 0', name='check_paid_amount_positive'),
        CheckConstraint('paid_amount <= total_amount',
                        name='check_paid_not_exceed_total'),
        CheckConstraint("payment_status IN ('pending', 'partial', 'paid', 'overdue')",
                        name='check_valid_payment_status'),
        Index('idx_invoice_date_status', 'invoice_date', 'payment_status'),
        Index('idx_invoice_customer_date', 'customer_id', 'invoice_date'),
    )

    @property
    def outstanding_amount(self) -> Decimal:
        """Calculate outstanding amount."""
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.due_date and self.payment_status != PaymentStatus.PAID.value:
            return datetime.now(timezone.utc) > self.due_date
        return False


# Create indexes for performance
Index('idx_users_username_active', User.username, User.is_active)
Index('idx_customers_name_active', Customer.name, Customer.is_active)
Index('idx_inventory_product_code', InventoryItem.product_code)
Index('idx_orders_status_date', Order.status, Order.order_date)
