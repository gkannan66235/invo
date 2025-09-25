import pytest
from httpx import AsyncClient

# Integration test skeleton (T015) PDF generation + audit log placeholder.
# Initially only checks PDF response; later we will query audit table.

@pytest.mark.asyncio
async def test_invoice_pdf_generates(app_client: AsyncClient, seeded_invoice_id):
    r = await app_client.get(f'/api/v1/invoices/{seeded_invoice_id}/pdf')
    assert r.status_code == 200
    assert r.content[:4] == b'%PDF'
