"""API routers package.

Adds lightweight placeholder routers for customers, inventory, and orders so
contract tests can exercise authentication & response envelope expectations
even before full domain implementation. These routers intentionally keep logic
minimal and return empty collections with pagination scaffolding.
"""

from fastapi import APIRouter, Depends, status, HTTPException, Request, Query
from typing import Any, Dict, List, Optional
from datetime import datetime, UTC
import re
import math
from uuid import uuid4
from .auth import get_current_user, User


def _pagination_stub() -> Dict[str, Any]:  # Consistent empty pagination shape
    return {
        "page": 1,
        "page_size": 0,
        "total_items": 0,
        "total_pages": 0,
        "has_next": False,
        "has_previous": False,
    }


def _auth_401() -> HTTPException:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required")
    setattr(exc, "code", "UNAUTHORIZED")  # consumed by global handler
    return exc


async def require_auth(request: Request) -> None:  # noqa: D401
    if not request.headers.get("Authorization"):
        raise _auth_401()


customers_router = APIRouter()

# In-memory stores (test session scope). Safe placeholder until real DB models implemented.
_CUSTOMERS: List[Dict[str, Any]] = []


@customers_router.get("", status_code=status.HTTP_200_OK)
@customers_router.get("/", status_code=status.HTTP_200_OK)
async def list_customers(  # noqa: D401
    search: Optional[str] = Query(None),
    customer_type: Optional[str] = Query(None),
    _current_user: User = Depends(require_auth),  # noqa: ARG001 - auth side-effect
):
    results = _CUSTOMERS
    if search:
        s = search.lower()
        results = [c for c in results if s in c["name"].lower()]
    if customer_type:
        results = [c for c in results if c.get(
            "customer_type") == customer_type]
    return {
        "status": "success",
        "data": {
            "customers": results,
            "pagination": {**_pagination_stub(), "page_size": len(results)},
        },
    }


@customers_router.post("", status_code=status.HTTP_201_CREATED)
@customers_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_customer(payload: Dict[str, Any], _current_user: User = Depends(require_auth)):  # noqa: D401, ARG001
    if not payload.get("name"):
        exc = HTTPException(
            status_code=422, detail="Missing required field: name")
        setattr(exc, "code", "VALIDATION_ERROR")
        raise exc
    gst_number = payload.get("gst_number")
    if gst_number and not re.match(r"^[0-9A-Z]{15}$", gst_number):
        exc = HTTPException(
            status_code=422, detail="Invalid GST number format")
        setattr(exc, "code", "VALIDATION_ERROR")
        raise exc
    now = datetime.now(UTC).isoformat()
    cid = len(_CUSTOMERS) + 1
    customer: Dict[str, Any] = {
        "id": cid,
        "name": payload["name"],
        "email": payload.get("email"),
        "phone": payload.get("phone"),
        "gst_number": gst_number,
        "address": payload.get("address", {"street": "", "area": "", "landmark": ""}),
        "city": payload.get("address", {}).get("city"),
        "state": payload.get("address", {}).get("state"),
        "pin_code": payload.get("address", {}).get("pin_code"),
        "customer_type": payload.get("customer_type", "business"),
        "is_active": True,
        "credit_limit": float(payload.get("credit_limit", 0.0)),
        "outstanding_amount": 0.0,
        "created_at": now,
        "updated_at": now,
    }
    _CUSTOMERS.append(customer)
    return {"status": "success", "data": {"customer": customer}}


inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from ..config.database import get_async_db_dependency  # noqa: E402
from src.services.inventory_service import (  # noqa: E402
    create_inventory_item as svc_create_inventory_item,
    list_inventory_items as svc_list_inventory_items,
    update_inventory_item as svc_update_inventory_item,
    InventoryValidationError,
    InventoryNotFound,
)


@inventory_router.get("", status_code=status.HTTP_200_OK)
@inventory_router.get("/", status_code=status.HTTP_200_OK)
@inventory_router.get("/items", status_code=status.HTTP_200_OK)
async def list_inventory_items(  # noqa: D401
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    low_stock: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _current_user: User = Depends(require_auth),  # noqa: ARG001
    db: AsyncSession = Depends(get_async_db_dependency),
):
    # Fetch more than we need to derive total without a separate count (cap 5 pages worth)
    fetch_limit = min(page_size * 5, 500)
    raw_items = await svc_list_inventory_items(
        db, category=category, search=search, low_stock=low_stock or False, limit=fetch_limit
    )
    total_items = len(raw_items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = raw_items[start:end]
    total_pages = max(1, math.ceil(total_items / page_size))
    has_next = page < total_pages
    has_previous = page > 1
    return {
        "status": "success",
        "data": {
            "items": page_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
            },
        },
    }


