import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_invoice_cancellation_then_payment_flow(auth_client: AsyncClient):
    """T016: Cancelling an invoice sets is_cancelled True but does NOT block later payments.

    Expectations (FR-012 clarification):
      - Cancellation is a logical flag (no hard lock)
      - Payment updates after cancellation still update payment_status & paid/outstanding amounts
    """
    create_payload = {
        "customer_name": "CancelUser",
        "customer_phone": "9100000016",
        "service_type": "repair",
        "service_description": "Pre-cancel job",
        "amount": 100.0,
        "gst_rate": 18.0,
    }
    r_create = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert r_create.status_code == status.HTTP_201_CREATED, r_create.text
    inv = r_create.json()
    invoice_id = inv["id"]
    total = inv["total_amount"]
    assert total == 118.0

    # Cancel the invoice
    r_cancel = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"status": "cancelled"})
    assert r_cancel.status_code == status.HTTP_200_OK, r_cancel.text
    inv_cancel = r_cancel.json()
    # Expect cancellation flag exposed
    assert inv_cancel.get("is_cancelled") is True, "Cancellation flag not set in response"
    # Still pending (no payment yet)
    assert inv_cancel["payment_status"] == "pending"

    # Partial payment AFTER cancellation
    r_partial = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": 50.0})
    assert r_partial.status_code == status.HTTP_200_OK, r_partial.text
    inv_partial = r_partial.json()
    assert inv_partial.get("is_cancelled") is True
    assert inv_partial["payment_status"] == "partial"
    assert abs(inv_partial["outstanding_amount"] - (total - 50.0)) < 1e-6

    # Full payment AFTER cancellation
    r_full = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"paid_amount": total})
    assert r_full.status_code == status.HTTP_200_OK, r_full.text
    inv_full = r_full.json()
    assert inv_full.get("is_cancelled") is True
    assert inv_full["payment_status"] == "paid"
    assert abs(inv_full["outstanding_amount"]) < 1e-6

