import re
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_frontend_style_invoice_creation_sequence(auth_client: AsyncClient):
    """Smoke test: create two invoices using ONLY frontend-style camelCase fields.

    Validates:
      - Endpoint accepts camelCase payload without backend snake_case keys
      - Computed GST and total amounts are correct
      - Invoice number pattern INVYYYYMMDDNNNN
      - Sequential numbering increments by 1 for consecutive creations in same day
      - Normalization stores gstRate numeric string correctly
    """
    payload1 = {
        "customerName": "Smoke Customer A",
        "customerPhone": "9876500011",
        "amount": "150",          # numeric string
        "gstRate": "18"            # numeric string
    }
    r1 = await auth_client.post("/api/v1/invoices/", json=payload1)
    assert r1.status_code == 201, r1.text
    j1 = r1.json()
    data1 = j1.get("data", j1)

    # Basic field assertions
    assert data1["amount"] == 150.0
    assert data1["gst_rate"] == 18.0
    assert data1["gst_amount"] == 27.0
    assert data1["total_amount"] == 177.0
    assert data1["payment_status"].lower() == "pending"

    inv_num1 = data1["invoice_number"]
    assert re.fullmatch(r"INV\d{8}\d{4}", inv_num1), inv_num1

    # Second invoice to verify increment
    payload2 = {
        "customerName": "Smoke Customer B",
        "customerPhone": "9876500012",
        "amount": 200,   # numeric (float/int acceptable)
        "gstRate": 18
    }
    r2 = await auth_client.post("/api/v1/invoices/", json=payload2)
    assert r2.status_code == 201, r2.text
    data2 = r2.json().get("data", r2.json())

    inv_num2 = data2["invoice_number"]
    assert re.fullmatch(r"INV\d{8}\d{4}", inv_num2), inv_num2

    # Extract the sequence (last 4 digits) and compare
    seq1 = int(inv_num1[-4:])
    seq2 = int(inv_num2[-4:])
    assert seq2 == seq1 + 1, f"Expected sequential invoice numbers, got {inv_num1} -> {inv_num2}"

    # Sanity check GST math for second invoice
    assert data2["gst_amount"] == 36.0  # 18% of 200
    assert data2["total_amount"] == 236.0
