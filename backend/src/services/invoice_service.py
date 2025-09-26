"""Invoice domain service layer.

Implements core create/update/delete logic previously embedded in the router.
Tasks: T037 (refactor duplication) & supports T038 (service unit tests).

Design goals:
 - Keep all DB persistence + business rules centralized.
 - Provide pure-ish functions where feasible to allow isolated unit tests with mocked session.
 - Do not leak FastAPI/HTTP concerns (no HTTPException here). Raise domain exceptions instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, UTC
import os
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import (
    Invoice,
    Customer,
    PaymentStatus,
    GSTTreatment,
    InvoiceDownloadAudit,
)
from sqlalchemy.exc import IntegrityError
from src.utils.errors import OverpayNotAllowed, ERROR_CODES
from src.config.settings import get_default_gst_rate


# ----------------------------- Domain Exceptions ----------------------------- #


class InvoiceNotFound(Exception):
    """Raised when an invoice cannot be found."""
    code = ERROR_CODES.get("invoice_not_found", ERROR_CODES["not_found"])  # type: ignore[index]


class CustomerNotFound(Exception):
    """Raised when a referenced customer id does not exist."""
    code = ERROR_CODES["not_found"]  # type: ignore[index]


class ValidationError(Exception):
    """Raised when incoming payload fails basic validation rules."""
    code = ERROR_CODES["validation"]  # type: ignore[index]


# ----------------------------- Helper Data Shapes ---------------------------- #


@dataclass
class CreatedInvoice:
    invoice: Invoice
    customer: Optional[Customer]


async def _generate_invoice_number(db: AsyncSession) -> str:
    """Generate next invoice number atomically using an UPSERT with RETURNING.

    Uses a single INSERT .. ON CONFLICT .. DO UPDATE statement to guarantee
    that only one concurrent transaction increments the per-day counter at a time.
    Works for both PostgreSQL and modern SQLite (>=3.35 with RETURNING support).

    Algorithm:
      INSERT (date_key, last_seq=1) ON CONFLICT(date_key)
      DO UPDATE SET last_seq = last_seq + 1
      RETURNING last_seq

    If the encompassing invoice creation later rolls back, the increment rolls
    back too (no gaps introduced by failed attempts). This eliminates the need
    for a manual SELECT + UPDATE pattern and avoids lost update races.
    """
    now_utc = datetime.now(UTC)
    date_key = now_utc.strftime('%Y%m%d')
    prefix = f"INV-{date_key}-"

    stmt = text(
        """
        INSERT INTO day_invoice_sequences (date_key, last_seq)
        VALUES (:date_key, 1)
        ON CONFLICT(date_key) DO UPDATE SET last_seq = last_seq + 1
        RETURNING last_seq
        """
    )

    # Bounded retries for transient DB errors (e.g. SQLITE_BUSY under heavy contention)
    import asyncio
    for _ in range(10):
        try:
            result = await db.execute(stmt, {"date_key": date_key})
            next_seq = int(result.scalar_one())
            formatted = f"{prefix}{next_seq:04d}"
            if os.getenv("INVOICE_NUM_DEBUG"):
                logging.getLogger("invoice_number").warning(
                    "INVOICE_NUM_DEBUG day_seq date_key=%s issued=%s", date_key, formatted
                )
            return formatted
        except Exception as exc:  # Handle SQLITE_BUSY/locked transiently
            msg = str(exc).lower()
            if "busy" in msg or "locked" in msg:
                await asyncio.sleep(0.005)
                continue
            raise
    raise RuntimeError("Failed to allocate invoice number after retries (atomic upsert)")


def _recompute_amounts(invoice: Invoice):
    base_amount = float(invoice.subtotal)
    rate = float(invoice.gst_rate or 0)
    invoice.gst_amount = round(base_amount * rate / 100, 2)
    invoice.total_amount = round(base_amount + invoice.gst_amount, 2)
    # outstanding_amount is a computed property on the model; no assignment needed


async def create_invoice_service(
    db: AsyncSession,
    payload: Dict[str, Any],
) -> CreatedInvoice:
    """Create an invoice from normalized payload with concurrency-safe numbering.

    Implements optimistic retry on unique constraint collisions for invoice_number.
    Avoids heavy-weight table locks / sequence tables while ensuring FR-005 sequential format.
    """
    # Preprocess / resolve customer first (outside retry loop).
    customer: Optional[Customer] = None
    if not payload.get("customer_id"):
        if not (payload.get("customer_name") and payload.get("customer_phone") and payload.get("amount") is not None):
            raise ValidationError("Missing required customer or amount fields")
        existing = await db.execute(
            select(Customer).where(
                Customer.name == payload["customer_name"],
                Customer.phone == payload["customer_phone"],
            )
        )
        customer = existing.scalar_one_or_none()
        if not customer:
            customer = Customer(
                name=payload["customer_name"],
                phone=payload["customer_phone"],
                email=payload.get("customer_email"),
                customer_type="individual",
                is_active=True,
                address={},
            )
            db.add(customer)
            await db.flush()  # obtain id
        customer_id = customer.id
        subtotal = float(payload["amount"])  # validated upstream
        if payload.get("gst_rate") is None:
            gst_rate = float(get_default_gst_rate())
        else:
            gst_rate = float(payload.get("gst_rate") or 0)
        gst_amount = round(subtotal * (gst_rate or 0) / 100, 2)
        total_amount = round(subtotal + gst_amount, 2)
        place_of_supply = payload.get("place_of_supply") or "KA"
        notes = payload.get("service_description") or payload.get("notes")
    else:
        customer_id = payload["customer_id"]
        cust_res = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = cust_res.scalar_one_or_none()
        if not customer:
            raise CustomerNotFound("Customer not found")
        subtotal = float(payload.get("subtotal") or 0)
        gst_amount = float(payload.get("gst_amount") or 0)
        total_amount = float(payload.get("total_amount")
                             or (subtotal + gst_amount))
        place_of_supply = payload.get("place_of_supply") or "KA"
        notes = payload.get("notes")
        gst_rate = float(payload.get("gst_rate") or 0.0)

    # Worst-case concurrent creation: each loser of unique constraint race will retry
    # at most once per successfully committed invoice preceding it. For N parallel
    # creators, the final invoice could require N attempts. Choose a generous cap
    # (64) to accommodate bursts while preventing infinite loops on persistent faults.
    MAX_RETRIES = 64
    last_err: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            invoice_number = await _generate_invoice_number(db)
            invoice = Invoice(
                id=uuid4(),
                invoice_number=invoice_number,
                customer_id=customer_id,
                subtotal=subtotal,
                discount_amount=payload.get("discount_amount") or 0,
                gst_amount=gst_amount,
                total_amount=total_amount,
                paid_amount=0,
                gst_rate=gst_rate,
                service_type=payload.get("service_type"),
                place_of_supply=place_of_supply,
                gst_treatment=payload.get(
                    "gst_treatment") or GSTTreatment.TAXABLE.value,
                reverse_charge=payload.get("reverse_charge") or False,
                due_date=payload.get("due_date"),
                notes=notes,
                terms_and_conditions=payload.get("terms_and_conditions"),
                payment_status=PaymentStatus.PENDING.value,
                branding_snapshot={"currency": "INR"},
                gst_rate_snapshot=gst_rate,
                settings_snapshot={"default_gst_rate": get_default_gst_rate()},
            )
            db.add(invoice)
            await db.commit()
            await db.refresh(invoice)
            return CreatedInvoice(invoice=invoice, customer=customer)
        except IntegrityError as ie:  # likely duplicate invoice_number under race
            await db.rollback()
            last_err = ie
            if attempt == MAX_RETRIES:
                raise ie  # bubble up after exhausting retries
            # continue loop to regenerate with updated count
        except Exception as e:  # noqa: BLE001
            await db.rollback()
            raise e
    if last_err:  # defensive: should not reach due to return/raise inside loop
        raise last_err
    raise RuntimeError(
        "Failed to create invoice after retries (unexpected fallthrough)")


async def get_invoice_service(db: AsyncSession, invoice_id: UUID) -> Tuple[Invoice, Optional[Customer]]:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise InvoiceNotFound("Invoice not found")
    customer = None
    if invoice.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        customer = cust_res.scalar_one_or_none()
    return invoice, customer


def _apply_update(invoice: Invoice, payload: Dict[str, Any]):
    if payload.get("service_description") is not None:
        invoice.notes = payload.get("service_description")
    if payload.get("notes") is not None:
        invoice.notes = payload.get("notes")
    if payload.get("terms_and_conditions") is not None:
        invoice.terms_and_conditions = payload.get("terms_and_conditions")
    if payload.get("service_type") is not None:
        invoice.service_type = payload.get("service_type")
    if payload.get("amount") is not None:
        invoice.subtotal = float(payload.get("amount"))
    if payload.get("gst_rate") is not None:
        invoice.gst_rate = float(payload.get("gst_rate"))
    if invoice.gst_rate is None:
        invoice.gst_rate = 0.0
    if payload.get("gst_rate") is not None or payload.get("amount") is not None:
        _recompute_amounts(invoice)
        # If paid_amount not explicitly updated, ensure consistency of payment_status vs new totals
        if payload.get("paid_amount") is None:
            # Clamp overpay scenario introduced by reducing total below existing paid_amount
            if invoice.paid_amount is not None and float(invoice.paid_amount) > float(invoice.total_amount):
                invoice.paid_amount = invoice.total_amount
            paid_val = float(invoice.paid_amount or 0)
            total_val = float(invoice.total_amount)
            if paid_val == 0:
                invoice.payment_status = PaymentStatus.PENDING.value
            elif abs(total_val - paid_val) < 0.0005:
                invoice.payment_status = PaymentStatus.PAID.value
            elif paid_val < total_val:
                invoice.payment_status = PaymentStatus.PARTIAL.value
    # Payments
    if payload.get("paid_amount") is not None:
        paid = float(payload.get("paid_amount"))
        if paid < 0 or paid > float(invoice.total_amount):
            raise OverpayNotAllowed(paid, float(invoice.total_amount))
        invoice.paid_amount = paid
        # Normalize comparison using rounding to 2 decimals to avoid float/Decimal precision mismatch
        total_val = float(invoice.total_amount)
        paid_val = float(invoice.paid_amount or 0)
        # Treat as fully paid if within 0.005 (half cent) after rounding to 2 decimals
        if round(abs(total_val - paid_val), 4) <= 0.0005:
            invoice.paid_amount = total_val  # snap to canonical total
            invoice.payment_status = PaymentStatus.PAID.value
        elif paid_val > 0:
            invoice.payment_status = PaymentStatus.PARTIAL.value
        else:
            invoice.payment_status = PaymentStatus.PENDING.value
    if payload.get("payment_status") is not None:
        invoice.payment_status = payload.get("payment_status")
    if payload.get("status") is not None:
        status_map = str(payload.get("status")).lower()
        if status_map == 'paid':
            invoice.payment_status = PaymentStatus.PAID.value
            invoice.paid_amount = invoice.total_amount
        elif status_map == 'draft':
            invoice.payment_status = PaymentStatus.PENDING.value
        elif status_map == 'sent':
            if invoice.paid_amount == 0:
                invoice.payment_status = PaymentStatus.PENDING.value
        elif status_map == 'cancelled':
            invoice.is_cancelled = True
    # Manually touch updated_at to ensure the timestamp reflects mutation in tests
    # (Database onupdate may not fire in some SQLite memory/fallback modes during tests.)
    # Use already imported datetime + UTC directly (avoid re-import warnings)
    invoice.updated_at = datetime.now(UTC)


async def update_invoice_service(
    db: AsyncSession, invoice_id: UUID, payload: Dict[str, Any]
) -> Tuple[Invoice, Optional[Customer]]:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise InvoiceNotFound("Invoice not found")
    _apply_update(invoice, payload)
    await db.commit()
    await db.refresh(invoice)
    customer = None
    if invoice.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        customer = cust_res.scalar_one_or_none()
    return invoice, customer


async def delete_invoice_service(db: AsyncSession, invoice_id: UUID) -> bool:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise InvoiceNotFound("Invoice not found")
    changed = False
    if not invoice.is_deleted:
        invoice.is_deleted = True
        changed = True
        await db.commit()
        await db.refresh(invoice)
    return changed


async def record_invoice_download(
    db: AsyncSession,
    invoice_id: UUID,
    user_id: Optional[UUID],
    action: str,
) -> InvoiceDownloadAudit:
    """Record an invoice download/print action in the audit log.

    Parameters:
        invoice_id: Target invoice UUID
        user_id: User performing the action (may be None)
        action: 'print' or 'pdf'

    Raises:
        ValueError: if action invalid
        InvoiceNotFound: if invoice doesn't exist
    """
    if action not in {"print", "pdf"}:
        raise ValueError("Invalid action; must be 'print' or 'pdf'")
    result = await db.execute(select(Invoice.id).where(Invoice.id == invoice_id))
    if not result.scalar_one_or_none():
        raise InvoiceNotFound("Invoice not found")
    audit = InvoiceDownloadAudit(
        invoice_id=invoice_id,
        user_id=user_id,
        action=action,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit
