import pytest
from httpx import AsyncClient
from src.main import app  # noqa: F401


@pytest.mark.asyncio
async def test_gst_default_applied_when_omitted(auth_client: AsyncClient):
    payload = {
        "customer_name": "GST Test",
        # Use a valid Indian mobile pattern (starts with 9, 10 digits)
        "customer_phone": "9123450000",
        "service_type": "svc",
        "service_description": "desc",
        "amount": 1000,
        # gst_rate intentionally omitted
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    inv = body.get("data", body)
    # Default from settings (commonly 18 unless overridden by other test manipulating env)
    from src.config.settings import get_default_gst_rate  # type: ignore
    expected_rate = get_default_gst_rate()
    assert inv["gst_rate"] == expected_rate
    expected_gst = round(1000 * expected_rate / 100, 2)
    expected_total = round(1000 + expected_gst, 2)
    assert inv["gst_amount"] == expected_gst
    assert inv["total_amount"] == expected_total


@pytest.mark.asyncio
async def test_gst_math_high_value(auth_client: AsyncClient):
    payload = {
        "customer_name": "High",
        "customer_phone": "9123450001",
        "service_type": "svc",
        "service_description": "desc",
        "amount": 99999.99,
        "gst_rate": 28,
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == 201, resp.text
    inv = resp.json().get("data", resp.json())
    assert inv["gst_rate"] == 28
    assert inv["gst_amount"] == round(99999.99 * 28 / 100, 2)
    assert inv["total_amount"] == round(99999.99 + inv["gst_amount"], 2)
