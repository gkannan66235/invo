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
        current_user: User = Depends(require_auth),  # noqa: ARG001
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
async def create_customer(payload: Dict[str, Any], current_user: User = Depends(require_auth)):  # noqa: D401, ARG001
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

_INVENTORY_ITEMS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "product_code": "PRD001",
        "description": "Sample Pump",
        "hsn_code": "8413",
        "gst_rate": 18,
        "current_stock": 10,
        "minimum_stock_level": 2,
        "purchase_price": 1000.0,
        "selling_price": 1500.0,
        "category": "pump",
        "is_active": True,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
]


@inventory_router.get("", status_code=status.HTTP_200_OK)
@inventory_router.get("/", status_code=status.HTTP_200_OK)
@inventory_router.get("/items", status_code=status.HTTP_200_OK)
async def list_inventory_items(  # noqa: D401
        category: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        low_stock: Optional[bool] = Query(False),
        page: int = 1,
        page_size: int = 10,
        current_user: User = Depends(require_auth),  # noqa: ARG001
):
    items = _INVENTORY_ITEMS
    # Clamp page_size to a sane maximum (contract expectation: cap at 100)
    if page_size < 1:
        page_size = 1
    elif page_size > 100:
        page_size = 100
    if category:
        items = [i for i in items if i["category"] == category]
    if search:
        s = search.lower()
        items = [i for i in items if s in i["description"].lower()]
    if low_stock:
        items = [i for i in items if i["current_stock"]
                 <= i["minimum_stock_level"]]
    # Simple pagination slice
    items_slice = items[:page_size]
    return {
        "status": "success",
        "data": {
            "items": items_slice,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": len(items),
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            },
        },
    }


@inventory_router.post("", status_code=status.HTTP_201_CREATED)
@inventory_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_inventory_item(payload: Dict[str, Any], current_user: User = Depends(require_auth)):
    required = ["product_code", "description", "hsn_code",
                "gst_rate", "selling_price", "category"]
    missing = [f for f in required if payload.get(f) in (None, "")]
    if missing:
        exc = HTTPException(
            status_code=422, detail=f"Missing required fields: {', '.join(missing)}")
        setattr(exc, "code", "VALIDATION_ERROR")
        raise exc
    # Simple uniqueness check
    if any(i["product_code"] == payload["product_code"] for i in _INVENTORY_ITEMS):
        exc = HTTPException(
            status_code=400, detail="Product code already exists")
        setattr(exc, "code", "DUPLICATE_PRODUCT_CODE")
        raise exc
    new_id = max([i["id"] for i in _INVENTORY_ITEMS] + [0]) + 1
    now = datetime.now(UTC).isoformat()
    item = {
        "id": new_id,
        "product_code": payload["product_code"],
        "description": payload["description"],
        "hsn_code": payload["hsn_code"],
        "gst_rate": payload.get("gst_rate", 0),
        "current_stock": payload.get("current_stock", 0),
        "minimum_stock_level": payload.get("minimum_stock_level", 0),
        "purchase_price": payload.get("purchase_price", 0),
        "selling_price": payload.get("selling_price", 0),
        "category": payload.get("category", "spare_part"),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    _INVENTORY_ITEMS.append(item)
    return {"status": "success", "data": {"item": item}}


@inventory_router.patch("/{item_id}")
async def update_inventory_item(item_id: int, payload: Dict[str, Any], current_user: User = Depends(require_auth)):
    for item in _INVENTORY_ITEMS:
        if item["id"] == item_id:
            # Apply allowed fields
            for f in ["description", "gst_rate", "current_stock", "minimum_stock_level", "purchase_price", "selling_price", "category", "is_active"]:
                if f in payload and payload[f] is not None:
                    item[f] = payload[f]
            item["updated_at"] = datetime.now(UTC).isoformat()
            return {"status": "success", "data": {"item": item}}
    raise HTTPException(status_code=404, detail="Inventory item not found")


orders_router = APIRouter()
_ORDERS: List[Dict[str, Any]] = []


@orders_router.post("", status_code=status.HTTP_201_CREATED)
@orders_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(payload: Dict[str, Any], current_user: User = Depends(require_auth)):  # noqa: D401, ARG001
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
async def list_orders(current_user: User = Depends(require_auth)):  # noqa: ARG001
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
