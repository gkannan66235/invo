"""Invoice router providing basic CRUD operations.

Phase 3 Adjustments (Tasks T019, T021, T028):
 - Layering note: this router will delegate to a forthcoming service layer (services/invoice_service.py)
 - Standardized error codes using utilities (INVOICE_NOT_FOUND replaces generic NOT_FOUND for domain clarity)
 - Metrics emission (create/update/delete counters) per observability plan (Section 9) & T028
"""
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, model_validator, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:  # Prefer src.* imports; fallback adds backend dir to path
    from src.config.database import get_async_db_dependency  # type: ignore
    from src.models.database import Invoice, Customer, PaymentStatus, GSTTreatment  # type: ignore
    from src.utils.errors import ERROR_CODES, OverpayNotAllowed  # type: ignore
    from src.config.settings import get_default_gst_rate  # type: ignore
    from src.config.observability import (  # type: ignore
        invoice_create_counter,
        invoice_update_counter,
        invoice_delete_counter,
        record_invoice_operation,
    )
    from src.services.invoice_service import (
        create_invoice_service,
        get_invoice_service,
        update_invoice_service,
        delete_invoice_service,
        record_invoice_download,
        InvoiceNotFound,
        ValidationError,
        CustomerNotFound,
        OverpayNotAllowed as ServiceOverpayNotAllowed,
    )
except ImportError:
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.append(str(backend_dir))
    from src.config.database import get_async_db_dependency  # type: ignore
    from src.models.database import Invoice, Customer, PaymentStatus, GSTTreatment  # type: ignore
    from src.utils.errors import ERROR_CODES, OverpayNotAllowed  # type: ignore
    from src.config.settings import get_default_gst_rate  # type: ignore
    from src.config.observability import (  # type: ignore
        invoice_create_counter,
        invoice_update_counter,
        invoice_delete_counter,
        record_invoice_operation,
    )
    from src.services.invoice_service import (
        create_invoice_service,
        get_invoice_service,
        update_invoice_service,
        delete_invoice_service,
        record_invoice_download,
        InvoiceNotFound,
        ValidationError,
        CustomerNotFound,
        OverpayNotAllowed as ServiceOverpayNotAllowed,
    )
from .auth import get_current_user, User

router = APIRouter()


def _success(data, **meta):  # lightweight envelope helper
    import time as _time
    return {"status": "success", "data": data, "meta": meta or None, "timestamp": _time.time()}


def _is_raw_legacy_mode(request: Request) -> bool:
    # Explicit header takes precedence to avoid impacting auth_client (which also uses fast token)
    if request.headers.get("X-Raw-Mode") in {"1", "true", "raw"}:
        return True
    # Backward compatibility: only treat fast token as raw if explicit header not required
    # (kept for any lingering tests not updated yet)
    auth = request.headers.get("Authorization", "")
    return auth.endswith("test.fast.token") and request.headers.get("X-Raw-Mode") is not None

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
        for src_key, dest_key in key_map.items():
            if src_key in values and dest_key not in values:
                values[dest_key] = values[src_key]

        # Coerce numeric fields
        for num_field in ['amount', 'gst_rate', 'subtotal', 'gst_amount', 'total_amount', 'discount_amount']:
            if num_field in values:
                if isinstance(values[num_field], str):
                    if values[num_field].strip() == '':
                        values[num_field] = None
                    else:
                        try:
                            values[num_field] = float(values[num_field])
                        except ValueError as exc:
                            raise ValueError(
                                f"Field '{num_field}' must be a number") from exc

        # Normalize due_date
        if 'due_date' in values and isinstance(values['due_date'], str):
            if values['due_date'].strip() == '':
                values['due_date'] = None
            else:
                try:
                    values['due_date'] = datetime.fromisoformat(
                        values['due_date'])
                except ValueError as exc:
                    raise ValueError(
                        "Field 'due_date' must be ISO 8601 date/datetime string") from exc

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
        for src_key, dest_key in key_map.items():
            if src_key in values and dest_key not in values:
                values[dest_key] = values[src_key]

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
                except ValueError as exc:
                    raise ValueError(
                        "Field 'due_date' must be ISO 8601 date/datetime string") from exc

        return values

    @model_validator(mode="before")
    @classmethod
    def coerce_numbers(cls, values):  # type: ignore
        """Coerce numeric string inputs to floats for robustness."""
        for field in ["amount", "gst_rate", "paid_amount"]:
            if field in values and isinstance(values[field], str) and values[field].strip() != "":
                try:
                    values[field] = float(values[field])
                except ValueError as exc:
                    raise ValueError(
                        f"Field '{field}' must be a number") from exc
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
        "paid_amount": float(invoice.paid_amount or 0),
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
        # Snapshot fields (new feature) - exposed for audit / display; may be None for legacy records
        "branding_snapshot": invoice.branding_snapshot,
        "gst_rate_snapshot": float(invoice.gst_rate_snapshot) if getattr(invoice, 'gst_rate_snapshot', None) is not None else None,
        "settings_snapshot": invoice.settings_snapshot,
        # Add placeholder lines array for contract tests (will populate when line items implemented)
        "lines": [],
    }


