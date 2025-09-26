"""Basic tests for Prometheus /metrics exposition (T032 validation).

Lightweight sanity check: ensure endpoint returns 200 and includes one
expected metric name (api_request_duration_ms histogram) or falls back gracefully.
"""
import pytest

from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint_basic():  # noqa: D401
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger at least one application route to register custom metrics with OTEL.
        await client.get("/health")
        resp = await client.get("/metrics")
        assert resp.status_code in (200, 503)
        if resp.status_code == 503:
            # Library missing scenario
            assert "not installed" in resp.text.lower()
            return
        # Assert deterministic native metrics added via prometheus_client (app_* metrics)
        text_payload = resp.text
        assert "app_requests_total" in text_payload, "Expected native counter 'app_requests_total' missing"
        assert (
            "app_request_duration_seconds" in text_payload
        ), "Expected histogram 'app_request_duration_seconds' missing"
        assert "app_uptime_seconds" in text_payload, "Expected gauge 'app_uptime_seconds' missing"
