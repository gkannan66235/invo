import pytest
from httpx import AsyncClient

# T009: Invoices API contract tests
# Validates create/list/get shapes, snapshot field presence, monetary calculations.


@pytest.mark.asyncio
async def test_invoice_create_snapshot_and_list(auth_client: AsyncClient):
    payload = {
        "customer_name": "Contract User",
        "customer_phone": "9123456780",
        "service_type": "repair",
        "service_description": "Motor rewind",
        "amount": 1234.50,
        "gst_rate": 18
    }
    r = await auth_client.post("/api/v1/invoices", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    inv = data if "invoice_number" in data else data.get(
        "invoice") or data.get("invoices")
    assert inv["gst_rate"] == 18
    assert inv["gst_amount"] == pytest.approx(round(1234.50 * 0.18, 2))
    assert inv["total_amount"] == pytest.approx(round(1234.50 * 1.18, 2))
    # Snapshot fields present
    assert "branding_snapshot" in inv
    assert "gst_rate_snapshot" in inv
    assert "settings_snapshot" in inv

    # List
    lst = await auth_client.get("/api/v1/invoices")
    assert lst.status_code == 200
    body = lst.json()
    assert body.get("status") == "success"
    invoices = body["data"] if isinstance(
        body.get("data"), list) else body["data"].get("invoices") or body["data"]
    assert any(i["invoice_number"] == inv["invoice_number"] for i in invoices)

    # Get single
    gid = await auth_client.get(f"/api/v1/invoices/{inv['id']}")
    assert gid.status_code == 200
    gbody = gid.json()["data"] if "data" in gid.json() else gid.json()
    assert gbody["invoice_number"] == inv["invoice_number"]
