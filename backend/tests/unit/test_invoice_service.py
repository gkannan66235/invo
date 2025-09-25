import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.invoice_service import (  # type: ignore
    create_invoice_service,
    update_invoice_service,
    delete_invoice_service,
    get_invoice_service,
    InvoiceNotFound,
    ValidationError,
)


@pytest.mark.asyncio
async def test_create_invoice_service_basic(db_session: AsyncSession):
    payload = {
        "customer_name": "SvcUser",
        "customer_phone": "9123400000",
        "amount": 100,
        "service_description": "Test desc",
        # omit gst_rate to trigger default
    }
    created = await create_invoice_service(db_session, payload)
    assert created.invoice.id is not None
    assert created.invoice.subtotal == 100
    assert created.invoice.gst_amount >= 0
    assert created.customer is not None


@pytest.mark.asyncio
async def test_create_invoice_service_validation(db_session: AsyncSession):
    with pytest.raises(ValidationError):
        await create_invoice_service(db_session, {"customer_name": "X"})  # missing phone & amount


@pytest.mark.asyncio
async def test_update_invoice_service_payment_flow(db_session: AsyncSession):
    # create first
    created = await create_invoice_service(db_session, {
        "customer_name": "PayFlow",
        "customer_phone": "9123400001",
        "amount": 50,
    })
    inv_id = created.invoice.id
    # partial
    inv, _ = await update_invoice_service(db_session, inv_id, {"paid_amount": 10})
    assert inv.payment_status.lower() == "partial"
    # full
    inv2, _ = await update_invoice_service(db_session, inv_id, {"paid_amount": inv.total_amount})
    assert inv2.payment_status.lower() == "paid"
    # downgrade
    inv3, _ = await update_invoice_service(db_session, inv_id, {"paid_amount": 0})
    assert inv3.payment_status.lower() == "pending"


@pytest.mark.asyncio
async def test_delete_invoice_service_soft(db_session: AsyncSession):
    created = await create_invoice_service(db_session, {
        "customer_name": "DelUser",
        "customer_phone": "9123400002",
        "amount": 70,
    })
    inv_id = created.invoice.id
    changed = await delete_invoice_service(db_session, inv_id)
    assert changed is True
    # second call should be idempotent
    changed2 = await delete_invoice_service(db_session, inv_id)
    assert changed2 is False


@pytest.mark.asyncio
async def test_get_invoice_service_not_found(db_session: AsyncSession):
    import uuid
    with pytest.raises(InvoiceNotFound):
        await get_invoice_service(db_session, uuid.uuid4())
