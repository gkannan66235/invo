import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoice_default_gst_applied_when_omitted(auth_client: AsyncClient, monkeypatch):
    """T046: Omitted gst_rate applies DEFAULT_GST_RATE env (FR-022).

    Steps:
      1. Set DEFAULT_GST_RATE env to a distinct value.
      2. Clear settings cache.
      3. Create invoice without gst_rate field.
      4. Assert gst_rate in response equals configured default and GST math matches.
    """
    # 1. Set environment value
    monkeypatch.setenv("DEFAULT_GST_RATE", "22.5")

    # 2. Clear cached settings so new env is picked up
    from src.config.settings import get_settings  # type: ignore
    get_settings.cache_clear()  # type: ignore[attr-defined]

    payload = {
        "customer_name": "DefaultGSTUser",
        "customer_phone": "9333300000",
        "service_type": "repair",
        "service_description": "Clamp replacement",
        "amount": 200.0,
        # gst_rate intentionally omitted
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    env1 = resp.json()
    assert env1.get("status") == "success"
    body = env1["data"]

    assert body["gst_rate"] == pytest.approx(22.5)
    expected_gst = round(payload["amount"] * 22.5 / 100, 2)
    expected_total = round(payload["amount"] + expected_gst, 2)
    assert body["gst_amount"] == pytest.approx(expected_gst)
    assert body["total_amount"] == pytest.approx(expected_total)


@pytest.mark.asyncio
async def test_invoice_explicit_gst_rate_not_overwritten(auth_client: AsyncClient, monkeypatch):
    """T046 (secondary): Explicit gst_rate must override default and be preserved."""
    # Set a default different from explicit to ensure override works
    monkeypatch.setenv("DEFAULT_GST_RATE", "15.0")
    from src.config.settings import get_settings  # type: ignore
    get_settings.cache_clear()  # type: ignore[attr-defined]

    payload = {
        "customer_name": "ExplicitGSTUser",
        "customer_phone": "9444400000",
        "service_type": "service",
        "service_description": "Calibration",
        "amount": 80.0,
        "gst_rate": 5.0,
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    env2 = resp.json()
    assert env2.get("status") == "success"
    body = env2["data"]

    assert body["gst_rate"] == pytest.approx(5.0)
    expected_gst = round(payload["amount"] * 5.0 / 100, 2)
    expected_total = round(payload["amount"] + expected_gst, 2)
    assert body["gst_amount"] == pytest.approx(expected_gst)
    assert body["total_amount"] == pytest.approx(expected_total)