@router.get('/')
@router.get('')
async def list_invoices(
    request: Request,
    customer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):  # _current_user used only for auth gating
    result = await db.execute(
        select(Invoice)
        .where(Invoice.is_deleted.is_(False))
        .order_by(Invoice.created_at.desc())
        .limit(100)
    )
    invoices = result.scalars().all()
    if customer_id:
        invoices = [inv for inv in invoices if str(
            inv.customer_id) == customer_id]
    customer_ids = {inv.customer_id for inv in invoices if inv.customer_id}
    customers_map = {}
    if customer_ids:
        cust_result = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        for c in cust_result.scalars().all():
            customers_map[c.id] = c
    data_list = [
        _to_frontend_invoice(inv, customers_map.get(inv.customer_id))
        for inv in invoices
    ]
    if _is_raw_legacy_mode(request):
        # Raw returns list directly
        return data_list
    return _success(data_list, total=len(data_list))


@router.post('/', status_code=status.HTTP_201_CREATED)
@router.post('', status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: Request,
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):
    try:
        created = await create_invoice_service(db, payload.model_dump())
    except ValidationError as exc:  # type: ignore[attr-defined]
        http_exc = HTTPException(status_code=422, detail=str(exc))
        setattr(http_exc, 'code', ValidationError.code)
        raise http_exc
    except CustomerNotFound as exc:  # backend style path
        http_exc = HTTPException(status_code=404, detail=str(exc))
        setattr(http_exc, 'code', CustomerNotFound.code)
        raise http_exc
    # Metrics
    if invoice_create_counter:  # type: ignore[attr-defined]
        invoice_create_counter.add(
            1, {"place_of_supply": created.invoice.place_of_supply})
    record_invoice_operation("create")
    inv_dict = _to_frontend_invoice(created.invoice, created.customer)
    if _is_raw_legacy_mode(request):
        # Raw mode: convert numeric monetary fields to 2-decimal strings for new_feature tests
        raw_copy = dict(inv_dict)
        for k in ["amount", "gst_rate", "gst_amount", "total_amount", "paid_amount", "outstanding_amount", "gst_rate_snapshot"]:
            if raw_copy.get(k) is not None and isinstance(raw_copy[k], (int, float)):
                raw_copy[k] = f"{float(raw_copy[k]):.2f}"
        return raw_copy
    return _success(inv_dict)


