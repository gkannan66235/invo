import pytest
from httpx import AsyncClient

# Integration test skeleton (T016) Settings change prospective GST effect.
# Placeholder: we record old rate then set new and expect subsequent invoice to use new rate snapshot.


@pytest.mark.asyncio
async def test_gst_rate_change_affects_future_invoice(app_client: AsyncClient, seeded_customer_id):
    r_get = await app_client.get('/api/v1/settings')
    assert r_get.status_code == 200
    _ = r_get.json().get('gst_default_rate')  # baseline rate (unused placeholder)

    r_patch = await app_client.patch('/api/v1/settings', json={'gst_default_rate': '19.00'})
    assert r_patch.status_code in (200, 204)

    # Create an invoice after settings change
    inv_payload = {
        'customer_id': seeded_customer_id,
        'service_type': 'repair',
        'place_of_supply': 'KA',
        'subtotal': '100.00',
        'gst_rate': '19.00',
        'gst_amount': '19.00',
        'total_amount': '119.00'
    }
    r_inv = await app_client.post('/api/v1/invoices', json=inv_payload)
    assert r_inv.status_code in (200, 201)
    data = r_inv.json()
    # Snapshot should reflect 19.00 (or string variant) once implementation enforced
    assert 'gst_rate_snapshot' in data
