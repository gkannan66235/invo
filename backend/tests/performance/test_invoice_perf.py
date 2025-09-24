import statistics
import time
from typing import List

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.performance
async def test_list_invoices_p95_under_200ms(auth_client: AsyncClient):  # T018
    """Performance test for listing invoices (p95 < 200ms for 100-row dataset).

    Steps:
    1. Seed 100 invoices (idempotent-ish; duplicates acceptable for perf scope).
    2. Warm up the endpoint (unmeasured calls) to mitigate first-call overhead.
    3. Perform N measured list calls capturing elapsed wall-clock (client side) latency.
    4. Compute p95 and assert it is < 200ms.

    Rationale:
    - 100 invoices approximates an early realistic page payload.
    - p95 chosen over a single measurement to smooth sporadic spikes.
    - Warmups reduce noise from import / first query planning.
    """
    # 1. Seed invoices (skip if already roughly present to limit growth)
    # We cannot rely on a truncate between tests; keep it simple & bounded.
    existing = await auth_client.get("/api/v1/invoices/")
    assert existing.status_code == 200, existing.text
    current_count = len(existing.json().get("data", existing.json())) if isinstance(
        existing.json(), dict) else len(existing.json())
    target_total = 100
    to_create = max(0, target_total - current_count)
    for i in range(to_create):
        idx = current_count + i
        # Ensure phone stays a valid 10-digit starting with 9 (pattern ^(\+91|91)?[6-9]\d{9}$)
        # Build a deterministic 10-digit number: leading 9 + 9-digit zero-padded index
        phone_suffix = f"{idx:09d}"  # 9 digits
        payload = {
            "customer_name": f"PerfUser{idx}",
            "customer_phone": f"9{phone_suffix}",  # total length = 10 digits
            "service_type": "perf",
            "service_description": "benchmark",
            "amount": 100 + (idx % 50),  # moderate variance
            "gst_rate": 18
        }
        resp = await auth_client.post("/api/v1/invoices/", json=payload)
        assert resp.status_code == 201, resp.text

    # 2. Warmups (unmeasured)
    WARMUPS = 3
    for _ in range(WARMUPS):
        r = await auth_client.get("/api/v1/invoices/")
        assert r.status_code == 200

    # 3. Measured calls
    SAMPLES = 15
    timings: List[float] = []
    for _ in range(SAMPLES):
        start = time.perf_counter()
        list_resp = await auth_client.get("/api/v1/invoices/")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert list_resp.status_code == 200, list_resp.text
        timings.append(elapsed_ms)

    # 4. Compute p95
    timings_sorted = sorted(timings)
    # p95 index (ceil(0.95 * n) - 1)
    import math
    p95_index = max(0, math.ceil(0.95 * len(timings_sorted)) - 1)
    p95 = timings_sorted[p95_index]
    mean = statistics.mean(timings_sorted)
    max_latency = max(timings_sorted)

    threshold_ms = 200.0
    assert p95 < threshold_ms, (
        "List invoices p95 latency {:.2f}ms (mean {:.2f}ms, max {:.2f}ms) exceeded <{:.0f}ms threshold. Samples: {}".format(
            p95, mean, max_latency, threshold_ms, [
                f"{t:.1f}" for t in timings_sorted]
        )
    )

    # Provide context if test passes (pytest -vv will show docstring + assertion not triggered)
    print(
        f"[PERF] list invoices p95={p95:.2f}ms mean={mean:.2f}ms max={max_latency:.2f}ms samples={len(timings_sorted)}")
