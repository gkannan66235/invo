"""Inventory service layer (Phase E - T019).

Provides CRUD operations and domain validation for InventoryItem.

Responsibilities:
- Create inventory item with uniqueness enforcement on product_code.
- List with filters (category, search, low_stock) + pagination stub.
- Update allowed fields (description, gst_rate, current_stock, minimum_stock_level, purchase_price, selling_price, category, is_active).
- (Future) Deactivate / soft delete semantics.

Assumptions:
- InventoryItem model already migrated (see models.database.InventoryItem).
- For now, no soft delete column; is_active used for activation state.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from uuid import UUID

from src.models.database import InventoryItem  # type: ignore
from sqlalchemy.exc import IntegrityError

ALLOWED_UPDATE_FIELDS = {
    "description",
    "gst_rate",
    "current_stock",
    "minimum_stock_level",
    "purchase_price",
    "selling_price",
    "category",
    "is_active",
}


class InventoryNotFound(Exception):
    pass


class InventoryValidationError(Exception):
    pass


def _serialize(item: InventoryItem) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "product_code": item.product_code,
        "description": item.description,
        "hsn_code": item.hsn_code,
        "gst_rate": float(item.gst_rate or 0),
        "current_stock": item.current_stock,
        "minimum_stock_level": item.minimum_stock_level,
        "maximum_stock_level": item.maximum_stock_level,
        "reorder_quantity": item.reorder_quantity,
        "purchase_price": float(item.purchase_price or 0),
        "selling_price": float(item.selling_price or 0),
        "mrp": float(item.mrp or 0) if item.mrp is not None else None,
        "category": item.category,
        "brand": item.brand,
        "model": item.model,
        "specifications": item.specifications or {},
        "supplier_id": str(item.supplier_id) if item.supplier_id else None,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "low_stock": item.current_stock <= item.minimum_stock_level,
    }


async def create_inventory_item(db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    required = ["product_code", "description", "hsn_code",
                "gst_rate", "selling_price", "category"]
    missing = [f for f in required if not payload.get(
        f) and payload.get(f) != 0]
    if missing:
        raise InventoryValidationError(
            f"Missing required fields: {', '.join(missing)}")
    try:
        item = InventoryItem(
            product_code=payload["product_code"],
            description=payload["description"],
            hsn_code=payload["hsn_code"],
            gst_rate=payload.get("gst_rate", 0),
            current_stock=payload.get("current_stock", 0),
            minimum_stock_level=payload.get("minimum_stock_level", 0),
            purchase_price=payload.get("purchase_price", 0),
            selling_price=payload.get("selling_price", 0),
            category=payload.get("category"),
            brand=payload.get("brand"),
            model=payload.get("model"),
            specifications=payload.get("specifications") or {},
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return _serialize(item)
    except IntegrityError as ie:  # duplicate product_code
        await db.rollback()
        # Idempotent create: fetch existing and return
        existing_q = await db.execute(
            select(InventoryItem).where(InventoryItem.product_code ==
                                        # type: ignore[arg-type]
                                        payload["product_code"])
        )
        existing = existing_q.scalar_one_or_none()
        if existing:
            return _serialize(existing)
        raise InventoryValidationError("Product code already exists") from ie


async def list_inventory_items(
    db: AsyncSession,
    *,
    category: Optional[str] = None,
    search: Optional[str] = None,
    low_stock: bool = False,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    if limit < 1:
        limit = 1
    if limit > 1000:
        limit = 1000
    stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True))
    if category:
        stmt = stmt.where(InventoryItem.category == category)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(or_(func.lower(InventoryItem.description).like(
            like), func.lower(InventoryItem.product_code).like(like)))
    if low_stock:
        stmt = stmt.where(InventoryItem.current_stock <=
                          InventoryItem.minimum_stock_level)
    stmt = stmt.order_by(InventoryItem.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize(r) for r in rows]


async def update_inventory_item(db: AsyncSession, item_id: UUID | str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        iid = UUID(str(item_id))
    except Exception as exc:  # noqa: BLE001
        raise InventoryNotFound("Invalid inventory item id") from exc
    res = await db.execute(select(InventoryItem).where(InventoryItem.id == iid))
    item = res.scalar_one_or_none()
    if not item:
        raise InventoryNotFound("Inventory item not found")
    for field, value in payload.items():
        if field in ALLOWED_UPDATE_FIELDS and value is not None:
            setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return _serialize(item)


__all__ = [
    "create_inventory_item",
    "list_inventory_items",
    "update_inventory_item",
    "InventoryValidationError",
    "InventoryNotFound",
]
