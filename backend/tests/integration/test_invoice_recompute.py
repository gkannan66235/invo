import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_invoice_recompute_on_amount_and_gst_change(auth_client: AsyncClient):
    """T015: Updating amount and gst_rate recomputes gst_amount & total_amount without losing payment status semantics.

    Steps:
      1. Create invoice with amount=100, gst_rate=18 -> gst=18.00, total=118.00
      2. PATCH invoice with amount=200, gst_rate=12 -> expect gst=24.00, total=224.00
      3. PATCH invoice with partial payment (e.g., paid_amount=50) -> status partial
      4. PATCH invoice adjusting amount down (150) and gst_rate up (18) -> recompute gst=27.00 total=177.00, payment status should remain partial (since paid < total) and NOT auto-paid
    """
    create_payload = {
        "customer_name": "RecomputeUser",
        "customer_phone": "9100000001",
        "service_type": "repair",
        "service_description": "Initial",
        "amount": 100.0,
        "gst_rate": 18.0,
    }
    r_create = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert r_create.status_code == status.HTTP_201_CREATED, r_create.text
    inv = r_create.json().get("data", r_create.json())
    assert inv["amount"] == 100.0
    assert inv["gst_rate"] == 18.0
    assert inv["gst_amount"] == 18.0
    assert inv["total_amount"] == 118.0

    invoice_id = inv["id"]

    # Recompute after amount & gst_rate change
    patch_payload = {"amount": 200.0, "gst_rate": 12.0}
    r_patch = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json=patch_payload)
    assert r_patch.status_code == status.HTTP_200_OK, r_patch.text
    inv2 = r_patch.json().get("data", r_patch.json())
    assert inv2["amount"] == 200.0
    assert inv2["gst_rate"] == 12.0
    assert inv2["gst_amount"] == 24.0, inv2
    assert inv2["total_amount"] == 224.0
    assert inv2["payment_status"] == "pending"

    # Partial payment
    pay_patch = {"paid_amount": 50.0}
    r_pay = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json=pay_patch)
    assert r_pay.status_code == status.HTTP_200_OK, r_pay.text
    inv3 = r_pay.json().get("data", r_pay.json())
    assert inv3["payment_status"] == "partial"
    assert inv3["outstanding_amount"] == 174.0  # 224 - 50

    # Adjust amounts again (down & new gst_rate)
    adjust_patch = {"amount": 150.0, "gst_rate": 18.0}
    r_adjust = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json=adjust_patch)
    assert r_adjust.status_code == status.HTTP_200_OK, r_adjust.text
    inv4 = r_adjust.json().get("data", r_adjust.json())
    # Recomputed amounts: subtotal=150, gst=27, total=177
    assert inv4["amount"] == 150.0
    assert inv4["gst_rate"] == 18.0
    assert inv4["gst_amount"] == 27.0, inv4
    assert inv4["total_amount"] == 177.0
    # Payment status should remain partial because paid_amount (50) < new total
    assert inv4["payment_status"] == "partial"
    assert abs(inv4["outstanding_amount"] - 127.0) < 1e-6
