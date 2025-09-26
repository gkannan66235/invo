import pytest
from httpx import AsyncClient

# T008: Inventory API contract tests
# Ensures create/list/update behavior & validation envelope.


@pytest.mark.asyncio
async def test_inventory_create_list_update(auth_client: AsyncClient):
    # Create inventory item (fields based on model requirements)
    payload = {
        "product_code": "PUMP-001",
        "description": "Water Pump 1HP",
        "hsn_code": "840999",
        "gst_rate": 18,
        "selling_price": 2500,
        "category": "spare_part"
    }
    r = await auth_client.post("/api/v1/inventory", json=payload)
    assert r.status_code in (200, 201), r.text
    item = r.json()["data"].get("item") or r.json()[
        "data"]["inventory"] if "data" in r.json() else r.json()
    assert item["product_code"] == "PUMP-001"

    # List items
    lst = await auth_client.get("/api/v1/inventory")
    assert lst.status_code == 200
    lbody = lst.json()
    assert lbody.get("status") == "success"
    assert any(i["product_code"] == "PUMP-001" for i in lbody["data"]["items"])

    # Update (PATCH) - toggle is_active
    upd = await auth_client.patch(f"/api/v1/inventory/{item['id']}", json={"is_active": False})
    assert upd.status_code in (200, 202), upd.text
    updated = upd.json()["data"].get("item") or upd.json()[
        "data"].get("inventory")
    assert updated["is_active"] is False
