import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoice_partial_then_paid(auth_client: AsyncClient):
    """T010: PATCH transitions payment status pending -> partial -> paid."""
    create_payload = {
        "customer_name": "PayUser",
        "customer_phone": "9000022222",
        "service_type": "install",
        "service_description": "Pump install",
        "amount": 1000.0,
        "gst_rate": 18.0,
    }
    resp = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    invoice = resp.json()
    invoice_id = invoice["id"]

    # Partial payment
    part = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 500})
    assert part.status_code == 200, part.text
    assert part.json()["payment_status"].lower() == "partial"

    # Full payment
    full = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": invoice["total_amount"]})
    assert full.status_code == 200, full.text
    assert full.json()["payment_status"].lower() == "paid"
