import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_create_invoice_contract_basic(auth_client: AsyncClient):
    """T009: Contract test for POST /api/v1/invoices

    Verifies:
      - 201 Created status
      - Response contains required computed monetary fields
      - GST math: gst_amount = round(amount * gst_rate / 100, 2)
      - total_amount = amount + gst_amount
      - outstanding_amount == total_amount when paid_amount is 0
      - payment_status starts as pending (case-insensitive)
    (Invoice number format & uniqueness covered later in T057; default GST omission in T046.)
    """
    payload = {
        "customer_name": "ContractUser",
        "customer_phone": "9000011111",
        "service_type": "repair",
        "service_description": "Bearing replacement",
        "amount": 123.45,
        "gst_rate": 18.0,
    }

    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    envelope = resp.json()
    assert envelope.get("status") == "success"
    body = envelope.get("data")
    assert isinstance(body, dict)

    # Presence of key fields
    for field in [
        "id", "invoice_number", "amount", "gst_rate", "gst_amount", "total_amount",
        "outstanding_amount", "payment_status", "created_at", "updated_at"
    ]:
        assert field in body, f"Missing field '{field}' in response data: {body}"

    # Basic GST math assertions
    amount = payload["amount"]
    gst_rate = payload["gst_rate"]
    expected_gst = round(amount * gst_rate / 100, 2)
    expected_total = round(amount + expected_gst, 2)

    assert body["amount"] == pytest.approx(amount)
    assert body["gst_rate"] == pytest.approx(gst_rate)
    assert body["gst_amount"] == pytest.approx(expected_gst)
    assert body["total_amount"] == pytest.approx(expected_total)
    assert body["outstanding_amount"] == pytest.approx(expected_total)

    # Payment status should begin pending
    assert body["payment_status"].lower() in {"pending"}

    # Do not enforce full invoice number spec here (T057 handles); just ensure non-empty string
    assert isinstance(body["invoice_number"],
                      str) and body["invoice_number"].strip() != ""
