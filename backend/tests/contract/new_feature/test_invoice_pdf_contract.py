import pytest
from httpx import AsyncClient

# Contract test skeleton for Invoice PDF endpoint (T010)
# Verifies endpoint + audit side effect (later). For now, just status/content-type.


@pytest.mark.asyncio
async def test_invoice_pdf_download(app_client: AsyncClient, seeded_invoice_id):
    r = await app_client.get(f'/api/v1/invoices/{seeded_invoice_id}/pdf')
    # Expect 200 once implemented
    assert r.status_code == 200
    assert r.headers.get(
        'content-type') in ('application/pdf', 'application/octet-stream')
    assert r.content[:4] == b'%PDF'
