from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.database import Customer

# Customer service (T018) minimal implementation for initial sprint.
# Responsibilities:
# - Create customer with mobile normalization (handled by model validator)
# - Duplicate warning detection (same mobile_normalized existing & active)
# - List customers
# - Get / Update customer


def _normalize_mobile(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    import re
    digits = re.sub(r"[^0-9]", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits if len(digits) == 10 else None


async def create_customer(db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = payload.get("name")
    phone = payload.get("phone")
    email = payload.get("email")

    customer = Customer(name=name, phone=phone, email=email)

    # Duplicate detection
    mobile_norm = customer.mobile_normalized or _normalize_mobile(phone)
    duplicate_warning = False
    if mobile_norm:
        q = await db.execute(
            select(Customer.id).where(
                Customer.mobile_normalized == mobile_norm,
                Customer.is_active.is_(True)
            ).limit(1)
        )
        existing = q.scalar_one_or_none()
        # If we found an existing row AND it's not the same (new object, so different)
        if existing is not None:
            duplicate_warning = True

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return _serialize_customer(customer, duplicate_warning=duplicate_warning)


async def list_customers(db: AsyncSession) -> list[Dict[str, Any]]:
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()).limit(200))
    rows = result.scalars().all()
    return [_serialize_customer(c) for c in rows]


async def get_customer(db: AsyncSession, customer_id: str) -> Optional[Dict[str, Any]]:
    res = await db.execute(select(Customer).where(Customer.id == customer_id))
    obj = res.scalar_one_or_none()
    if not obj:
        return None
    return _serialize_customer(obj)


async def update_customer(db: AsyncSession, customer_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    res = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = res.scalar_one_or_none()
    if not customer:
        return None

    for field in ("name", "phone", "email", "is_active"):
        if field in payload and payload[field] is not None:
            setattr(customer, field, payload[field])

    # Trigger validators by reassigning phone (if present)
    if "phone" in payload:
        _ = customer.phone  # access property for clarity

    duplicate_warning = False
    if customer.mobile_normalized:
        q = await db.execute(
            select(Customer.id).where(
                Customer.mobile_normalized == customer.mobile_normalized,
                Customer.id != customer.id,
                Customer.is_active.is_(True)
            ).limit(1)
        )
        if q.scalar_one_or_none() is not None:
            duplicate_warning = True

    await db.commit()
    await db.refresh(customer)

    return _serialize_customer(customer, duplicate_warning=duplicate_warning)


def _serialize_customer(customer: Customer, duplicate_warning: bool = False) -> Dict[str, Any]:
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "mobile_normalized": customer.mobile_normalized,
        "duplicate_warning": duplicate_warning,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }
