"""Test configuration and fixtures for contract tests.

Path manipulation must run before importing application modules so that
`from src...` imports resolve when running `pytest` from the backend folder.
"""

import sys
from pathlib import Path
import os
import asyncio
import configparser
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure tests use lightweight SQLite database
os.environ.setdefault("TESTING", "true")

# --- Ensure backend root & src on sys.path BEFORE importing src.* ---
BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
for p in (BACKEND_DIR, SRC_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from src.config.database import (
    get_async_db_dependency,  # noqa: E402
    create_database_tables,  # noqa: E402
    SessionLocal  # noqa: E402
)


def _seed_test_users():
    """Seed required users for contract tests (idempotent)."""
    from src.models.database import User  # local import after path setup
    pwd = pwd_ctx.hash("secure_password")
    admin_pwd = pwd_ctx.hash("admin123")
    with SessionLocal() as session:
        # test_admin user
        if not session.query(User).filter_by(username="test_admin").first():
            session.add(User(
                username="test_admin",
                email="test_admin@example.com",
                password_hash=pwd,
                full_name="Test Admin",
                is_active=True,
                is_admin=True
            ))
        # legacy admin user for other fixtures
        if not session.query(User).filter_by(email="admin@example.com").first():
            session.add(User(
                username="admin",
                email="admin@example.com",
                password_hash=admin_pwd,
                full_name="Administrator",
                is_active=True,
                is_admin=True
            ))
        session.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    """Create tables and seed users once per test session."""
    # For evolving schema in early phase, ensure tables reflect latest model definitions.
    # Simple approach: drop then recreate (SQLite in-memory / file is lightweight) to pick up new columns like is_deleted (T026).
    from src.config.database import drop_database_tables  # local import to avoid circular
    drop_database_tables()
    create_database_tables()
    _seed_test_users()
    yield


from src.main import app  # noqa: E402
from src.models.database import User  # noqa: E402

# Ensure application root (backend/src) is importable when running tests directly
BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
for p in [BACKEND_DIR, SRC_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def db_session():
    """Provide an async DB session (shared DB, not isolated transaction).

    NOTE: For true isolation, wrap each test in a SAVEPOINT / ROLLBACK strategy.
    This simplified version is acceptable for early smoke tests but may allow
    cross-test state leakage.
    """
    async for session in get_async_db_dependency():
        yield session


pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _ensure_admin(session: AsyncSession):
    result = await session.execute(select(User).where(User.email == "admin@example.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash=pwd_ctx.hash("admin123"),
            full_name="Administrator",
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        await session.commit()


@pytest_asyncio.fixture
async def auth_client(db_session) -> AsyncGenerator[AsyncClient, None]:  # noqa: PT019
    """Async client with valid JWT auth header for admin user."""
    await _ensure_admin(db_session)
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Support both legacy flat response and new envelope during transition
        if "data" in body and isinstance(body.get("data"), dict):
            token = body["data"].get("access_token")
        else:
            token = body.get("access_token")
        client.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        yield client


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


def pytest_sessionfinish(session, exitstatus):  # noqa: D401, ARG001
    """Enforce invoice router specific coverage threshold (>=90%).

    Implements T004 supplemental domain coverage gate.
    Reads path & threshold from pytest.ini [invoice_coverage] section.
    If coverage data absent (e.g., -k single test without coverage), silently skip.
    """
    try:
        from coverage import Coverage
    except ImportError:  # coverage plugin not installed
        return

    ini_path = Path(__file__).resolve().parents[1] / "pytest.ini"
    if not ini_path.exists():  # Should not happen
        return

    parser = configparser.ConfigParser()
    parser.read(ini_path)
    if "invoice_coverage" not in parser:
        return
    path = parser["invoice_coverage"].get("path", "src/routers/invoices.py")
    try:
        threshold = float(parser["invoice_coverage"].get("fail_under", "90"))
    except ValueError:
        threshold = 90.0

    data_file = os.getenv("COVERAGE_FILE", ".coverage")
    if not Path(data_file).exists():  # No coverage data generated
        return

    cov = Coverage(data_file=data_file)
    try:
        cov.load()
    except Exception:  # noqa: BLE001  # Safe fallback: coverage import optional
        return

    try:
        filename = Path(path)
        if not filename.exists():
            # Support running from backend dir where relative path valid
            filename = Path(".") / path
        if not filename.exists():
            return
        analysis = cov.analysis2(str(filename))
    except Exception:  # noqa: BLE001  # Coverage analysis may fail for partial runs
        return

    # analysis2 returns (filename, statements, excluded, missing, missing_formatted)
    statements = analysis[1]
    missing = analysis[3]
    total = len(statements)
    missed = len(missing)
    if total == 0:
        return
    covered = total - missed
    pct = covered / total * 100.0
    if pct + 1e-9 < threshold:  # small epsilon
        session.exitstatus = 1
        session.config.warn(
            code="INVOICE_COV",
            message=f"Invoice router coverage {pct:.2f}% below required {threshold:.2f}% (statements={total}, missed={missed})"
        )
