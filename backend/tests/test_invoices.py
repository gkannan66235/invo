import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_invoice_minimal(auth_client: AsyncClient):
    payload = {
        "customer_name": "Alice",
        "customer_phone": "9990001111",
        "service_type": "repair",
        "service_description": "Motor rewinding",
        "amount": 1000,
        "gst_rate": 18
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["amount"] == 1000
    assert data["gst_rate"] == 18
    assert data["gst_amount"] == 180
    assert data["total_amount"] == 1180
    assert data["payment_status"].lower() == "pending"


@pytest.mark.asyncio
async def test_partial_payment_and_full_payment(auth_client: AsyncClient):
    # Create invoice
    create_payload = {
        "customer_name": "Bob",
        "customer_phone": "8887776666",
        "service_type": "installation",
        "service_description": "Pump installation",
        "amount": 2000,
        "gst_rate": 18
    }
    create_resp = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert create_resp.status_code == 201, create_resp.text
    invoice = create_resp.json()
    invoice_id = invoice["id"]

    # Partial payment
    patch_resp = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 500})
    assert patch_resp.status_code == 200, patch_resp.text
    updated = patch_resp.json()
    assert updated["payment_status"].lower() == "partial"

    # Full payment
    total_amount = updated["total_amount"]
    patch_resp2 = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": total_amount})
    assert patch_resp2.status_code == 200, patch_resp2.text
    updated2 = patch_resp2.json()
    assert updated2["payment_status"].lower() == "paid"


@pytest.mark.asyncio
async def test_overpay_rejected(auth_client: AsyncClient):
    payload = {
        "customer_name": "Charlie",
        "customer_phone": "7776665555",
        "service_type": "maintenance",
        "service_description": "Quarterly maintenance",
        "amount": 500,
        "gst_rate": 18
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201, resp.text
    invoice_id = resp.json()["id"]

    bad = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 10000})
    assert bad.status_code == 400
    # Domain error standardized message: Paid amount <x> exceeds total <y>
    assert "exceeds total" in bad.text
