import pytest
from httpx import AsyncClient

# Integration test skeleton (T013) duplicate mobile warning flow.

@pytest.mark.asyncio
async def test_duplicate_mobile_warning(app_client: AsyncClient):
    first = await app_client.post('/api/v1/customers', json={'name': 'A', 'phone': '9876543210'})
    assert first.status_code in (200, 201)
    second = await app_client.post('/api/v1/customers', json={'name': 'B', 'phone': '+91-98765 43210'})
    assert second.status_code in (200, 201)
    body = second.json()
    assert body.get('duplicate_warning') is True
