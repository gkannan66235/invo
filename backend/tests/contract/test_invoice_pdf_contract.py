import pytest
from httpx import AsyncClient

# T010: Invoice PDF download & audit contract test
# Validates /download/pdf audit trail (201) and /pdf content-type 200.


@pytest.mark.asyncio
async def test_invoice_pdf_download_contract(auth_client: AsyncClient):
    # Create invoice
    payload = {
        "customer_name": "PDF User",
        "customer_phone": "9012345678",
        "service_type": "service",
        "service_description": "General service",
        "amount": 500,
        "gst_rate": 18
    }
    r = await auth_client.post("/api/v1/invoices", json=payload)
    assert r.status_code == 201, r.text
    inv = r.json()["data"]

    # Audit endpoint (POST /download/pdf) -> 201 + envelope
    dl = await auth_client.post(f"/api/v1/invoices/{inv['id']}/download/pdf")
    assert dl.status_code == 201, dl.text
    dbody = dl.json()["data"] if "data" in dl.json() else dl.json()
    assert dbody["action"] == "pdf"
    assert dbody["invoice_id"] == inv["id"]

    # Direct PDF content GET /pdf -> 200 + application/pdf
    pdf = await auth_client.get(f"/api/v1/invoices/{inv['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
