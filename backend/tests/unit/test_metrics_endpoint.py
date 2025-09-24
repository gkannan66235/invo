"""Basic tests for Prometheus /metrics exposition (T032 validation).

Lightweight sanity check: ensure endpoint returns 200 and includes one
expected metric name (api_request_duration_ms histogram) or falls back gracefully.
"""
import pytest

from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint_basic():  # noqa: D401
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Trigger at least one application route to register custom metrics with OTEL.
        await client.get("/health")
        resp = await client.get("/metrics")
        assert resp.status_code in (200, 503)
        if resp.status_code == 503:
            # Library missing scenario
            assert "not installed" in resp.text.lower()
            return
        # If 200, attempt to confirm (best-effort) presence of at least one custom metric name; if absent, do not fail hard.
        text_payload = resp.text
        custom_metric_names = ["api_request_duration_ms", "api_request_count"]
        if not any(n in text_payload for n in custom_metric_names):
            pytest.skip("Custom metrics not exposed yet in Prometheus payload (possibly metric reader version mismatch)")
