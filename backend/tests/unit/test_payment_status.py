import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_transitions(auth_client: AsyncClient):
    # Create invoice
    payload = {
        "customer_name": "Pay",
        "customer_phone": "9123455555",
        "service_type": "svc",
        "service_description": "desc",
        "amount": 500,
        "gst_rate": 10,
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201
    inv = resp.json().get("data", resp.json())
    invoice_id = inv["id"]
    assert inv["payment_status"].lower() == "pending"

    # Partial payment
    patch = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 100})
    assert patch.status_code == 200
    upd = patch.json().get("data", patch.json())
    assert upd["payment_status"].lower() == "partial"

    # Full payment
    patch2 = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": upd["total_amount"]})
    assert patch2.status_code == 200
    upd2 = patch2.json().get("data", patch2.json())
    assert upd2["payment_status"].lower() == "paid"

    # Downgrade to pending by reducing paid_amount
    patch3 = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 0})
    assert patch3.status_code == 200
    upd3 = patch3.json().get("data", patch3.json())
    assert upd3["payment_status"].lower() == "pending"
