import re
from datetime import datetime, UTC, timedelta
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_invoice_number_daily_sequence_reset(auth_client: AsyncClient, monkeypatch):
    """Ensure invoice number sequence resets to 0001 on a new day.

    Strategy:
      1. Create an invoice normally -> expect sequence N (typically 0001 in isolated test).
      2. Monkeypatch `src.services.invoice_service.datetime.now` to return tomorrow's date.
      3. Create a second invoice -> expect new date segment and sequence 0001 again.
    """
    # Step 1: Create first invoice (today)
    payload_today = {
        "customerName": "SeqReset Customer 1",
        "customerPhone": "9999911111",
        "amount": 50,
        "gstRate": 18,
    }
    r1 = await auth_client.post("/api/v1/invoices/", json=payload_today)
    assert r1.status_code == 201, r1.text
    data1 = r1.json().get("data", r1.json())
    inv1 = data1["invoice_number"]
    m1 = re.fullmatch(r"INV-(\d{8})-(\d{4})", inv1)
    assert m1, inv1
    date_part_1, seq_part_1 = m1.group(1), int(m1.group(2))
    assert seq_part_1 >= 1

    # Step 2: Monkeypatch datetime in service layer to simulate tomorrow
    tomorrow = (datetime.now(UTC) + timedelta(days=1)
                ).replace(hour=12, minute=0, second=0, microsecond=0)

    class _FakeDateTime:
        @staticmethod
        def now(tz=UTC):  # mimic datetime.now signature
            return tomorrow

    # Apply monkeypatch (only service uses this for invoice number generation)
    monkeypatch.setattr("src.services.invoice_service.datetime", _FakeDateTime)

    # Step 3: Create second invoice -> should use tomorrow's date and reset sequence to 0001
    payload_tomorrow = {
        "customerName": "SeqReset Customer 2",
        "customerPhone": "9999922222",
        "amount": 75,
        "gstRate": 18,
    }
    r2 = await auth_client.post("/api/v1/invoices/", json=payload_tomorrow)
    assert r2.status_code == 201, r2.text
    data2 = r2.json().get("data", r2.json())
    inv2 = data2["invoice_number"]
    m2 = re.fullmatch(r"INV-(\d{8})-(\d{4})", inv2)
    assert m2, inv2
    date_part_2, seq_part_2 = m2.group(1), int(m2.group(2))

    assert date_part_2 != date_part_1, f"Expected different date part after boundary: {date_part_1} vs {date_part_2}"
    assert seq_part_2 == 1, f"Sequence did not reset: got {seq_part_2} (invoice {inv2})"

    # Sanity: GST math still correct
    assert data2["gst_amount"] == 13.5  # 18% of 75
    assert data2["total_amount"] == 88.5
