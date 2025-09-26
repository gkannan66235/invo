import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_soft_delete_flow_multiple_creates(auth_client: AsyncClient):
    """T045 (integration): Soft delete flow with multiple invoices.

    Ensures only deleted invoices are hidden and others remain.
    """
    created_ids = []
    for i in range(3):
        r = await auth_client.post(
            "/api/v1/invoices/",
            json={
                "customer_name": f"FlowUser{i}",
                # Provide a valid 10-digit Indian mobile number starting 6-9
                "customer_phone": f"900000000{i}",
                "service_type": "svc",
                "service_description": "multi",
                "amount": 50 + i,
                # omit gst_rate to exercise default path too
            },
        )
        assert r.status_code == status.HTTP_201_CREATED, r.text
        body = r.json()
        created_ids.append(body.get("data", body)["id"])

    # Soft delete the middle invoice
    mid_id = created_ids[1]
    d = await auth_client.delete(f"/api/v1/invoices/{mid_id}")
    assert d.status_code == status.HTTP_204_NO_CONTENT, d.text

    # List: should contain first & last, not middle
    lst = await auth_client.get("/api/v1/invoices/")
    assert lst.status_code == 200, lst.text
    body_list = lst.json()
    data_list = body_list.get("data", body_list)
    ids_in_list = {inv["id"] for inv in data_list}
    assert created_ids[0] in ids_in_list
    assert created_ids[2] in ids_in_list
    assert mid_id not in ids_in_list

    # Detail of deleted still accessible
    detail = await auth_client.get(f"/api/v1/invoices/{mid_id}")
    assert detail.status_code == 200, detail.text
    detail_data = detail.json().get("data", detail.json())
    assert detail_data.get("is_deleted") is True
