import pytest
from httpx import AsyncClient

# Contract test skeleton for Settings API (T011)
# Ensures get/patch flows and gst_default_rate prospective change semantics placeholder.

@pytest.mark.asyncio
async def test_get_settings(app_client: AsyncClient):
    r = await app_client.get('/api/v1/settings')
    assert r.status_code == 200
    body = r.json()
    assert 'gst_default_rate' in body

@pytest.mark.asyncio
async def test_patch_settings_updates_gst_rate(app_client: AsyncClient):
    r = await app_client.patch('/api/v1/settings', json={'gst_default_rate': '18.00'})
    # Might be 200/204 depending on implementation – allow either for contract start.
    assert r.status_code in (200, 204)
