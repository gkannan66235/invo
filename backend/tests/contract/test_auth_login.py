"""
Contract tests for authentication endpoints.
Tests POST /auth/login endpoint according to API specification.
"""

import pytest
from httpx import AsyncClient
from fastapi import status


class TestAuthLogin:
    """Contract tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, async_client: AsyncClient):
        """Test successful login with valid credentials."""
        request_payload = {
            "username": "test_admin",
            "password": "secure_password"
        }

        response = await async_client.post("/api/v1/auth/login", json=request_payload)

        # Verify response status
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure according to API contract
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data

        data = response_data["data"]
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Verify token type
        assert data["token_type"] == "bearer"

        # Verify expires_in is positive integer
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

        # Verify user object structure
        user = data["user"]
        assert "id" in user
        assert "username" in user
        assert "full_name" in user
        assert "role" in user
        assert "gst_preference" in user

        # Verify user values
        assert user["username"] == "test_admin"
        assert user["role"] in ["admin", "operator", "viewer"]
        assert isinstance(user["gst_preference"], bool)

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, async_client: AsyncClient):
        """Test login failure with invalid credentials."""
        request_payload = {
            "username": "invalid_user",
            "password": "wrong_password"
        }

        response = await async_client.post("/api/v1/auth/login", json=request_payload)

        # Verify response status
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "error" in response_data

        error = response_data["error"]
        assert "code" in error
        assert "message" in error
        # After T020: standardized code AUTH_INVALID_CREDENTIALS (keep backward compatibility for interim)
        assert error["code"] in {"UNAUTHORIZED", "AUTH_INVALID_CREDENTIALS"}

    @pytest.mark.asyncio
    async def test_login_with_missing_username(self, async_client: AsyncClient):
        """Test login failure with missing username."""
        request_payload = {
            "password": "some_password"
        }

        response = await async_client.post("/api/v1/auth/login", json=request_payload)

        # Verify validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "error" in response_data
        assert response_data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_login_with_missing_password(self, async_client: AsyncClient):
        """Test login failure with missing password."""
        request_payload = {
            "username": "test_admin"
        }

        response = await async_client.post("/api/v1/auth/login", json=request_payload)

        # Verify validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "error" in response_data
        assert response_data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_login_with_empty_payload(self, async_client: AsyncClient):
        """Test login failure with empty request payload."""
        response = await async_client.post("/api/v1/auth/login", json={})

        # Verify validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_response_time_constitutional_requirement(self, async_client: AsyncClient):
        """Test that login response time meets constitutional requirement (<200ms)."""
        import time

        request_payload = {
            "username": "test_admin",
            "password": "secure_password"
        }

        start_time = time.time()
        response = await async_client.post("/api/v1/auth/login", json=request_payload)
        end_time = time.time()

        # Calculate response time in milliseconds
        response_time_ms = (end_time - start_time) * 1000

        # Verify constitutional requirement: API responses <200ms
        assert response_time_ms < 200, f"Login response time {response_time_ms:.1f}ms exceeds constitutional requirement of 200ms"

        # Also verify successful response
        assert response.status_code == status.HTTP_200_OK


# Test data fixtures
@pytest.fixture
def valid_login_payload():
    """Valid login request payload."""
    return {
        "username": "test_admin",
        "password": "secure_password"
    }


@pytest.fixture
def expected_login_response_structure():
    """Expected structure of successful login response."""
    return {
        "status": "success",
        "data": {
            "access_token": str,
            "token_type": "bearer",
            "expires_in": int,
            "user": {
                "id": str,
                "username": str,
                "full_name": str,
                "role": str,
                "gst_preference": bool
            }
        }
    }
