import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_invoice_download_audit_flow(auth_client: AsyncClient):
    # Create an invoice first
    payload = {
        "customer_name": "AuditUser",
        "customer_phone": "9876501234",
        "service_type": "inspection",
        "service_description": "Site inspection",
        "amount": 750,
        "gst_rate": 18
    }
    create_resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    invoice_id = create_resp.json()["data"]["id"]

    # Record a PDF download
    dl_resp = await auth_client.post(f"/api/v1/invoices/{invoice_id}/download/pdf")
    assert dl_resp.status_code == 201, dl_resp.text
    data = dl_resp.json()["data"]
    assert data["action"] == "pdf"
    assert data["invoice_id"] == invoice_id

    # Record a print action
    pr_resp = await auth_client.post(f"/api/v1/invoices/{invoice_id}/download/print")
    assert pr_resp.status_code == 201, pr_resp.text
    pdata = pr_resp.json()["data"]
    assert pdata["action"] == "print"
    assert pdata["invoice_id"] == invoice_id

    # Invalid action
    bad_resp = await auth_client.post(f"/api/v1/invoices/{invoice_id}/download/other")
    assert bad_resp.status_code == 400
    assert "Invalid action" in bad_resp.text
