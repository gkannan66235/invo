"""
Contract tests for inventory management endpoints.
Tests GET /inventory/items endpoint according to API specification.
"""

import pytest
from httpx import AsyncClient
from fastapi import status


class TestInventoryList:
    """Contract tests for GET /inventory/items endpoint."""

    @pytest.mark.asyncio
    async def test_list_inventory_items_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful retrieval of inventory items list."""
        response = await async_client.get("/api/v1/inventory/items", headers=auth_headers)

        # Verify response status
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure according to API contract
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data

        data = response_data["data"]
        assert "items" in data
        assert "pagination" in data

        # Verify pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_previous" in pagination

        # Verify pagination values are valid
        assert isinstance(pagination["page"], int)
        assert pagination["page"] >= 1
        assert isinstance(pagination["page_size"], int)
        assert pagination["page_size"] >= 1
        assert isinstance(pagination["total_items"], int)
        assert pagination["total_items"] >= 0

    @pytest.mark.asyncio
    async def test_list_inventory_items_structure(self, async_client: AsyncClient, auth_headers: dict):
        """Test that inventory items have correct structure."""
        response = await async_client.get("/api/v1/inventory/items", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If items exist, verify their structure
        if data["items"]:
            item = data["items"][0]
            required_fields = [
                "id", "product_code", "description", "hsn_code", "gst_rate",
                "current_stock", "minimum_stock_level", "purchase_price",
                "selling_price", "category", "is_active", "created_at", "updated_at"
            ]

            for field in required_fields:
                assert field in item, f"Missing required field: {field}"

            # Verify data types
            assert isinstance(item["gst_rate"], (int, float))
            assert isinstance(item["current_stock"], int)
            assert isinstance(item["minimum_stock_level"], int)
            assert isinstance(item["purchase_price"], (int, float))
            assert isinstance(item["selling_price"], (int, float))
            assert isinstance(item["is_active"], bool)
            assert item["category"] in [
                "pump", "motor", "spare_part", "service"]

            # Verify supplier structure if present
            if "supplier" in item:
                supplier = item["supplier"]
                assert "id" in supplier
                assert "name" in supplier

    @pytest.mark.asyncio
    async def test_list_inventory_with_pagination(self, async_client: AsyncClient, auth_headers: dict):
        """Test inventory list with pagination parameters."""
        params = {"page": 1, "page_size": 10}
        response = await async_client.get("/api/v1/inventory/items", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Verify pagination respects parameters
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10
        assert len(data["items"]) <= 10

    @pytest.mark.asyncio
    async def test_list_inventory_with_category_filter(self, async_client: AsyncClient, auth_headers: dict):
        """Test inventory list with category filter."""
        params = {"category": "pump"}
        response = await async_client.get("/api/v1/inventory/items", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If items exist, verify they match the category filter
        for item in data["items"]:
            assert item["category"] == "pump"

    @pytest.mark.asyncio
    async def test_list_inventory_with_search(self, async_client: AsyncClient, auth_headers: dict):
        """Test inventory list with search parameter."""
        params = {"search": "pump"}
        response = await async_client.get("/api/v1/inventory/items", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Response should be valid regardless of search results
        assert "items" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_list_inventory_low_stock_filter(self, async_client: AsyncClient, auth_headers: dict):
        """Test inventory list with low stock filter."""
        params = {"low_stock": True}
        response = await async_client.get("/api/v1/inventory/items", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If items exist, verify they are below minimum stock level
        for item in data["items"]:
            assert item["current_stock"] <= item["minimum_stock_level"]

    @pytest.mark.asyncio
    async def test_list_inventory_unauthorized(self, async_client: AsyncClient):
        """Test inventory list without authentication."""
        response = await async_client.get("/api/v1/inventory/items")

        # Should return unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_list_inventory_response_time_constitutional_requirement(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that inventory list response time meets constitutional requirement (<200ms)."""
        import time

        start_time = time.time()
        response = await async_client.get("/api/v1/inventory/items", headers=auth_headers)
        end_time = time.time()

        # Calculate response time in milliseconds
        response_time_ms = (end_time - start_time) * 1000

        # Verify constitutional requirement: API responses <200ms
        assert response_time_ms < 200, (
            f"Inventory list response time {response_time_ms:.1f}ms exceeds "
            "constitutional requirement of 200ms"
        )

        # Also verify successful response
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_list_inventory_with_invalid_page_size(self, async_client: AsyncClient, auth_headers: dict):
        """Test inventory list with invalid page size (too large)."""
        params = {"page_size": 1000}  # Exceeds max of 100
        response = await async_client.get("/api/v1/inventory/items", params=params, headers=auth_headers)

        # Should either cap at 100 or return validation error
        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()["data"]
            assert data["pagination"]["page_size"] <= 100


# Placeholder fixtures removed; using shared fixtures from tests/conftest.py
