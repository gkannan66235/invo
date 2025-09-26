import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoice_create_missing_required_fields(auth_client: AsyncClient):
    """T013: Missing required customer/amount fields returns 422 with error schema (FR-015/FR-024)."""
    # Omit amount
    bad_payload = {
        "customer_name": "NoAmountUser",
        "customer_phone": "9900012345",
        # "amount": missing
        "gst_rate": 18.0,
    }
    resp = await auth_client.post("/api/v1/invoices/", json=bad_payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp.text
    body = resp.json()
    if isinstance(body, dict) and body.get("status") == "error":
        assert body.get("error", {}).get("code") == "VALIDATION_ERROR"

    # Omit customer name
    bad_payload2 = {
        "customer_phone": "9900099999",
        "amount": 10,
        "gst_rate": 18.0,
    }
    resp2 = await auth_client.post("/api/v1/invoices/", json=bad_payload2)
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp2.text
