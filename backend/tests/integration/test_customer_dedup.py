import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.models.database import Customer

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_customer_reuse_on_duplicate_invoice(auth_client: AsyncClient, db_session):
    """T014: Creating multiple invoices with same customer name+phone reuses existing customer (no duplicate).

    Steps:
    1. Create first invoice with customer (name+phone+amount)
    2. Create second invoice with same name+phone (different amount)
    3. Assert both invoices reference the same customer_id
    4. Assert only one customer row exists for that (name, phone)
    """
    payload1 = {
        "customer_name": "ReuseUser",
        "customer_phone": "9000011111",
        "service_type": "repair",
        "service_description": "Initial job",
        "amount": 150.0,
        "gst_rate": 18.0,
    }
    r1 = await auth_client.post("/api/v1/invoices/", json=payload1)
    assert r1.status_code == 201, r1.text
    inv1 = r1.json()
    assert inv1["customer_id"], "First invoice missing customer_id"

    payload2 = {
        "customer_name": "ReuseUser",  # same name
        "customer_phone": "9000011111",  # same phone
        "service_type": "repair",
        "service_description": "Follow-up job",
        "amount": 200.0,
        "gst_rate": 18.0,
    }
    r2 = await auth_client.post("/api/v1/invoices/", json=payload2)
    assert r2.status_code == 201, r2.text
    inv2 = r2.json()

    assert inv2["customer_id"] == inv1["customer_id"], "Expected same customer reused, got different IDs"

    # Query DB to ensure only a single customer record exists for that name/phone
    result = await db_session.execute(
        # type: ignore[arg-type]
        select(Customer).where(Customer.name ==
                               payload1["customer_name"], Customer.phone == payload1["customer_phone"])
    )
    customers = result.scalars().all()
    assert len(
        customers) == 1, f"Expected 1 customer row, found {len(customers)}"


@pytest.mark.asyncio
async def test_new_customer_created_for_different_phone(auth_client: AsyncClient, db_session):
    """T014 (extended): Different phone number should create a new customer even if name matches."""
    base = {
        "customer_name": "ReuseUser2",
        "service_type": "repair",
        "service_description": "Job A",
        "amount": 50.0,
        "gst_rate": 18.0,
    }
    p1 = {**base, "customer_phone": "9000022222"}
    p2 = {**base, "customer_phone": "9000022223"}

    r1 = await auth_client.post("/api/v1/invoices/", json=p1)
    assert r1.status_code == 201, r1.text
    inv1 = r1.json()

    r2 = await auth_client.post("/api/v1/invoices/", json=p2)
    assert r2.status_code == 201, r2.text
    inv2 = r2.json()

    assert inv1["customer_id"] != inv2["customer_id"], "Different phone should yield different customers"

    res = await db_session.execute(
        select(Customer).where(Customer.name ==
                               base["customer_name"])  # type: ignore[arg-type]
    )
    customers = res.scalars().all()
    # Two different customers for two distinct phone numbers
    assert len(customers) >= 2
