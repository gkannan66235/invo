"""Integration test for invoice timestamp immutability & update behavior (T058 / FR-019).

Verifies:
 1. created_at is set on creation and never changes after updates.
 2. updated_at reflects last modification and changes on update operations.
 3. Listing endpoint returns the same timestamps as detail endpoint (no mutation on read).
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

import pytest


def _extract_invoice(body: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(body, dict) and "data" in body and isinstance(body["data"], dict):
        return body["data"]
    return body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invoice_timestamps_immutability_and_update(auth_client):  # noqa: D401
    # Create invoice
    payload = {
        "customer_name": "Timestamp Test Co",
        "customer_phone": "+919876543212",
        "service_type": "diagnostics",
        "service_description": "Initial timestamp test",
        "amount": 111.0,
        "gst_rate": 18.0,
    }
    create_resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    inv_created = _extract_invoice(create_resp.json())

    invoice_id = inv_created["id"]

    # Fetch detail to capture authoritative timestamps
    detail_resp_1 = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
    assert detail_resp_1.status_code == 200, detail_resp_1.text
    inv_detail_1 = _extract_invoice(detail_resp_1.json())

    created_at_1 = inv_detail_1["created_at"]
    updated_at_1 = inv_detail_1["updated_at"]

    assert created_at_1, "created_at missing"
    assert updated_at_1, "updated_at missing"

    # Parse to ensure valid ISO 8601
    dt_created_1 = datetime.fromisoformat(created_at_1)
    dt_updated_1 = datetime.fromisoformat(updated_at_1)
    assert dt_updated_1 >= dt_created_1

    # Ensure a slight time delta before update
    await asyncio.sleep(0.05)

    # Patch invoice (amount change triggers update)
    patch_resp = await auth_client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"amount": 222.0}
    )
    assert patch_resp.status_code == 200, patch_resp.text

    # Fetch detail again
    detail_resp_2 = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
    assert detail_resp_2.status_code == 200, detail_resp_2.text
    inv_detail_2 = _extract_invoice(detail_resp_2.json())

    created_at_2 = inv_detail_2["created_at"]
    updated_at_2 = inv_detail_2["updated_at"]

    # created_at immutable
    assert created_at_2 == created_at_1, (
        f"created_at changed after update: before={created_at_1} after={created_at_2}"
    )

    # updated_at changed
    assert updated_at_2 != updated_at_1, (
        f"updated_at did not change after update: before={updated_at_1} after={updated_at_2}"
    )
    dt_updated_2 = datetime.fromisoformat(updated_at_2)
    assert dt_updated_2 >= dt_updated_1

    # List endpoint should reflect same timestamps (no mutation by read)
    list_resp = await auth_client.get("/api/v1/invoices/")
    assert list_resp.status_code == 200, list_resp.text
    list_body = list_resp.json()
    invoices = list_body.get("data", list_body)
    matching = [i for i in invoices if i.get("id") == invoice_id]
    assert matching, "Invoice not found in list response"
    list_invoice = matching[0]
    assert list_invoice["created_at"] == created_at_2
    assert list_invoice["updated_at"] == updated_at_2
