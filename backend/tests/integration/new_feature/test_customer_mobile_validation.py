import pytest
from httpx import AsyncClient

# Integration test skeleton (T012) invalid Indian mobile rejection.


@pytest.mark.asyncio
async def test_invalid_mobile_rejected(app_client: AsyncClient):
    r = await app_client.post('/api/v1/customers', json={'name': 'Bad Mobile', 'phone': '+91 1234567890'})
    assert r.status_code in (400, 422)
