import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_invoice_create_invalid_due_date(auth_client: AsyncClient):
    """T047: Malformed due_date on create should yield 422 (FR-021).

    Accept either our standardized error envelope (status=error, code=VALIDATION_ERROR)
    or FastAPI/Pydantic default validation error structure (detail list), matching the
    approach used in earlier validation tests (T013).
    """
    payload = {
        "customer_name": "BadDueDateUser",
        "customer_phone": "9876500000",
        "amount": 50.0,
        # clearly invalid date string
        "due_date": "not-a-date",
    }
    resp = await auth_client.post("/api/v1/invoices/", json=payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp.text
    body = resp.json()
    # Two acceptable shapes:
    if isinstance(body, dict) and body.get("status") == "error":
        assert body.get("error", {}).get("code") == "VALIDATION_ERROR"
    else:
        # FastAPI default validation error shape
        assert "detail" in body


@pytest.mark.asyncio
async def test_invoice_update_invalid_due_date(auth_client: AsyncClient):
    """T047: Malformed due_date on update should also yield 422 (FR-021)."""
    # First create a valid invoice
    create_payload = {
        "customer_name": "DueDateUpdUser",
        "customer_phone": "9876511111",
        "amount": 75.0,
    }
    create_resp = await auth_client.post("/api/v1/invoices/", json=create_payload)
    assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.text
    inv_id = create_resp.json()["data"]["id"] if create_resp.json().get(
        "data") else create_resp.json()["id"]

    # Attempt invalid update
    patch_resp = await auth_client.patch(
        # invalid day
        f"/api/v1/invoices/{inv_id}", json={"due_date": "2025-02-30T10:00:00"}
    )
    assert patch_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, patch_resp.text
    body = patch_resp.json()
    if isinstance(body, dict) and body.get("status") == "error":
        assert body.get("error", {}).get("code") == "VALIDATION_ERROR"
    else:
        assert "detail" in body
