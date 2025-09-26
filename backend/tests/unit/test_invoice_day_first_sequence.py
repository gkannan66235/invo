import re
from datetime import datetime, UTC, timedelta
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_invoice_first_of_new_day_is_0001(auth_client: AsyncClient, monkeypatch):
    """Directly assert the first invoice for a synthetic future day starts at sequence 0001.

    This is a more granular unit-style test complementing the smoke reset test.
    It avoids creating an invoice for 'today' first so that we strictly test the
    logic that resets/initializes the day row when no invoices exist for that date.
    """
    future = (datetime.now(UTC) + timedelta(days=3)
              ).replace(hour=9, minute=0, second=0, microsecond=0)

    class _FakeDateTime:
        @staticmethod
        def now(tz=UTC):
            return future

    monkeypatch.setattr("src.services.invoice_service.datetime", _FakeDateTime)

    payload = {
        "customerName": "DayBoundary Test",
        "customerPhone": "8888877777",
        "amount": 42,
        "gstRate": 18,
    }
    r = await auth_client.post("/api/v1/invoices/", json=payload)
    assert r.status_code == 201, r.text
    body = r.json().get("data", r.json())
    inv = body["invoice_number"]
    m = re.fullmatch(r"INV-(\d{8})-(\d{4})", inv)
    assert m, inv
    seq = int(m.group(2))
    assert seq == 1, f"Expected first sequence for new future day to be 0001, got {seq} ({inv})"
