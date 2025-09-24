import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoices_list_ordering(auth_client: AsyncClient):
    """T012: List newest first ordering constraint."""
    # Create two invoices sequentially
    for idx in range(2):
        resp = await auth_client.post(
            "/api/v1/invoices/",
            json={
                "customer_name": f"ListUser{idx}",
                "customer_phone": f"91000{idx}0000",
                "service_type": "maintenance",
                "service_description": f"Cycle {idx}",
                "amount": 50 + idx,
                "gst_rate": 18.0,
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.text

    lst = await auth_client.get("/api/v1/invoices/")
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body.get("status") == "success"
    data = body.get("data")
    assert isinstance(data, list)
    # Ensure at least the two we just created are first by created_at (current code orders by created_at desc)
    created_at_values = [inv.get("created_at") for inv in data[:2]]
    assert all(created_at_values)
    # Basic monotonic check: first created_at >= second
    if len(created_at_values) == 2:
        assert created_at_values[0] >= created_at_values[1]
