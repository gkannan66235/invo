import pytest
from httpx import AsyncClient

# T007: Customers API contract tests
# Focus: list/create/get/update shapes, duplicate warning behavior, auth envelope on list without token.


@pytest.mark.asyncio
async def test_customers_list_requires_auth(async_client: AsyncClient):
    # async_client provides no Authorization header
    resp = await async_client.get("/api/v1/customers")
    assert resp.status_code == 401, f"Expected 401 for unauth list, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("status") == "error"
    assert body.get("error", {}).get("code") == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_create_and_get_customer_duplicate_warning(auth_client: AsyncClient):
    # First create
    payload = {"name": "Acme Corp", "phone": "+91-9876543210",
               "email": "acme@example.com"}
    r1 = await auth_client.post("/api/v1/customers", json=payload)
    assert r1.status_code == 201, r1.text
    c1 = r1.json()["data"]["customer"]
    assert c1["duplicate_warning"] is False
    assert c1["mobile_normalized"] == "9876543210"

    # Second create with same phone triggers duplicate_warning True
    r2 = await auth_client.post("/api/v1/customers", json={"name": "Acme Corp Duplicate", "phone": "9876543210"})
    assert r2.status_code == 201, r2.text
    c2 = r2.json()["data"]["customer"]
    assert c2["duplicate_warning"] is True

    # List customers (auth)
    lst = await auth_client.get("/api/v1/customers")
    assert lst.status_code == 200
    lbody = lst.json()
    assert lbody.get("status") == "success"
    assert "customers" in lbody["data"]
    assert "pagination" in lbody["data"]
    assert any(c["duplicate_warning"] for c in lbody["data"]
               ["customers"])  # at least one duplicate flagged

    # Get single
    gid = await auth_client.get(f"/api/v1/customers/{c1['id']}")
    assert gid.status_code == 200
    gbody = gid.json()["data"]["customer"]
    assert gbody["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_update_customer_contract(auth_client: AsyncClient):
    r = await auth_client.post("/api/v1/customers", json={"name": "UpdateCo", "phone": "9990011223"})
    assert r.status_code == 201, r.text
    cid = r.json()["data"]["customer"]["id"]

    upr = await auth_client.patch(f"/api/v1/customers/{cid}", json={"email": "new@example.com"})
    assert upr.status_code == 200
    updated = upr.json()["data"]["customer"]
    assert updated["email"] == "new@example.com"
