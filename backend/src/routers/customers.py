from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List

from ..config.database import get_async_db_dependency
from ..services import customer_service
from .auth import get_current_user, User
from src.utils.api_shapes import success as _success, is_raw_mode  # noqa: F401
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    _request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        _optional_bearer),
    db: AsyncSession = Depends(get_async_db_dependency),
):
    """Optional auth wrapper returning None when no credentials provided.

    Avoids default HTTPBearer 403 behavior so we can emit contract-specific 401 envelope.
    When credentials exist we delegate to the standard get_current_user, ensuring we pass
    concrete dependencies so its internal DB lookups work (and FAST_TESTS shortcut still applies).
    """
    if not credentials:  # no Authorization header -> treat as unauthenticated
        return None
    # Delegate with explicit parameters (bypassing Depends defaults)
    # type: ignore[arg-type]
    return await get_current_user(credentials=credentials, db=db)

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("")
async def list_customers(
    request: Request,
    search: str | None = None,
    customer_type: str | None = None,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User | None = Depends(
        get_current_user_optional),  # optional to craft 401 ourselves
):
    # Contract requirement: missing auth header -> 401 with standardized envelope
    if not request.headers.get("Authorization"):
        return JSONResponse(status_code=401, content={
            "status": "error",
            "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}
        })
    customers: List[Dict[str, Any]] = await customer_service.list_customers(
        db,
        search=search,
        customer_type=customer_type,
    )
    pagination = {
        "page": 1,
        "page_size": len(customers),
        "total_items": len(customers),
        "total_pages": 1,
        "has_next": False,
        "has_previous": False,
    }
    if is_raw_mode(request):
        # Raw mode returns plain list (original new_feature tests expect a list only)
        return customers
    return _success({"customers": customers, "pagination": pagination})


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(
    request: Request,  # noqa: ARG001 - part of uniform handler signature (raw mode check)
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user),
):
    if not payload.get("name"):
        err = {"status": "error", "error": {
            "code": "VALIDATION_ERROR", "message": "'name' required"}}
        return JSONResponse(status_code=422, content=err)
    # Rudimentary GST validation (simple length/pattern placeholder) if provided
    gst_number = payload.get("gst_number")
    if gst_number:
        import re
        if not re.match(r"^[0-9A-Z]{15}$", gst_number):
            err = {"status": "error", "error": {
                "code": "VALIDATION_ERROR", "message": "Invalid GST number format"}}
            return JSONResponse(status_code=422, content=err)
    try:
        cust = await customer_service.create_customer(db, payload)
    except ValueError as ve:  # validation from model (phone, gst)
        err = {"status": "error", "error": {
            "code": "VALIDATION_ERROR", "message": str(ve)}}
        return JSONResponse(status_code=422, content=err)
    if is_raw_mode(request):
        # Raw mode returns flattened customer dict with duplicate_warning at top level
        return cust | {"duplicate_warning": cust.get("duplicate_warning", False)}
    return _success({"customer": cust})


@router.get("/{customer_id}")
async def get_customer(
    request: Request,  # noqa: ARG001 - kept for possible raw mode / future auditing
    customer_id: str,
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user),
):
    c = await customer_service.get_customer(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail={
                            "code": "NOT_FOUND", "message": "Customer not found"})
    if is_raw_mode(request):
        return c
    return _success({"customer": c})


@router.patch("/{customer_id}")
async def update_customer(
    request: Request,  # noqa: ARG001 - consistent signature
    customer_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db_dependency),
    _current_user: User = Depends(get_current_user),
):
    try:
        c = await customer_service.update_customer(db, customer_id, payload)
    except ValueError as ve:
        err = {"status": "error", "error": {
            "code": "VALIDATION_ERROR", "message": str(ve)}}
        return JSONResponse(status_code=422, content=err)
    if not c:
        raise HTTPException(status_code=404, detail={
                            "code": "NOT_FOUND", "message": "Customer not found"})
    if is_raw_mode(request):
        return c
    return _success({"customer": c})
