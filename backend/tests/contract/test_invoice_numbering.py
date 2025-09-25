"""Contract test for invoice numbering format & daily sequence (T057 / FR-005).

Verifies that newly created invoices receive an invoice_number matching pattern:
    INV-YYYYMMDD-NNNN
Where:
  - YYYYMMDD is the current UTC date at time of creation
  - NNNN is a zero-padded 4 digit daily sequence that monotonically increments

The test does NOT assume the sequence starts at 0001 because previous tests in the
same session may have already created invoices for the day. Instead it captures two
consecutive creations and asserts:
  1. Both match the pattern
  2. Second sequence = first sequence + 1 (monotonic increment)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

PATTERN_RE = re.compile(r"^INV-(\d{8})-(\d{4})$")


def _extract_invoice(body):  # helper tolerant of legacy/non-envelope responses
    if isinstance(body, dict) and "data" in body and isinstance(body["data"], dict):
        return body["data"]
    return body


@pytest.mark.contract
@pytest.mark.asyncio
async def test_invoice_number_format_and_sequence(auth_client):  # noqa: D401
    utc_today = datetime.now(timezone.utc).strftime('%Y%m%d')

    payload = {
        "customer_name": "Numbering Contract Co",
        "customer_phone": "+919876543211",  # Valid Indian number per validation
        "service_type": "diagnostics",
        "service_description": "Sequence test #1",
        "amount": 50.0,
        "gst_rate": 18.0,
    }

    r1 = await auth_client.post("/api/v1/invoices/", json=payload)
    assert r1.status_code == 201, r1.text
    inv1 = _extract_invoice(r1.json())

    r2 = await auth_client.post("/api/v1/invoices/", json={**payload, "service_description": "Sequence test #2"})
    assert r2.status_code == 201, r2.text
    inv2 = _extract_invoice(r2.json())

    num1 = inv1["invoice_number"]
    num2 = inv2["invoice_number"]

    m1 = PATTERN_RE.match(num1)
    m2 = PATTERN_RE.match(num2)
    assert m1, f"First invoice_number does not match pattern: {num1}"
    assert m2, f"Second invoice_number does not match pattern: {num2}"

    date1, seq1 = m1.group(1), int(m1.group(2))
    date2, seq2 = m2.group(1), int(m2.group(2))

    assert date1 == utc_today, f"Expected first invoice date {utc_today} got {date1}"
    assert date2 == utc_today, f"Expected second invoice date {utc_today} got {date2}"
    assert seq2 == seq1 + \
        1, f"Expected second sequence {seq1 + 1} got {seq2} (first={seq1})"