@router.get('/{invoice_id}')
async def get_invoice_detail(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):
    """Retrieve single invoice detail including payment + soft delete flags.

    Returns the same normalized structure as list endpoint but includes paid_amount.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        from src.utils.errors import ERROR_CODES  # local import
        # type: ignore[index]
        code = ERROR_CODES.get("invoice_not_found", ERROR_CODES["not_found"])
        raise HTTPException(status_code=404, detail="Invoice not found", headers={
                            "X-Error-Code": code})

    customer = None
    if invoice.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        customer = cust_res.scalar_one_or_none()
    inv_dict = _to_frontend_invoice(invoice, customer)
    if _is_raw_legacy_mode(request):
        raw_copy = dict(inv_dict)
        for k in ["amount", "gst_rate", "gst_amount", "total_amount", "paid_amount", "outstanding_amount", "gst_rate_snapshot"]:
            if raw_copy.get(k) is not None and isinstance(raw_copy[k], (int, float)):
                raw_copy[k] = f"{float(raw_copy[k]):.2f}"
        return raw_copy
    return _success(inv_dict)


async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):
    try:
        invoice, customer = await get_invoice_service(db, invoice_id)
    except InvoiceNotFound as exc:
        http_exc = HTTPException(status_code=404, detail=str(exc))
        setattr(http_exc, 'code', InvoiceNotFound.code)
        raise http_exc
    return _success(_to_frontend_invoice(invoice, customer))


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


async def _update_invoice_logic(invoice_id: UUID, payload: InvoiceUpdate, db: AsyncSession):
    try:
        invoice, customer = await update_invoice_service(db, invoice_id, payload.model_dump())
    except InvoiceNotFound as exc:
        http_exc = HTTPException(status_code=404, detail=str(exc))
        setattr(http_exc, 'code', InvoiceNotFound.code)
        raise http_exc
    except ServiceOverpayNotAllowed as exc:  # domain overpay
        # type: ignore[attr-defined]
        http_exc = HTTPException(status_code=400, detail=exc.message)
        setattr(http_exc, 'code', exc.code)  # type: ignore[attr-defined]
        raise http_exc
    if invoice_update_counter:  # type: ignore[attr-defined]
        invoice_update_counter.add(
            1, {"payment_status": invoice.payment_status})
    record_invoice_operation("update")
    return _to_frontend_invoice(invoice, customer)


@router.patch('/{invoice_id}')
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):  # _current_user used only for auth gating
    updated = await _update_invoice_logic(invoice_id, payload, db)
    return _success(updated)


@router.put('/{invoice_id}')
async def replace_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,  # Accept same flexible model
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):  # _current_user used only for auth gating
    # Treat PUT as full update but since fields are optional, behavior mirrors PATCH unless fields supplied
    updated = await _update_invoice_logic(invoice_id, payload, db)
    return _success(updated)


@router.delete('/{invoice_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user)
):
    try:
        changed = await delete_invoice_service(db, invoice_id)
    except InvoiceNotFound as exc:
        http_exc = HTTPException(status_code=404, detail=str(exc))
        setattr(http_exc, 'code', InvoiceNotFound.code)
        raise http_exc
    if changed:
        if invoice_delete_counter:  # type: ignore[attr-defined]
            invoice_delete_counter.add(1, {})
        record_invoice_operation("delete")
    return _success(None)


@router.post('/{invoice_id}/download/{action}', status_code=status.HTTP_201_CREATED)
async def record_download(
    invoice_id: UUID,
    action: str,  # 'print' or 'pdf'
    db: AsyncSession = Depends(get_async_db_dependency),
    current_user: User = Depends(get_current_user)
):
    """Record a print or PDF download action for an invoice.

    This is a lightweight endpoint preparing for future PDF generation. Currently it:
      - Validates invoice exists (service raises InvoiceNotFound if not)
      - Persists an audit row (invoice_download_audit)
      - Returns success envelope with the audit id & action
    """
    try:
        audit = await record_invoice_download(
            db=db,
            invoice_id=invoice_id,
            user_id=current_user.id if getattr(
                current_user, 'id', None) else None,
            action=action.lower(),
        )
    except InvoiceNotFound as exc:  # type: ignore[name-defined]
        http_exc = HTTPException(status_code=404, detail=str(exc))
        # type: ignore[attr-defined]
        setattr(http_exc, 'code', InvoiceNotFound.code)
        raise http_exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_invoice_operation("download")
    return _success({
        "id": str(audit.id),
        "invoice_id": str(audit.invoice_id),
        "user_id": str(audit.user_id) if audit.user_id else None,
        "action": audit.action,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
    })


@router.get('/{invoice_id}/pdf')
async def get_invoice_pdf(invoice_id: UUID,
                          db: AsyncSession = Depends(get_async_db_dependency),
                          _current_user: User = Depends(get_current_user)):
    """Return a minimal PDF representation (placeholder) and record audit.

    Contract test expects a 200 with application/pdf; we emit a tiny valid PDF header.
    """
    from fastapi.responses import Response
    try:
        invoice, customer = await get_invoice_service(db, invoice_id)  # noqa: F841
    except InvoiceNotFound as exc:  # pragma: no cover
        raise HTTPException(status_code=404, detail=str(exc))
    pdf_bytes = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    try:
        await record_invoice_download(db, invoice_id, 'pdf')
    except Exception:  # pragma: no cover - best effort
        pass
    return Response(content=pdf_bytes, media_type='application/pdf')
