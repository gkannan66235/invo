"""
Test configuration and fixtures for contract tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient

from src.main import app
from src.config.database import get_async_db_dependency


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create async test client for FastAPI application.
    This fixture will be used by contract tests.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers() -> dict:
    """
    Authentication headers with JWT token.
    For now returns empty dict - will be implemented when auth is created.
    """
    # TODO: Implement proper JWT token generation for tests
    # This should create a valid JWT token for testing
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
async def db_session():
    """
    Database session fixture for tests.
    Creates a test database session.
    """
    # TODO: Implement test database session
    # This should create an isolated test database session
    async for session in get_async_db_dependency():
        yield session


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "name": "Test Customer",
        "email": "test@example.com",
        "phone": "9876543210",
        "gst_number": "29ABCDE1234F1Z5",
        "address": {
            "street": "123 Test Street",
            "area": "Test Area",
            "landmark": "Near Test Landmark",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pin_code": "400001"
        },
        "customer_type": "business",
        "credit_limit": 50000.00
    }


@pytest.fixture
def sample_inventory_item_data():
    """Sample inventory item data for testing."""
    return {
        "product_code": "PUMP001",
        "description": "Centrifugal Water Pump 1HP",
        "hsn_code": "8413",
        "gst_rate": 18.0,
        "current_stock": 10,
        "minimum_stock_level": 5,
        "purchase_price": 8000.00,
        "selling_price": 10000.00,
        "category": "pump",
        "brand": "Test Brand",
        "model": "TB-1HP"
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "customer_id": 1,
        "order_type": "sale",
        "items": [
            {
                "inventory_item_id": 1,
                "quantity": 2,
                "unit_price": 1500.00,
                "discount_percentage": 5.0
            }
        ],
        "gst_treatment": "taxable",
        "place_of_supply": "Maharashtra",
        "payment_terms": "net_30",
        "notes": "Test order"
    }


# Test markers for categorizing tests
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "contract: mark test as a contract test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )
