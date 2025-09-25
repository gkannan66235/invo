"""Integration test for metrics counters (T054).

Validates that invoice operation counters exposed via the Prometheus `/metrics` endpoint
increase after performing create/update/delete operations.

Relies on the native `invoice_operations_total{operation="..."}` counter emitted through
`record_invoice_operation()` which is invoked in the invoices router on each respective
operation (create/update/delete). This avoids depending on the OpenTelemetry exporter
stack and keeps the assertions deterministic.
"""
from __future__ import annotations

import re
from typing import Dict

import pytest


METRIC_NAME = "invoice_operations_total"
METRIC_LINE_RE = re.compile(r'^invoice_operations_total\{operation="(?P<op>[a-z_]+)"}\s+(?P<value>[0-9]+(?:\.[0-9]+)?)$')


def _parse_invoice_operation_metrics(metrics_text: str) -> Dict[str, float]:
    """Parse the Prometheus metrics text and extract invoice operation counts.

    Returns a mapping of operation -> value (float, though counters are integers in practice).
    Missing operations simply won't appear in the mapping.
    """
    values: Dict[str, float] = {}
    for line in metrics_text.splitlines():
        m = METRIC_LINE_RE.match(line.strip())
        if m:
            values[m.group("op")] = float(m.group("value"))
    return values


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invoice_operation_counters_increment(auth_client):  # noqa: D401
    # 1. Capture baseline metrics
    resp = await auth_client.get("/metrics")
    assert resp.status_code == 200, resp.text
    baseline = _parse_invoice_operation_metrics(resp.text)

    # Helper to fetch current counter mapping
    async def current():  # noqa: D401
        r = await auth_client.get("/metrics")
        assert r.status_code == 200, r.text
        return _parse_invoice_operation_metrics(r.text)

    # 2. Create an invoice
    create_payload = {
        "customer_name": "Metrics Test Co",
        # Use valid Indian mobile number pattern per validation logic (starts 6-9 and 10 digits)
        "customer_phone": "+919876543210",
        "service_type": "diagnostics",
        "service_description": "Full system diagnostics",
        "amount": 100.0,
        "gst_rate": 18.0,
    }
    create_resp = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    invoice = body.get("data", body)
    invoice_id = invoice["id"]

    after_create = await current()

    # 3. Update the invoice (PATCH)
    update_resp = await auth_client.patch(f"/api/v1/invoices/{invoice_id}", json={"amount": 150.0})
    assert update_resp.status_code == 200, update_resp.text
    after_update = await current()

    # 4. Delete the invoice
    delete_resp = await auth_client.delete(f"/api/v1/invoices/{invoice_id}")
    # Endpoint returns 204 with envelope in body (acceptable) or plain 204
    assert delete_resp.status_code == 204, delete_resp.text
    after_delete = await current()

    # Extract baseline values (default 0.0 if absent)
    base_create = baseline.get("create", 0.0)
    base_update = baseline.get("update", 0.0)
    base_delete = baseline.get("delete", 0.0)

    # Assert each counter increased by at least 1.0 relative to its baseline
    assert after_create.get("create", 0.0) >= base_create + 1, (
        f"Create counter did not increment: baseline={base_create}, after_create={after_create.get('create', 0.0)}"
    )
    assert after_update.get("update", 0.0) >= base_update + 1, (
        f"Update counter did not increment: baseline={base_update}, after_update={after_update.get('update', 0.0)}"
    )
    assert after_delete.get("delete", 0.0) >= base_delete + 1, (
        f"Delete counter did not increment: baseline={base_delete}, after_delete={after_delete.get('delete', 0.0)}"
    )

    # Bonus: Ensure create counter is monotonic across subsequent operations (no regression)
    assert after_update.get("create", 0.0) >= after_create.get("create", 0.0)
    assert after_delete.get("create", 0.0) >= after_update.get("create", 0.0)
