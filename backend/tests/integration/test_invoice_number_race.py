import asyncio
import re
from typing import List

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invoice_number_concurrent_creation_unique(auth_client: AsyncClient):
    """T062: Concurrency test ensuring invoice number uniqueness & sequence integrity.

    Maps FR-005 (invoice number format) & NFR-002 (performance/reliability under load).

    Strategy:
      - Spawn N concurrent create invoice requests after a barrier.
      - Collect returned invoice numbers.
      - Assert: all unique, pattern matches INV-YYYYMMDD-NNNN, and sequence numbers form
        a contiguous increasing series (no gaps) relative to their min value.
    """
    N = 25  # moderate concurrency to expose race without overloading local DB
    start_barrier = asyncio.Event()
    pattern = re.compile(r"INV-(\d{8})-(\d{4})")

    async def create_one(i: int):
        await start_barrier.wait()
        payload = {
            "customerName": f"RaceUser{i}",
            # Valid Indian mobile numbers: 9xxxxxxxxx range
            "customerPhone": f"98{76500000 + i:07d}",
            "amount": 10 + i,  # vary amount a bit
            "gstRate": 18,
        }
        resp = await auth_client.post("/api/v1/invoices/", json=payload)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        data = body.get("data", body)
        inv_number = data["invoice_number"]
        m = pattern.fullmatch(inv_number)
        assert m, inv_number
        date_part, seq_part = m.group(1), int(m.group(2))
        return date_part, seq_part, inv_number

    tasks: List[asyncio.Task] = []
    for i in range(N):
        tasks.append(asyncio.create_task(create_one(i)))

    # Let all tasks reach the barrier
    await asyncio.sleep(0)
    start_barrier.set()
    results = await asyncio.gather(*tasks)

    date_parts = {r[0] for r in results}
    seqs = [r[1] for r in results]
    numbers = [r[2] for r in results]

    # All share same date segment (expected during single test run)
    assert len(
        date_parts) == 1, f"Expected single date segment, got {date_parts}"

    # Uniqueness
    assert len(numbers) == len(
        set(numbers)), "Duplicate invoice numbers detected"

    # Contiguous sequence relative to min (no gaps introduced by retry logic)
    seqs_sorted = sorted(seqs)
    base = seqs_sorted[0]
    for idx, val in enumerate(seqs_sorted):
        assert val - \
            base == idx, f"Non-contiguous sequence at position {idx}: {seqs_sorted}"

    # Optional: ensure monotonic increase across original order (not required but informative)
    # This may fail if interleaving occurs; uniqueness + contiguity are primary guarantees.
