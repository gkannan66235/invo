import statistics
import time
from typing import List

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.performance
# T059
async def test_create_invoices_p95_under_300ms(auth_client: AsyncClient):
    """Performance test for invoice creation latency (p95 < 300ms).

    Maps NFR-002 (creation performance).

    Methodology:
      1. Perform a small warmup set of creations (unmeasured) to absorb import / first-commit cost.
      2. Execute N measured POST /api/v1/invoices/ requests, capturing client-side wall clock.
      3. Compute p95 (ceil(0.95 * n) - 1 index of sorted samples) and assert it is below 300ms.

    Rationale:
      - Measuring multiple samples and asserting p95 reduces flakiness from occasional GC / I/O spikes.
      - Warmups mitigate first-request overhead (lazy metadata compilation, connection pool establishment).
      - Creation path exercises: customer creation (for new phone/name), invoice number generation, GST calc, commit.
    """
    # 1. Warmups (create a few invoices but do not measure)
    WARMUPS = 5
    for i in range(WARMUPS):
        payload = {
            "customer_name": f"PerfCreateWarm{i}",
            # 10-digit valid Indian mobile (starts with 9)
            "customer_phone": f"9{(10000 + i):09d}",
            "service_type": "perf",
            "service_description": "warmup",
            "amount": 123.45 + i,
            "gst_rate": 18,
        }
        r = await auth_client.post("/api/v1/invoices/", json=payload)
        assert r.status_code == 201, r.text

    # 2. Measured creations
    SAMPLES = 25  # modest sample size; enough for a stable p95 while keeping suite fast
    timings: List[float] = []
    for i in range(SAMPLES):
        idx = i + WARMUPS
        payload = {
            "customer_name": f"PerfCreate{idx}",
            # Ensure uniqueness & validity (leading 9 + zero padded sequence)
            "customer_phone": f"9{(20000 + idx):09d}",
            "service_type": "perf",
            "service_description": "measured",
            "amount": 150 + (i % 20),
            "gst_rate": 18,
        }
        start = time.perf_counter()
        resp = await auth_client.post("/api/v1/invoices/", json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201, resp.text
        timings.append(elapsed_ms)

    # 3. Compute statistics (p95, mean, max)
    import math
    timings_sorted = sorted(timings)
    p95_index = max(0, math.ceil(0.95 * len(timings_sorted)) - 1)
    p95 = timings_sorted[p95_index]
    mean = statistics.mean(timings_sorted)
    max_latency = max(timings_sorted)

    threshold_ms = 300.0
    assert p95 < threshold_ms, (
        "Invoice creation p95 latency {:.2f}ms (mean {:.2f}ms, max {:.2f}ms) exceeded <{:.0f}ms threshold. "
        "Samples: {}".format(
            p95,
            mean,
            max_latency,
            threshold_ms,
            [f"{t:.1f}" for t in timings_sorted],
        )
    )

    # 4. Print a concise summary for visibility in verbose mode / CI logs
    print(
        f"[PERF] create invoice p95={p95:.2f}ms mean={mean:.2f}ms max={max_latency:.2f}ms samples={len(timings_sorted)}"
    )
