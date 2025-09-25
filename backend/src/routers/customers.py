from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from ..config.database import get_async_db
from ..services import customer_service

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("", response_model=list[dict])
async def list_customers(db: AsyncSession = Depends(get_async_db)):
    return await customer_service.list_customers(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(payload: Dict[str, Any], db: AsyncSession = Depends(get_async_db)):
    # Basic required field check
    if not payload.get("name"):
        raise HTTPException(status_code=422, detail="name required")
    return await customer_service.create_customer(db, payload)


@router.get("/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_async_db)):
    c = await customer_service.get_customer(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


@router.patch("/{customer_id}")
async def update_customer(customer_id: str, payload: Dict[str, Any], db: AsyncSession = Depends(get_async_db)):
    c = await customer_service.update_customer(db, customer_id, payload)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c
