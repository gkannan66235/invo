import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.integration]

"""T017: Cancelled vs soft-deleted invoice access control.

Expectations:
- Soft-deleted: detail accessible (is_deleted True) but excluded from list.
- Cancelled: remains in list and detail accessible (visibility retained).
- Payment update on cancelled invoice: future refinement (status persistence checked only).
"""


@pytest.mark.asyncio
async def test_invoice_soft_delete_vs_cancel_access(auth_client: AsyncClient):
    # Create two invoices
    base_payload = {
        "customer_name": "AccessUser",
        "customer_phone": "9000011111",
        "service_type": "repair",
        "service_description": "motor",
        "amount": 120,
        "gst_rate": 18,
    }
    r1 = await auth_client.post("/api/v1/invoices/", json=base_payload)
    assert r1.status_code == status.HTTP_201_CREATED, r1.text
    inv1 = r1.json().get("data", r1.json())

    r2 = await auth_client.post(
        "/api/v1/invoices/",
        json=base_payload | {"customer_phone": "9000011112", "amount": 140},
    )
    assert r2.status_code == status.HTTP_201_CREATED, r2.text
    inv2 = r2.json().get("data", r2.json())

    # Soft delete invoice 1
    d1 = await auth_client.delete(f"/api/v1/invoices/{inv1['id']}")
    assert d1.status_code == status.HTTP_204_NO_CONTENT, d1.text

    # Cancel invoice 2 (PATCH with status cancelled)
    c2 = await auth_client.patch(f"/api/v1/invoices/{inv2['id']}", json={"status": "cancelled"})
    assert c2.status_code == 200, c2.text
    c2_body = c2.json().get("data", c2.json())
    # payment_status remains a valid value; cancellation sets is_cancelled flag internally
    assert c2_body.get("payment_status") is not None

    # List invoices -> should not include soft-deleted inv1 but should include cancelled inv2
    lst = await auth_client.get("/api/v1/invoices/")
    assert lst.status_code == 200, lst.text
    lst_body = lst.json().get("data", lst.json())
    ids = {i["id"] for i in lst_body}
    assert inv1["id"] not in ids, "Soft deleted invoice appeared in list"
    assert inv2["id"] in ids, "Cancelled invoice missing from list"

    # Detail: soft-deleted still retrievable with is_deleted True
    det1 = await auth_client.get(f"/api/v1/invoices/{inv1['id']}")
    assert det1.status_code == 200
    det1_body = det1.json().get("data", det1.json())
    assert det1_body.get("is_deleted") is True

    # Detail: cancelled invoice accessible and not flagged is_deleted
    det2 = await auth_client.get(f"/api/v1/invoices/{inv2['id']}")
    assert det2.status_code == 200
    det2_body = det2.json().get("data", det2.json())
    assert det2_body.get("is_deleted") is False
    # Business rule placeholder: is_cancelled True should remain visible (could assert once model exposes field)
