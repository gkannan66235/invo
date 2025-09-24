import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoice_soft_delete_contract(auth_client: AsyncClient):
    """T045 (contract): Soft delete hides invoice from list but keeps detail accessible.

    Steps:
      1. Create an invoice.
      2. DELETE the invoice (soft delete -> 204).
      3. GET list: invoice id NOT present.
      4. GET detail: invoice still returned with is_deleted == True.
    """
    # 1. Create
    create_resp = await auth_client.post(
        "/api/v1/invoices/",
        json={
            "customer_name": "SoftDelUser",
            "customer_phone": "9898989898",
            "service_type": "maintenance",
            "service_description": "Soft delete test",
            "amount": 100.0,
            "gst_rate": 18.0,
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.text
    create_env = create_resp.json()
    assert create_env.get("status") == "success"
    invoice = create_env["data"]
    invoice_id = invoice["id"]

    # 2. Delete
    del_resp = await auth_client.delete(f"/api/v1/invoices/{invoice_id}")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT, del_resp.text

    # 3. List should NOT contain
    list_resp = await auth_client.get("/api/v1/invoices/")
    assert list_resp.status_code == 200, list_resp.text
    listing_env = list_resp.json()
    assert listing_env.get("status") == "success"
    listing = listing_env["data"]
    assert all(
        inv["id"] != invoice_id for inv in listing), "Soft-deleted invoice appeared in list"

    # 4. Detail still accessible & is_deleted True
    detail_resp = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail_env = detail_resp.json()
    assert detail_env.get("status") == "success"
    detail = detail_env["data"]
    assert detail["id"] == invoice_id
    # is_deleted surfaced by helper mapping
    assert detail.get("is_deleted") is True
