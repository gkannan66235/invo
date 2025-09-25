import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError


@pytest.mark.asyncio
async def test_db_failure_returns_standardized_db_error(auth_client: AsyncClient, monkeypatch):
    """T051: Simulate a database failure and assert standardized DB_ERROR response.

    We monkeypatch the invoice number generator (first DB touch point in service) to raise
    a synthetic SQLAlchemyError. The global exception handler should translate this into
    a 500 response with code DB_ERROR (not INTERNAL_SERVER_ERROR).
    """

    class SyntheticDBError(SQLAlchemyError):
        pass

    async def boom(*args, **kwargs):  # noqa: D401
        raise SyntheticDBError("synthetic db failure")

    monkeypatch.setattr(
        "src.services.invoice_service._generate_invoice_number", boom)

    payload = {
        "customerName": "DB Failure Customer",
        "customerPhone": "7777700001",
        "amount": 10,
        "gstRate": 18
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)

    # EXPECTATION (will currently fail until handler added): 500 & DB_ERROR
    assert resp.status_code == 500, resp.text
    data = resp.json()
    assert data.get("status") == "error"
    # This assertion is meant to fail pre-implementation (currently INTERNAL_SERVER_ERROR)
    assert data.get("error", {}).get("code") == "DB_ERROR", data
