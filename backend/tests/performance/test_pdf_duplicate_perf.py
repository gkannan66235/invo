import math
import statistics
import time
from typing import List

import pytest
from httpx import AsyncClient


PDF_P95_THRESHOLD_MS = 2000.0  # NFR-002 (< 2s)
DUPLICATE_LOOKUP_P95_THRESHOLD_MS = 50.0  # Requirement (<50ms)


@pytest.mark.asyncio
@pytest.mark.performance
# T030
async def test_invoice_pdf_generation_p95_under_2s(auth_client: AsyncClient):
    """Performance test: PDF generation latency p95 < 2000ms.

    Methodology:
      1. Warm up (create & fetch) to ensure lazy imports/connections established.
      2. Measure N GET /api/v1/invoices/{id}/pdf requests (client wall-clock).
      3. Compute p95 (ceil(0.95*n)-1) and assert below threshold.

    Notes:
      - Stub generator now; real renderer later may be slower.
      - Threshold generous (2s) to stay valid post real implementation.
    """

    # 1. Create invoice
    create_payload = {
        "customer_name": "PerfPDFUser",
        "customer_phone": "9876543210",  # valid Indian mobile
        "service_type": "perf",
        "service_description": "pdf benchmark",
        "amount": 500,
        "gst_rate": 18,
    }
    r = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert r.status_code == 201, r.text
    invoice_json = r.json()
    invoice_id = (
        invoice_json.get("data", {}).get("invoice", {}).get("id")
        if "data" in invoice_json
        else invoice_json.get("id")
    )

    # Warmups
    WARMUPS = 3
    for _ in range(WARMUPS):
        pdf_resp_w = await auth_client.get(f"/api/v1/invoices/{invoice_id}/pdf")
        assert pdf_resp_w.status_code == 200
        assert pdf_resp_w.headers.get(
            "content-type", "").startswith("application/pdf")

    # 2. Measured requests
    SAMPLES = 15
    timings: List[float] = []
    for _ in range(SAMPLES):
        start = time.perf_counter()
        pdf_resp = await auth_client.get(f"/api/v1/invoices/{invoice_id}/pdf")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert pdf_resp.status_code == 200
        assert pdf_resp.content.startswith(b"%PDF")
        timings.append(elapsed_ms)

    timings_sorted = sorted(timings)
    p95_index = max(0, math.ceil(0.95 * len(timings_sorted)) - 1)
    p95 = timings_sorted[p95_index]
    mean = statistics.mean(timings_sorted)
    max_latency = max(timings_sorted)

    assert p95 < PDF_P95_THRESHOLD_MS, (
        f"PDF generation p95 {p95:.2f}ms (mean {mean:.2f}ms, max {max_latency:.2f}ms) exceeded "
        f"<{PDF_P95_THRESHOLD_MS:.0f}ms threshold. Samples: "
        + ",".join(f"{t:.1f}" for t in timings_sorted)
    )

    print(
        f"[PERF] pdf generation p95={p95:.2f}ms mean={mean:.2f}ms max={max_latency:.2f}ms "
        f"samples={len(timings_sorted)}"
    )


@pytest.mark.asyncio
@pytest.mark.performance
# T030
async def test_customer_duplicate_lookup_p95_under_50ms(auth_client: AsyncClient):
    """Performance test: duplicate customer mobile lookup p95 < 50ms.

    Methodology:
      1. Seed a baseline customer with a specific mobile (normalized form stored).
      2. Warm up duplicate creations (same mobile, different name) to absorb first-query overhead.
      3. Perform N measured duplicate customer creations capturing wall-clock latency.
      4. Compute p95 and assert < 50ms.

    Rationale:
      - Duplicate detection path performs a limited (LIMIT 2) indexed equality lookup by normalized mobile.
      - Measuring creation (rather than isolated service call) yields end-to-end latency including DB round-trip.
      - p95 metric ensures occasional GC/network jitter does not fail the test if overall path is performant.

        Caveats:
            - Accumulating many duplicates on the same mobile is acceptable; query stops at 2 rows due to LIMIT,
                keeping latency flat.
    """

    base_payload = {
        "name": "DupBase",
        "mobile": "+91 91234 56789",  # includes prefix & spaces to exercise normalization
        "email": "dupbase@example.com",
    }
    base_resp = await auth_client.post("/api/v1/customers", json=base_payload)
    assert base_resp.status_code in (
        201, 200, 409, 422) or base_resp.status_code < 500
    # Even if already seeded, proceed (idempotent-ish for perf scope)

    # Warmups
    WARMUPS = 5
    for i in range(WARMUPS):
        warm_payload = {
            "name": f"DupWarm{i}",
            "mobile": "9123456789",  # same normalized digits
            "email": f"dupwarm{i}@example.com",
        }
        wr = await auth_client.post("/api/v1/customers", json=warm_payload)
        assert wr.status_code in (201, 200, 409, 422) or wr.status_code < 500

    # Measured duplicate creations
    SAMPLES = 20
    timings: List[float] = []
    for i in range(SAMPLES):
        payload = {
            "name": f"DupMeasure{i}",
            "mobile": "9123456789",  # duplicate
            "email": f"dupmeasure{i}@example.com",
        }
        start = time.perf_counter()
        resp = await auth_client.post("/api/v1/customers", json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        # Expect success with duplicate warning in response when successful
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        # Defensive: some responses may have envelope
        customer_obj = None
        if isinstance(body, dict):
            if body.get("data") and isinstance(body["data"], dict):
                # possible shapes: {data: {customer: {...}}} OR directly the object
                if "customer" in body["data"]:
                    customer_obj = body["data"]["customer"]
                else:
                    customer_obj = body["data"]
            else:
                customer_obj = body
        if customer_obj:
            # duplicate_warning should be True beyond the first baseline
            assert customer_obj.get("duplicate_warning") is True
        timings.append(elapsed_ms)

    timings_sorted = sorted(timings)
    p95_index = max(0, math.ceil(0.95 * len(timings_sorted)) - 1)
    p95 = timings_sorted[p95_index]
    mean = statistics.mean(timings_sorted)
    max_latency = max(timings_sorted)

    assert p95 < DUPLICATE_LOOKUP_P95_THRESHOLD_MS, (
        f"Customer duplicate lookup p95 {p95:.2f}ms (mean {mean:.2f}ms, max {max_latency:.2f}ms) exceeded "
        f"<{DUPLICATE_LOOKUP_P95_THRESHOLD_MS:.0f}ms threshold. Samples: "
        + ",".join(f"{t:.1f}" for t in timings_sorted)
    )

    print(
        f"[PERF] customer duplicate create p95={p95:.2f}ms mean={mean:.2f}ms max={max_latency:.2f}ms "
        f"samples={len(timings_sorted)}"
    )
