import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_customer_duplicate_warning_basic(auth_client: AsyncClient):
    """First create should have duplicate_warning False; second with same mobile True.

    Uses minimal payload (name + phone). Relies on per-test SQLite isolation fixture to
    guarantee clean state in FAST_TESTS mode.
    """
    payload1 = {"name": "DupWarn One", "phone": "+91 9876543210"}
    r1 = await auth_client.post("/api/v1/customers", json=payload1)
    assert r1.status_code == 201, r1.text
    body1 = r1.json()
    data1 = body1.get("data", body1)
    cust1 = data1.get("customer", data1)
    assert cust1.get("duplicate_warning") is False

    payload2 = {"name": "DupWarn Two",
                "phone": "9876543210"}  # normalized same
    r2 = await auth_client.post("/api/v1/customers", json=payload2)
    assert r2.status_code == 201, r2.text
    body2 = r2.json()
    data2 = body2.get("data", body2)
    cust2 = data2.get("customer", data2)
    assert cust2.get("duplicate_warning") is True, cust2

    # Third create (different phone) remains isolated
    payload3 = {"name": "DupWarn Three", "phone": "9999988888"}
    r3 = await auth_client.post("/api/v1/customers", json=payload3)
    assert r3.status_code == 201
    body3 = r3.json()
    data3 = body3.get("data", body3)
    cust3 = data3.get("customer", data3)
    assert cust3.get("duplicate_warning") is False


@pytest.mark.asyncio
async def test_customer_duplicate_warning_update_transition(auth_client: AsyncClient):
    """Changing a customer's phone to collide with an existing one should set duplicate_warning.

    Flow:
      1. Create base customer A (phone X)
      2. Create customer B (phone Y) -> no warning
      3. Update B's phone to X -> expect duplicate_warning True
    """
    create_a = {"name": "Base A", "phone": "9876500000"}
    ra = await auth_client.post("/api/v1/customers", json=create_a)
    assert ra.status_code == 201
    body_a = ra.json()
    data_a = body_a.get("data", body_a)
    cust_a = data_a.get("customer", data_a)
    assert cust_a["duplicate_warning"] is False

    create_b = {"name": "Base B", "phone": "9999977777"}
    rb = await auth_client.post("/api/v1/customers", json=create_b)
    assert rb.status_code == 201
    body_b = rb.json()
    data_b = body_b.get("data", body_b)
    cust_b = data_b.get("customer", data_b)
    assert cust_b["duplicate_warning"] is False

    # Update B to phone of A
    cust_b_id = cust_b["id"]
    upd = await auth_client.patch(f"/api/v1/customers/{cust_b_id}", json={"phone": "9876500000"})
    assert upd.status_code == 200, upd.text
    body_upd = upd.json()
    data_upd = body_upd.get("data", body_upd)
    cust_upd = data_upd.get("customer", data_upd)
    assert cust_upd["duplicate_warning"] is True

    # Re-fetch A to verify serialization still shows duplicate_warning True now that there are two
    refetch_a = await auth_client.get(f"/api/v1/customers/{cust_a['id']}")
    assert refetch_a.status_code == 200
    body_a2 = refetch_a.json()
    data_a2 = body_a2.get("data", body_a2)
    cust_a2 = data_a2.get("customer", data_a2)
    assert cust_a2["duplicate_warning"] is True
