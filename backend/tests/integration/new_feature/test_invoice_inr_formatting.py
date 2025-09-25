import pytest
from httpx import AsyncClient

# Integration test skeleton (T014) verifying invoice INR totals.

@pytest.mark.asyncio
async def test_invoice_amounts_in_inr(app_client: AsyncClient, seeded_customer_id):
    payload = {
        'customer_id': seeded_customer_id,
        'service_type': 'repair',
        'place_of_supply': 'KA',
        'subtotal': '500.00',
        'gst_rate': '18.00',
        'gst_amount': '90.00',
        'total_amount': '590.00'
    }
    r = await app_client.post('/api/v1/invoices', json=payload)
    assert r.status_code in (200, 201)
    body = r.json()
    assert body['total_amount'] == '590.00'
