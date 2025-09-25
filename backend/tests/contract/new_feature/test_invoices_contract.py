import pytest
from httpx import AsyncClient

# Contract test skeleton for Invoices API (T009)
# Ensures INR currency semantics & snapshot placeholders presence.


@pytest.mark.asyncio
async def test_create_invoice_includes_snapshots(app_client: AsyncClient, seeded_customer_id):
    # Create minimal invoice payload (lines will be introduced later)
    payload = {
        'customer_id': seeded_customer_id,
        'service_type': 'general_service',
        'place_of_supply': 'KA',
        'subtotal': '1000.00',
        'gst_rate': '18.00',
        'gst_amount': '180.00',
        'total_amount': '1180.00'
    }
    r = await app_client.post('/api/v1/invoices', json=payload)
    assert r.status_code in (200, 201)
    data = r.json()
    # Snapshot fields expected (may be null initially until service fills them)
    assert 'branding_snapshot' in data
    assert 'gst_rate_snapshot' in data
    assert 'settings_snapshot' in data


@pytest.mark.asyncio
async def test_list_invoices_customer_filter(app_client: AsyncClient, seeded_customer_id):
    r = await app_client.get(f'/api/v1/invoices?customer_id={seeded_customer_id}')
    assert r.status_code == 200
    invoices = r.json()
    assert isinstance(invoices, list)


@pytest.mark.asyncio
async def test_invoice_detail_includes_lines(app_client: AsyncClient, seeded_invoice_id):
    r = await app_client.get(f'/api/v1/invoices/{seeded_invoice_id}')
    assert r.status_code == 200
    body = r.json()
    assert 'lines' in body  # even if empty list early
