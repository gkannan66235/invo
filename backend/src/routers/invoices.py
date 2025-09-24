"""Invoice router providing basic CRUD operations."""
from datetime import datetime
from uuid import uuid4
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_async_db_dependency
from ..models.database import Invoice, Customer, PaymentStatus, GSTTreatment
from ..utils.errors import ERROR_CODES, OverpayNotAllowed
from ..config.settings import get_default_gst_rate
from .auth import get_current_user, User

router = APIRouter()

# Pydantic schemas


class InvoiceCreate(BaseModel):
    # Ignore unknown fields from frontend
    model_config = ConfigDict(extra='ignore')
    """Flexible invoice create model supporting both backend and frontend schemas.

    Frontend (current) sends:
        customer_name, customer_phone, customer_email?, service_type, service_description,
        amount, gst_rate, due_date?

    Original backend design expected:
        customer_id, subtotal, gst_amount, total_amount, place_of_supply

    This unified model makes all fields optional and we'll derive missing values.
    """
    # Frontend style
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    service_type: Optional[str] = None
    service_description: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    # Default moved to runtime (settings) in T023; keep None here to detect omission explicitly
    gst_rate: Optional[float] = Field(default=None, ge=0)

    # Backend style
    customer_id: Optional[UUID] = None
    subtotal: Optional[float] = Field(default=None, ge=0)
    discount_amount: float = 0
    gst_amount: Optional[float] = Field(default=None, ge=0)
    total_amount: Optional[float] = Field(default=None, ge=0)
    place_of_supply: Optional[str] = None
    gst_treatment: Optional[str] = GSTTreatment.TAXABLE.value
    reverse_charge: bool = False
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, values):  # type: ignore
        """Normalize and coerce diverse frontend payload shapes to internal schema.

        Handles:
          - CamelCase keys: customerName, customerPhone, serviceDescription, gstRate
          - Alternate keys: name -> customer_name, phone -> customer_phone
          - Numeric strings for amount / gst_rate
          - Empty strings converted to None
          - due_date string parsing (ISO 8601) or blank -> None
        """
        if not isinstance(values, dict):
            return values
        key_map = {
            'customerName': 'customer_name',
            'customerPhone': 'customer_phone',
            'serviceDescription': 'service_description',
            'gstRate': 'gst_rate',
            'name': 'customer_name',
            'phone': 'customer_phone'
        }
        for src, dest in key_map.items():
            if src in values and dest not in values:
                values[dest] = values[src]

        # Coerce numeric fields
        for num_field in ['amount', 'gst_rate', 'subtotal', 'gst_amount', 'total_amount', 'discount_amount']:
            if num_field in values:
                if isinstance(values[num_field], str):
                    if values[num_field].strip() == '':
                        values[num_field] = None
                    else:
                        try:
                            values[num_field] = float(values[num_field])
                        except ValueError:
                            raise ValueError(
                                f"Field '{num_field}' must be a number")

        # Normalize due_date
        if 'due_date' in values and isinstance(values['due_date'], str):
            if values['due_date'].strip() == '':
                values['due_date'] = None
            else:
                try:
                    # Attempt parse (accept date or datetime iso)
                    values['due_date'] = datetime.fromisoformat(
                        values['due_date'])
                except ValueError:
                    raise ValueError(
                        "Field 'due_date' must be ISO 8601 date/datetime string")

        return values


