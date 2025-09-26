import pytest
from httpx import AsyncClient

# T011: Settings API contract tests
# GET + PATCH (prospective GST rate update placeholder; persistence not yet implemented)


@pytest.mark.asyncio
async def test_settings_get_and_patch(auth_client: AsyncClient):
    # Initial GET
    g = await auth_client.get("/api/v1/settings")
    assert g.status_code == 200, g.text
    body = g.json()
    assert "gst_default_rate" in body
    original = body["gst_default_rate"]

    # PATCH update
    new_rate = original + 2 if isinstance(original, (int, float)) else 20
    p = await auth_client.patch("/api/v1/settings", json={"gst_default_rate": new_rate})
    assert p.status_code == 200, p.text
    pbody = p.json()
    assert pbody["gst_default_rate"] == new_rate

    # Idempotent re-read
    g2 = await auth_client.get("/api/v1/settings")
    assert g2.status_code == 200
    g2body = g2.json()
    assert g2body["gst_default_rate"] == new_rate