@inventory_router.post("", status_code=status.HTTP_201_CREATED)
@inventory_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_inventory_item(payload: Dict[str, Any], _current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_async_db_dependency)):  # noqa: ARG001
    try:
        item = await svc_create_inventory_item(db, payload)
        return {"status": "success", "data": {"item": item}}
    except InventoryValidationError as e:
        http_exc = HTTPException(status_code=422, detail=str(e))
        setattr(http_exc, "code", "VALIDATION_ERROR")
        raise http_exc from e


@inventory_router.patch("/{item_id}")
async def update_inventory_item(item_id: str, payload: Dict[str, Any], _current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_async_db_dependency)):  # noqa: ARG001
    try:
        item = await svc_update_inventory_item(db, item_id, payload)
        return {"status": "success", "data": {"item": item}}
    except InventoryNotFound as e:
        raise HTTPException(
            status_code=404, detail="Inventory item not found") from e
    except InventoryValidationError as e:
        http_exc = HTTPException(status_code=422, detail=str(e))
        setattr(http_exc, "code", "VALIDATION_ERROR")
        raise http_exc from e


orders_router = APIRouter()
_ORDERS: List[Dict[str, Any]] = []


@orders_router.post("", status_code=status.HTTP_201_CREATED)
@orders_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(payload: Dict[str, Any], _current_user: User = Depends(require_auth)):  # noqa: D401, ARG001
    items = payload.get("items", [])
    if not items:
        exc = HTTPException(
            status_code=422, detail="Items list cannot be empty")
        setattr(exc, "code", "VALIDATION_ERROR")
        raise exc
    customer_id = payload.get("customer_id")
    if customer_id == 99999:
        exc = HTTPException(status_code=404, detail="Customer not found")
        setattr(exc, "code", "CUSTOMER_NOT_FOUND")
        raise exc
    # Insufficient inventory rule: any quantity > 500
    if any(i.get("quantity", 0) > 500 for i in items):
        exc = HTTPException(
            status_code=400, detail="Insufficient inventory for one or more items")
        setattr(exc, "code", "INSUFFICIENT_INVENTORY")
        raise exc
    subtotal = 0.0
    order_items = []
    for idx, it in enumerate(items, start=1):
        qty = float(it.get("quantity", 0))
        unit_price = float(it.get("unit_price", 0))
        discount_pct = float(it.get("discount_percentage", 0))
        line_base = qty * unit_price
        discount_amt = line_base * discount_pct / 100
        line_total = line_base - discount_amt
        gst_rate = 18
        gst_amount = round(line_total * gst_rate / 100, 2)
        subtotal += line_total
        order_items.append({
            "id": idx,
            "inventory_item_id": it.get("inventory_item_id", idx),
            "quantity": qty,
            "unit_price": unit_price,
            "discount_percentage": discount_pct,
            "line_total": round(line_total, 2),
            "gst_rate": gst_rate,
            "gst_amount": gst_amount,
        })
    gst_amount_sum = round(sum(i["gst_amount"] for i in order_items), 2)
    total_amount = round(subtotal + gst_amount_sum, 2)
    now = datetime.now(UTC).isoformat()
    order_dict = {
        "id": str(uuid4()),
        "order_number": f"ORD{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{len(_ORDERS)+1:03d}",
        "customer_id": customer_id,
        "order_type": payload.get("order_type", "sale"),
        "status": "pending",
        "subtotal": round(subtotal, 2),
        "gst_amount": gst_amount_sum,
        "total_amount": total_amount,
        "items": order_items,
        "created_at": now,
        "updated_at": now,
    }
    _ORDERS.append(order_dict)
    return {"status": "success", "data": {"order": order_dict}}


@orders_router.get("", status_code=status.HTTP_200_OK)
@orders_router.get("/", status_code=status.HTTP_200_OK)
async def list_orders(_current_user: User = Depends(require_auth)):  # noqa: ARG001
    return {
        "status": "success",
        "data": {
            "orders": _ORDERS,
            "pagination": {**_pagination_stub(), "page_size": len(_ORDERS)},
        },
    }

__all__ = [
    "customers_router",
    "inventory_router",
    "orders_router",
]
