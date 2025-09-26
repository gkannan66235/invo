import pytest
from httpx import AsyncClient

# Contract test skeleton for Customers API (T007)
# Focus: list/create/get/update with duplicate mobile warning flag.
# Will initially fail until service & router implemented.


@pytest.mark.asyncio
async def test_create_customer_duplicate_warning_flag(app_client: AsyncClient):
    # Create first customer
    r1 = await app_client.post('/api/v1/customers', json={
        'name': 'Alpha Co',
        'phone': '+91 9876543210'
    })
    assert r1.status_code in (200, 201)

    # Create second customer with same phone (different formatting)
    r2 = await app_client.post('/api/v1/customers', json={
        'name': 'Alpha Duplicate',
        'phone': '98765 43210'
    })
    # Expect success but body contains duplicate_warning true
    assert r2.status_code in (200, 201)
    body2 = r2.json()
    assert body2.get(
        'duplicate_warning') is True, 'Expected duplicate_warning true for normalized match'


@pytest.mark.asyncio
async def test_list_customers_includes_normalized_mobile(app_client: AsyncClient):
    r = await app_client.get('/api/v1/customers')
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        sample = data[0]
        # Expect mobile_normalized field present (even if null for legacy)
        assert 'mobile_normalized' in sample


@pytest.mark.asyncio
async def test_update_customer_mobile_normalizes(app_client: AsyncClient):
    # Create a customer
    r = await app_client.post('/api/v1/customers', json={'name': 'Norm Test', 'phone': '+91-9123456789'})
    assert r.status_code in (200, 201)
    # Real implementation returns UUID string; use it directly
    cid = r.json()['id']

    # Update with alternative formatting
    r2 = await app_client.patch(f'/api/v1/customers/{cid}', json={'phone': '91234 56789'})
    assert r2.status_code == 200
    body = r2.json()
    assert body.get('mobile_normalized') == '9123456789'
