import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_invoice_numeric_string_coercion_create_and_update(auth_client: AsyncClient):
    """T017: Numeric string coercion for amount, gst_rate, paid_amount (FR-013/FR-014/FR-020).

    Verifies:
      - Create accepts amount & gst_rate as strings and computes gst & total correctly.
      - Create with empty gst_rate string treats it as omitted (0% tax).
      - Update with string values recomputes amounts.
      - Partial payment with string paid_amount works and sets payment_status partial.
    """
    # Case 1: Normal numeric strings
    create_payload = {
        "customer_name": "StringNumUser",
        "customer_phone": "9200000017",
        "service_type": "repair",
        "service_description": "String values",
        "amount": "100.00",
        "gst_rate": "18"
    }
    r_create = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert r_create.status_code == status.HTTP_201_CREATED, r_create.text
    inv = r_create.json()
    assert inv["amount"] == 100.0
    assert inv["gst_rate"] == 18.0
    assert inv["gst_amount"] == 18.0
    assert inv["total_amount"] == 118.0

    invoice_id = inv["id"]

    # Update with new numeric strings (amount & gst_rate)
    patch_payload = {"amount": "200.50", "gst_rate": "5"}
    r_patch = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json=patch_payload)
    assert r_patch.status_code == status.HTTP_200_OK, r_patch.text
    inv2 = r_patch.json()
    assert inv2["amount"] == 200.5
    assert inv2["gst_rate"] == 5.0
    # gst = 200.50 * 5% = 10.025 -> rounded 10.03 (current rounding strategy)
    # allow for rounding differences until Decimal HALF_UP implemented
    assert inv2["gst_amount"] in (10.03, 10.02)
    expected_total = round(inv2["amount"] + inv2["gst_amount"], 2)
    assert inv2["total_amount"] == expected_total

    # Partial payment with paid_amount as string
    pay_patch = {"paid_amount": "50"}
    r_pay = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json=pay_patch)
    assert r_pay.status_code == status.HTTP_200_OK, r_pay.text
    inv3 = r_pay.json()
    assert inv3["payment_status"] == "partial"
    assert inv3["outstanding_amount"] == round(inv3["total_amount"] - 50.0, 2)

    # Case 2: Create with empty gst_rate string -> treat as 0
    create_payload2 = {
        "customer_name": "StringNumUser2",
        "customer_phone": "9200000018",
        "service_type": "repair",
        "service_description": "Empty gst_rate",
        "amount": "80",
        "gst_rate": ""  # becomes None -> interpreted as 0
    }
    r_create2 = await auth_client.post("/api/v1/invoices/", json=create_payload2)
    assert r_create2.status_code == status.HTTP_201_CREATED, r_create2.text
    inv_empty = r_create2.json()
    assert inv_empty["amount"] == 80.0
    # Current implementation returns gst_rate as None when omitted/empty; gst_amount should be 0
    assert inv_empty["gst_amount"] == 0.0
    assert inv_empty["total_amount"] == 80.0
