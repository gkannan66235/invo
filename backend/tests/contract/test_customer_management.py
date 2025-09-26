"""
Contract tests for customer management endpoints.
Tests GET /customers endpoint according to API specification.
"""

import pytest
from httpx import AsyncClient
from fastapi import status


class TestCustomerList:
    """Contract tests for GET /customers endpoint."""

    @pytest.mark.asyncio
    async def test_list_customers_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful retrieval of customers list."""
        response = await async_client.get("/api/v1/customers", headers=auth_headers)

        # Verify response status
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure according to API contract
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data

        data = response_data["data"]
        assert "customers" in data
        assert "pagination" in data

        # Verify pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_previous" in pagination

    @pytest.mark.asyncio
    async def test_list_customers_structure(self, async_client: AsyncClient, auth_headers: dict):
        """Test that customers have correct structure."""
        response = await async_client.get("/api/v1/customers", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If customers exist, verify their structure
        if data["customers"]:
            customer = data["customers"][0]
            required_fields = [
                "id", "name", "email", "phone", "gst_number", "address",
                "city", "state", "pin_code", "customer_type", "is_active",
                "credit_limit", "outstanding_amount", "created_at", "updated_at"
            ]

            for field in required_fields:
                assert field in customer, f"Missing required field: {field}"

            # Verify data types
            assert isinstance(customer["credit_limit"], (int, float))
            assert isinstance(customer["outstanding_amount"], (int, float))
            assert isinstance(customer["is_active"], bool)
            assert customer["customer_type"] in ["individual", "business"]

            # Verify address structure if present
            address = customer["address"]
            assert "street" in address
            assert "area" in address
            assert "landmark" in address

    @pytest.mark.asyncio
    async def test_list_customers_with_search(self, async_client: AsyncClient, auth_headers: dict):
        """Test customers list with search parameter."""
        params = {"search": "john"}
        response = await async_client.get("/api/v1/customers", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Response should be valid regardless of search results
        assert "customers" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_list_customers_by_type(self, async_client: AsyncClient, auth_headers: dict):
        """Test customers list filtered by customer type."""
        params = {"customer_type": "business"}
        response = await async_client.get("/api/v1/customers", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If customers exist, verify they match the type filter
        for customer in data["customers"]:
            assert customer["customer_type"] == "business"

    @pytest.mark.asyncio
    async def test_list_customers_unauthorized(self, async_client: AsyncClient):
        """Test customers list without authentication."""
        response = await async_client.get("/api/v1/customers")

        # Should return unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_list_customers_response_time_constitutional_requirement(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that customers list response time meets constitutional requirement (<200ms)."""
        import time

        start_time = time.time()
        response = await async_client.get("/api/v1/customers", headers=auth_headers)
        end_time = time.time()

        # Calculate response time in milliseconds
        response_time_ms = (end_time - start_time) * 1000

        # Verify constitutional requirement: API responses <200ms
        assert response_time_ms < 200, (
            f"Customers list response time {response_time_ms:.1f}ms exceeds "
            "constitutional requirement of 200ms"
        )

        # Also verify successful response
        assert response.status_code == status.HTTP_200_OK


class TestCustomerCreate:
    """Contract tests for POST /customers endpoint."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful customer creation."""
        customer_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "gst_number": "29ABCDE1234F1Z5",
            "address": {
                "street": "123 Main St",
                "area": "Central Market",
                "landmark": "Near Bank",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pin_code": "400001"
            },
            "customer_type": "business",
            "credit_limit": 50000.00
        }

        response = await async_client.post("/api/v1/customers", json=customer_data, headers=auth_headers)

        # Verify response status
        assert response.status_code == status.HTTP_201_CREATED

        # Verify response structure
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data

        # Verify created customer data
        customer = response_data["data"]["customer"]
        assert customer["name"] == customer_data["name"]
        assert customer["email"] == customer_data["email"]
        assert "id" in customer
        assert "created_at" in customer

    @pytest.mark.asyncio
    async def test_create_customer_missing_required_field(self, async_client: AsyncClient, auth_headers: dict):
        """Test customer creation with missing required field."""
        customer_data = {
            "email": "john@example.com",
            "phone": "9876543210"
            # Missing name field
        }

        response = await async_client.post("/api/v1/customers", json=customer_data, headers=auth_headers)

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_customer_invalid_gst_number(self, async_client: AsyncClient, auth_headers: dict):
        """Test customer creation with invalid GST number format."""
        customer_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "gst_number": "INVALID_GST",  # Invalid format
            "customer_type": "business"
        }

        response = await async_client.post("/api/v1/customers", json=customer_data, headers=auth_headers)

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify error mentions GST validation
        response_data = response.json()
        assert "gst" in response_data["error"]["message"].lower()


# Placeholder fixtures removed; real fixtures provided in tests/conftest.py
