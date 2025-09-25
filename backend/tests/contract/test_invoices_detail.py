import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.contract


async def _create_invoice(auth_client: AsyncClient):
    payload = {
        "customer_name": "DetailUser",
        "customer_phone": "9123499999",
        "amount": 120.0,
        "service_description": "Detail svc",
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    return data["id"], data


@pytest.mark.asyncio
async def test_invoice_detail_round_trip(auth_client: AsyncClient):
    inv_id, _ = await _create_invoice(auth_client)

    # Fetch detail
    resp = await auth_client.get(f"/api/v1/invoices/{inv_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()["data"]
    # Basic field presence
    for field in [
        "id", "invoice_number", "amount", "gst_amount", "total_amount",
        "payment_status", "paid_amount", "is_deleted", "is_cancelled"
    ]:
        assert field in detail
    assert detail["id"] == inv_id
    assert detail["paid_amount"] == 0

    # Update payment
    upd = await auth_client.patch(f"/api/v1/invoices/{inv_id}", json={"paid_amount": detail["total_amount"]})
    assert upd.status_code == 200, upd.text
    updated = upd.json()["data"]
    assert updated["payment_status"].lower() == "paid"

    # Fetch again to ensure reflect changes
    resp2 = await auth_client.get(f"/api/v1/invoices/{inv_id}")
    assert resp2.status_code == 200
    detail2 = resp2.json()["data"]
    assert detail2["payment_status"].lower() == "paid"
    assert float(detail2["paid_amount"]) == float(detail2["total_amount"])  # fully paid
