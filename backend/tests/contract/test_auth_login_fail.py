import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient):
    """T008: Wrong password returns standardized 401 error schema (FR-001, FR-024)."""
    response = await async_client.post(
        "/api/v1/auth/login", json={"username": "test_admin", "password": "wrong_password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    body = response.json()
    assert body.get("status") == "error"
    error = body.get("error") or {}
    assert error.get("code") in {"UNAUTHORIZED", "AUTH_INVALID_CREDENTIALS"}
    assert "message" in error
