import time
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.performance
async def test_list_invoices_p95_under_200ms(auth_client: AsyncClient):
    """Performance harness skeleton (T005).

    Creates a modest batch of invoices then measures list latency.
    Real p95 aggregation logic will be added in T018; here we assert a single run <300ms
    (looser) to avoid flakiness while still catching egregious regressions.
    """
    # Ensure some invoices exist
    for i in range(5):
        payload = {
            "customer_name": f"PerfUser{i}",
            "customer_phone": f"90000000{i:02d}",
            "service_type": "perf",
            "service_description": "benchmark",
            "amount": 100 + i,
            "gst_rate": 18
        }
        resp = await auth_client.post("/api/v1/invoices/", json=payload)
        assert resp.status_code == 201, resp.text

    start = time.perf_counter()
    list_resp = await auth_client.get("/api/v1/invoices/")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert list_resp.status_code == 200, list_resp.text
    # Initial relaxed bound; tightened & converted to p95 aggregation in T018
    assert elapsed_ms < 300, f"List invoices took {elapsed_ms:.2f}ms (expected <300ms placeholder)"
