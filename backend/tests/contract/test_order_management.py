"""
Contract tests for order management endpoints.
Tests POST /orders endpoint according to API specification.
"""

import pytest
from httpx import AsyncClient
from fastapi import status


class TestOrderCreate:
    """Contract tests for POST /orders endpoint."""

    @pytest.mark.asyncio
    async def test_create_order_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful order creation."""
        order_data = {
            "customer_id": 1,
            "order_type": "sale",
            "items": [
                {
                    "inventory_item_id": 1,
                    "quantity": 2,
                    "unit_price": 1500.00,
                    "discount_percentage": 5.0
                },
                {
                    "inventory_item_id": 2,
                    "quantity": 1,
                    "unit_price": 2500.00,
                    "discount_percentage": 0.0
                }
            ],
            "gst_treatment": "taxable",
            "place_of_supply": "Maharashtra",
            "payment_terms": "net_30",
            "notes": "Urgent delivery required"
        }
        response = await async_client.post("/api/v1/orders", json=order_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["status"] == "success"
        order = response_data["data"]["order"]
        assert order["customer_id"] == order_data["customer_id"]
        assert order["order_type"] == order_data["order_type"]
        assert order["total_amount"] > 0
        assert len(order["items"]) == 2
        for item in order["items"]:
            assert "id" in item and "gst_amount" in item

    @pytest.mark.asyncio
    async def test_create_order_missing_items(self, async_client: AsyncClient, auth_headers: dict):
        """Test order creation without items."""
        order_data = {
            "customer_id": 1,
            "order_type": "sale",
            "items": []  # Empty items array
        }

        response = await async_client.post("/api/v1/orders", json=order_data, headers=auth_headers)

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "VALIDATION_ERROR"
        assert "items" in response_data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_create_order_invalid_customer(self, async_client: AsyncClient, auth_headers: dict):
        """Test order creation with non-existent customer."""
        order_data = {
            "customer_id": 99999,  # Non-existent customer
            "order_type": "sale",
            "items": [
                {
                    "inventory_item_id": 1,
                    "quantity": 1,
                    "unit_price": 1000.00
                }
            ]
        }

        response = await async_client.post("/api/v1/orders", json=order_data, headers=auth_headers)

        # Should return not found error
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify error response
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "CUSTOMER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_order_insufficient_inventory(self, async_client: AsyncClient, auth_headers: dict):
        """Test order creation with insufficient inventory."""
        order_data = {
            "customer_id": 1,
            "order_type": "sale",
            "items": [
                {
                    "inventory_item_id": 1,
                    "quantity": 1000,  # Exceeds available stock
                    "unit_price": 1500.00
                }
            ]
        }

        response = await async_client.post("/api/v1/orders", json=order_data, headers=auth_headers)

        # Should return business rule violation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify error response
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INSUFFICIENT_INVENTORY"

    @pytest.mark.asyncio
    async def test_create_order_response_time_constitutional_requirement(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that order creation response time meets constitutional requirement (<200ms)."""
        import time

        order_data = {
            "customer_id": 1,
            "order_type": "sale",
            "items": [
                {
                    "inventory_item_id": 1,
                    "quantity": 1,
                    "unit_price": 1500.00
                }
            ]
        }

        start_time = time.time()
        resp_time_call = await async_client.post(
            "/api/v1/orders", json=order_data, headers=auth_headers
        )
        end_time = time.time()

        # Calculate response time in milliseconds
        response_time_ms = (end_time - start_time) * 1000

        # Verify constitutional requirement: API responses <200ms
        assert response_time_ms < 200, (
            f"Order creation response time {response_time_ms:.1f}ms exceeds "
            "constitutional requirement of 200ms"
        )
        assert resp_time_call.status_code == status.HTTP_201_CREATED


class TestOrderList:
    """Contract tests for GET /orders endpoint."""

    @pytest.mark.asyncio
    async def test_list_orders_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful retrieval of orders list."""
        response = await async_client.get("/api/v1/orders", headers=auth_headers)

        # Verify response status
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data

        data = response_data["data"]
        assert "orders" in data
        assert "pagination" in data

        # Verify pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination

    @pytest.mark.asyncio
    async def test_list_orders_with_status_filter(self, async_client: AsyncClient, auth_headers: dict):
        """Test orders list with status filter."""
        params = {"status": "pending"}
        response = await async_client.get("/api/v1/orders", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # If orders exist, verify they match the status filter
        for order in data["orders"]:
            assert order["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_orders_by_date_range(self, async_client: AsyncClient, auth_headers: dict):
        """Test orders list with date range filter."""
        params = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        response = await async_client.get("/api/v1/orders", params=params, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Response should be valid
        assert "orders" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_list_orders_unauthorized(self, async_client: AsyncClient):
        """Test orders list without authentication."""
        response = await async_client.get("/api/v1/orders")

        # Should return unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verify error response structure
        response_data = response.json()
        assert response_data["status"] == "error"
        assert response_data["error"]["code"] == "UNAUTHORIZED"


# Placeholder fixtures removed; global fixtures used
