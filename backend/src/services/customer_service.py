from typing import Any, Dict, Optional
from sqlalchemy import select
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.database import Customer  # type: ignore

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
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    duplicate_warning = False
    if customer.mobile_normalized:
        # Fetch up to 2 active customers sharing this mobile (including self)
        dup_rows = await db.execute(
            select(Customer.id).where(
                Customer.mobile_normalized == customer.mobile_normalized,
                Customer.is_active.is_(True),
            ).limit(2)
        )
        ids = [r for r, in dup_rows.all()]
        if len(ids) > 1:
            duplicate_warning = True
    return _serialize_customer(customer, duplicate_warning=duplicate_warning)


async def list_customers(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    customer_type: Optional[str] = None,
) -> list[Dict[str, Any]]:
    """List customers with optional search and type filter.

    search: substring match on name or phone (simple ILIKE/LIKE fallback for SQLite)
    customer_type: exact filter on customer_type
    """
    stmt = select(Customer).order_by(Customer.created_at.desc()).limit(500)
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import or_, func as f2  # localized import for readability
        stmt = stmt.where(or_(f2.lower(Customer.name).like(
            like), f2.lower(Customer.phone).like(like)))
    if customer_type:
        stmt = stmt.where(Customer.customer_type == customer_type)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    # Compute duplicate groups by mobile_normalized (active customers only)
    from collections import Counter
    mobiles = [c.mobile_normalized for c in rows if c.mobile_normalized]
    counts = Counter(mobiles)
    serialized: list[Dict[str, Any]] = []
    for c in rows:
        dup_flag = False
        if c.mobile_normalized and counts.get(c.mobile_normalized, 0) > 1 and c.is_active:
            dup_flag = True
        serialized.append(_serialize_customer(c, duplicate_warning=dup_flag))
    return serialized


async def get_customer(db: AsyncSession, customer_id: str) -> Optional[Dict[str, Any]]:
    # Ensure we pass a proper UUID object when model column uses as_uuid=True
    try:
        cust_uuid = UUID(customer_id)
    except ValueError:
        return None
    res = await db.execute(select(Customer).where(Customer.id == cust_uuid))
    obj = res.scalar_one_or_none()
    if not obj:
        return None
    # Recompute duplicate flag on demand (consistent with list/create semantics)
    dup_flag = False
    if obj.mobile_normalized:
        dup_rows = await db.execute(
            select(Customer.id).where(
                Customer.mobile_normalized == obj.mobile_normalized,
                Customer.is_active.is_(True)
            ).limit(2)
        )
        ids = [r for (r,) in dup_rows.all()]
        if len(ids) > 1:
            dup_flag = True
    return _serialize_customer(obj, duplicate_warning=dup_flag)


async def update_customer(db: AsyncSession, customer_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        # Invalid UUID format
        return None
    res = await db.execute(select(Customer).where(Customer.id == customer_uuid))
    customer = res.scalar_one_or_none()
    if not customer:
        return None

    for field in ("name", "phone", "email", "is_active"):
        if field in payload and payload[field] is not None:
            setattr(customer, field, payload[field])

    # Trigger validators by reassigning phone (if present)
    if "phone" in payload:
        _ = customer.phone  # access property for clarity

    # Flush pending changes to ensure normalized mobile reflects update before duplicate check
    await db.flush()
    duplicate_warning = False
    if customer.mobile_normalized:
        dup_rows = await db.execute(
            select(Customer.id).where(
                Customer.mobile_normalized == customer.mobile_normalized,
                Customer.is_active.is_(True)
            ).limit(2)
        )
        ids = [rid for (rid,) in dup_rows.all()]
        if len(ids) > 1:
            duplicate_warning = True

    await db.commit()
    await db.refresh(customer)

    return _serialize_customer(customer, duplicate_warning=duplicate_warning)


def _serialize_customer(customer: Customer, duplicate_warning: bool = False) -> Dict[str, Any]:
    """Rich serializer matching broader contract expectations.

    Includes legacy/new_feature fields plus full contract fields (gst_number, address, type, credit/outstanding).
    Provides flattened address accessors (city/state/pin_code) even if None.
    """
    address = customer.address or {}
    # Ensure nested address keys exist
    for k in ("street", "area", "landmark"):
        address.setdefault(k, None)
    data: Dict[str, Any] = {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "mobile_normalized": customer.mobile_normalized,
        "duplicate_warning": duplicate_warning,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if getattr(customer, "updated_at", None) else None,
        # Contract oriented fields
        "gst_number": customer.gst_number,
        "customer_type": customer.customer_type,
        "credit_limit": float(customer.credit_limit or 0),
        "outstanding_amount": float(customer.outstanding_amount or 0),
        "address": address,
        # Flattened projections (may be None if not stored)
        "city": address.get("city"),
        "state": address.get("state"),
        "pin_code": address.get("pin_code") or address.get("pincode") or address.get("postal_code"),
    }
    return data