class InvoiceUpdate(BaseModel):
    # Allow whole invoice object to be sent
    model_config = ConfigDict(extra='ignore')
    """Flexible update model supporting both payment/status changes and service detail edits.

    This allows the current frontend (which re-sends create-style fields) to update seamlessly.
    """
    # Allow id / invoice_number in payload (ignored for update logic but prevents 422)
    id: Optional[str] = None
    invoice_number: Optional[str] = None
    # Frontend style (all optional)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    service_type: Optional[str] = None
    service_description: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    gst_rate: Optional[float] = Field(default=None, ge=0)
    due_date: Optional[datetime] = None

    # Payment & backend oriented
    paid_amount: Optional[float] = None
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None  # frontend status (draft/sent/paid/cancelled)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, values):  # type: ignore
        """Normalize camelCase and alternate frontend keys; parse dates; empty strings -> None.

        Mirrors create normalization so frontend can submit the same shape for updates without 422.
        """
        if not isinstance(values, dict):
            return values
        key_map = {
            'customerName': 'customer_name',
            'customerPhone': 'customer_phone',
            'customerEmail': 'customer_email',
            'serviceDescription': 'service_description',
            'serviceType': 'service_type',
            'gstRate': 'gst_rate',
            'paidAmount': 'paid_amount',
            'invoiceNumber': 'invoice_number',
            'dueDate': 'due_date',
            'name': 'customer_name',
            'phone': 'customer_phone'
        }
        for src, dest in key_map.items():
            if src in values and dest not in values:
                values[dest] = values[src]

        # Normalize empty string to None for selected fields
        for field in [
            'customer_name', 'customer_phone', 'customer_email', 'service_description',
                'service_type', 'status', 'payment_status']:
            if field in values and isinstance(values[field], str) and values[field].strip() == '':
                values[field] = None

        # due_date parsing (ISO 8601 date or datetime)
        if 'due_date' in values and isinstance(values['due_date'], str):
            if values['due_date'].strip() == '':
                values['due_date'] = None
            else:
                try:
                    values['due_date'] = datetime.fromisoformat(
                        values['due_date'])
                except ValueError:
                    raise ValueError(
                        "Field 'due_date' must be ISO 8601 date/datetime string")

        return values

    @model_validator(mode="before")
    @classmethod
    def coerce_numbers(cls, values):  # type: ignore
        """Coerce numeric string inputs to floats for robustness."""
        for field in ["amount", "gst_rate", "paid_amount"]:
            if field in values and isinstance(values[field], str) and values[field].strip() != "":
                try:
                    values[field] = float(values[field])
                except ValueError:
                    raise ValueError(f"Field '{field}' must be a number")
            if field in values and values[field] == "":  # empty string -> None
                values[field] = None
        return values


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: UUID
    subtotal: float
    discount_amount: float
    gst_amount: float
    total_amount: float
    paid_amount: float
    outstanding_amount: float
    payment_status: str
    place_of_supply: str
    gst_treatment: str
    reverse_charge: bool
    is_cancelled: bool
    invoice_date: datetime
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Helpers


async def _generate_invoice_number(db: AsyncSession) -> str:
    from datetime import UTC
    now_utc = datetime.now(UTC)
    today = now_utc.strftime('%Y%m%d')
    # Count invoices for today to increment
    start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(select(Invoice).where(Invoice.invoice_date >= start_of_day))
    count = len(result.scalars().all()) + 1
    return f"INV{today}{count:04d}"  # e.g. INV20250924 0001

# Routes


def _to_frontend_invoice(invoice: Invoice, customer: Optional[Customer] = None) -> dict:
    """Transform backend invoice + customer into the shape expected by current frontend."""
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
        "customer_name": customer.name if customer else None,
        "customer_phone": customer.phone if customer else None,
        "customer_email": customer.email if customer else None,
        "service_type": invoice.service_type,
        "service_description": invoice.notes,  # Using notes as placeholder
        "amount": float(invoice.subtotal),
        "gst_rate": float(invoice.gst_rate) if invoice.gst_rate is not None else None,
        "gst_amount": float(invoice.gst_amount),
        "total_amount": float(invoice.total_amount),
        # Map directly (frontend will adapt later)
        "status": invoice.payment_status,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "payment_status": invoice.payment_status,
        "place_of_supply": invoice.place_of_supply,
        "gst_treatment": invoice.gst_treatment,
        "reverse_charge": invoice.reverse_charge,
        "outstanding_amount": float(invoice.outstanding_amount),
        "is_cancelled": bool(invoice.is_cancelled),
        # Include is_deleted to enable UI decisions; list endpoint already filters them out (T026/T027)
        "is_deleted": bool(getattr(invoice, 'is_deleted', False)),
    }


@router.get('/')
async def list_invoices(
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    # Exclude soft-deleted invoices (T027)
    result = await db.execute(
        select(Invoice)
        .where(Invoice.is_deleted.is_(False))
        .order_by(Invoice.created_at.desc())
        .limit(100)
    )
    invoices = result.scalars().all()

    # Fetch customers for mapping to reduce N+1 (simple approach: gather ids then fetch)
    customer_ids = {inv.customer_id for inv in invoices if inv.customer_id}
    customers_map = {}
    if customer_ids:
        cust_result = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        for c in cust_result.scalars().all():
            customers_map[c.id] = c

    return [_to_frontend_invoice(inv, customers_map.get(inv.customer_id)) for inv in invoices]


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    # Determine creation path
    customer: Optional[Customer] = None
    if not payload.customer_id:
        # Frontend style - must have customer_name & phone & amount
        if not (payload.customer_name and payload.customer_phone and payload.amount is not None):
            # Raise validation style HTTPException with code attribute consumed by global handler
            exc = HTTPException(
                status_code=422, detail="Missing required customer or amount fields")
            # annotate for handler
            setattr(exc, 'code', ERROR_CODES['validation'])
            raise exc

        # Try to find existing customer by name+phone
        existing = await db.execute(
            select(Customer).where(
                Customer.name == payload.customer_name,
                Customer.phone == payload.customer_phone
            )
        )
        customer = existing.scalar_one_or_none()
        if not customer:
            customer = Customer(
                name=payload.customer_name,
                phone=payload.customer_phone,
                email=payload.customer_email,
                customer_type='individual',
                is_active=True,
                address={},
            )
            db.add(customer)
            await db.flush()  # Get customer.id
        customer_id = customer.id
        subtotal = float(payload.amount)
        # Apply default GST if omitted (T023)
        # Distinguish between omitted/None (use default) vs explicit provided value (could be 0)
        if payload.gst_rate is None:
            effective_gst_rate = get_default_gst_rate()
            gst_rate = float(effective_gst_rate)
        else:
            gst_rate = float(payload.gst_rate)
        gst_amount = round(subtotal * (gst_rate or 0) / 100, 2)
        total_amount = round(subtotal + gst_amount, 2)
        place_of_supply = payload.place_of_supply or 'KA'
        notes = payload.service_description or payload.notes
    else:
        # Backend style
        customer_id = payload.customer_id
        # Fetch customer
        cust_res = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = cust_res.scalar_one_or_none()
        if not customer:
            exc = HTTPException(status_code=404, detail='Customer not found')
            setattr(exc, 'code', ERROR_CODES['not_found'])
            raise exc
        subtotal = float(payload.subtotal or 0)
        gst_amount = float(payload.gst_amount or 0)
        total_amount = float(payload.total_amount or (subtotal + gst_amount))
        place_of_supply = payload.place_of_supply or 'KA'
        notes = payload.notes

    invoice_number = await _generate_invoice_number(db)

    invoice = Invoice(
        id=uuid4(),  # Explicit UUID to avoid relying on Postgres gen_random_uuid() in SQLite tests
        invoice_number=invoice_number,
        customer_id=customer_id,
        subtotal=subtotal,
        discount_amount=payload.discount_amount,
        gst_amount=gst_amount,
        total_amount=total_amount,
        paid_amount=0,
        gst_rate=gst_rate,
        service_type=payload.service_type,
        place_of_supply=place_of_supply,
        gst_treatment=payload.gst_treatment or GSTTreatment.TAXABLE.value,
        reverse_charge=payload.reverse_charge,
        due_date=payload.due_date,
        notes=notes,
        terms_and_conditions=payload.terms_and_conditions,
        payment_status=PaymentStatus.PENDING.value,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return _to_frontend_invoice(invoice, customer)


@router.get('/{invoice_id}')
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        exc = HTTPException(status_code=404, detail='Invoice not found')
        setattr(exc, 'code', ERROR_CODES['not_found'])
        raise exc
    # Fetch customer
    cust = None
    if invoice.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        cust = cust_res.scalar_one_or_none()
    return _to_frontend_invoice(invoice, cust)


def _apply_update(invoice: Invoice, payload: InvoiceUpdate):
    """Apply mutable field updates to invoice instance (in-place)."""
    # Service description stored in notes (until dedicated columns added)
    if payload.service_description is not None:
        invoice.notes = payload.service_description
    if payload.notes is not None:
        invoice.notes = payload.notes
    if payload.terms_and_conditions is not None:
        invoice.terms_and_conditions = payload.terms_and_conditions
    if payload.service_type is not None:
        invoice.service_type = payload.service_type
    if payload.amount is not None:
        invoice.subtotal = float(payload.amount)

    if payload.gst_rate is not None:
        invoice.gst_rate = float(payload.gst_rate)
    # If gst_rate stayed None (legacy invoices) recompute with 0 rate so math consistent
    if invoice.gst_rate is None:
        invoice.gst_rate = 0.0

    # Recompute if amount or gst_rate changed
    if payload.gst_rate is not None or payload.amount is not None:
        base_amount = float(invoice.subtotal)
        rate = float(invoice.gst_rate or 0)
        gst_amount = round(base_amount * rate / 100, 2)
        invoice.gst_amount = gst_amount
        invoice.total_amount = round(base_amount + gst_amount, 2)

    # Paid amount / payment status logic
    if payload.paid_amount is not None:
        if payload.paid_amount < 0 or payload.paid_amount > float(invoice.total_amount):
            # Standardized overpay error
            domain_err = OverpayNotAllowed(
                payload.paid_amount, float(invoice.total_amount))
            exc = HTTPException(status_code=400, detail=domain_err.message)
            setattr(exc, 'code', domain_err.code)
            raise exc
        invoice.paid_amount = payload.paid_amount
        if invoice.paid_amount == invoice.total_amount:
            invoice.payment_status = PaymentStatus.PAID.value
        elif invoice.paid_amount > 0:
            invoice.payment_status = PaymentStatus.PARTIAL.value
        else:
            invoice.payment_status = PaymentStatus.PENDING.value

    # Explicit payment_status override
    if payload.payment_status is not None:
        invoice.payment_status = payload.payment_status

    # Frontend 'status' mapping (draft|sent|paid|cancelled) -> internal fields
    if payload.status is not None:
        status_map = payload.status.lower()
        if status_map == 'paid':
            invoice.payment_status = PaymentStatus.PAID.value
            invoice.paid_amount = invoice.total_amount
        elif status_map == 'draft':
            invoice.payment_status = PaymentStatus.PENDING.value
        elif status_map == 'sent':
            # Treat 'sent' as pending (not yet paid)
            if invoice.paid_amount == 0:
                invoice.payment_status = PaymentStatus.PENDING.value
        elif status_map == 'cancelled':
            invoice.is_cancelled = True


async def _update_invoice_logic(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: AsyncSession
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        exc = HTTPException(status_code=404, detail='Invoice not found')
        setattr(exc, 'code', ERROR_CODES['not_found'])
        raise exc
    _apply_update(invoice, payload)
    await db.commit()
    await db.refresh(invoice)
    cust = None
    if invoice.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        cust = cust_res.scalar_one_or_none()
    return _to_frontend_invoice(invoice, cust)


@router.patch('/{invoice_id}')
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    return await _update_invoice_logic(invoice_id, payload, db)


@router.put('/{invoice_id}')
async def replace_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,  # Accept same flexible model
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    # Treat PUT as full update but since fields are optional, behavior mirrors PATCH unless fields supplied
    return await _update_invoice_logic(invoice_id, payload, db)


@router.delete('/{invoice_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        exc = HTTPException(status_code=404, detail='Invoice not found')
        setattr(exc, 'code', ERROR_CODES['not_found'])
        raise exc
    # Soft delete (T026): mark as deleted but retain record
    if not invoice.is_deleted:
        invoice.is_deleted = True
        await db.commit()
        await db.refresh(invoice)
    return None
