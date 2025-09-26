"""Prometheus metrics exposition router (T032).

Registers a /metrics endpoint exposing Prometheus text format collected via
OpenTelemetry PrometheusMetricReader or direct prometheus_client collectors.

FastAPI best practice: provide raw Response with correct content-type so
Prometheus server can scrape.
"""
from fastapi import APIRouter, Response

try:
    # Primary: use prometheus_client which the OTEL PrometheusMetricReader feeds
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - fallback if library missing
    generate_latest = None  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"  # type: ignore

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:  # noqa: D401
    if generate_latest is None:
        return Response("prometheus_client not installed", status_code=503, media_type="text/plain")
    data = generate_latest()  # type: ignore
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
