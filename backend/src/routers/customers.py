from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from ..config.database import get_async_db_dependency
from ..services import customer_service

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("", response_model=list[dict])
async def list_customers(db: AsyncSession = Depends(get_async_db_dependency)):
    return await customer_service.list_customers(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(payload: Dict[str, Any], db: AsyncSession = Depends(get_async_db_dependency)):
    # Basic required field check
    if not payload.get("name"):
        raise HTTPException(status_code=422, detail="name required")
    customer_dict = await customer_service.create_customer(db, payload)
    # For contract tests expecting duplicate_warning at top-level response, surface it directly
    if "duplicate_warning" in customer_dict:
        # Return flattened response (not wrapped in {data:{}}) to align with newer contract tests
        return customer_dict
    return customer_dict


@router.get("/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_async_db_dependency)):
    c = await customer_service.get_customer(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


@router.patch("/{customer_id}")
async def update_customer(customer_id: str, payload: Dict[str, Any], db: AsyncSession = Depends(get_async_db_dependency)):
    c = await customer_service.update_customer(db, customer_id, payload)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c
