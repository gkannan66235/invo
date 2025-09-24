"""Test configuration and fixtures.

Primary goals:
1. Prefer a Postgres test database managed by Alembic migrations when TEST_DB_URL is provided.
2. Fall back to legacy SQLite create_all() approach if Postgres not configured (developer convenience).
3. Provide per-test transactional isolation (rollback) for Postgres to avoid cross-test mutation leakage.

Environment Variables:
    TESTING=true      -> activates test-oriented code paths in application
    TEST_DB_URL=...   -> postgres:// or postgresql+asyncpg:// connection string for dedicated test DB

Behavior Matrix:
    If TEST_DB_URL set:
        - Run Alembic migrations (synchronous) to head once per session.
        - Use async engine derived from TEST_DB_URL (asyncpg driver conversion).
        - Wrap each test in a SAVEPOINT (nested transaction) for isolation.
    Else:
        - Use legacy SQLite metadata drop/create for fast local iteration.
        - No per-test rollback (state leakage possible across tests).
"""

import sys
from pathlib import Path
import os
import asyncio
import configparser
from typing import AsyncGenerator, Optional

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# Flag test mode early
os.environ.setdefault("TESTING", "true")

# --- Ensure backend root & src on sys.path BEFORE importing src.* ---
BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
for p in (BACKEND_DIR, SRC_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:  # noqa: SIM105
    from src.config.database import (  # type: ignore  # noqa: E402
        get_async_db_dependency,
        create_database_tables,
        SessionLocal,
    )
except Exception:  # noqa: BLE001
    # Static analysis / import-time failures (e.g., missing deps) are tolerated in lint context.
    get_async_db_dependency = None  # type: ignore
    create_database_tables = None  # type: ignore
    SessionLocal = None  # type: ignore


def _seed_test_users_sync(sync_session_factory: Optional[sessionmaker] = None):
    """Seed required users for contract tests (idempotent, sync)."""
    from src.models.database import User  # noqa: WPS433 (runtime import)
    pwd = pwd_ctx.hash("secure_password")
    admin_pwd = pwd_ctx.hash("admin123")
    SessionFac = sync_session_factory or SessionLocal
    with SessionFac() as session:
        if not session.query(User).filter_by(username="test_admin").first():
            session.add(User(
                username="test_admin",
                email="test_admin@example.com",
                password_hash=pwd,
                full_name="Test Admin",
                is_active=True,
                is_admin=True
            ))
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
def _bootstrap_db():  # noqa: D401
    """Bootstrap database for tests.

    Postgres path: migrations + seed handled in pytest_configure (early) for gevent safety.
    SQLite fallback: drop/create metadata here then seed.
    """
    if not os.getenv("TEST_DB_URL"):
        from src.config.database import drop_database_tables, create_database_tables  # noqa: WPS433
        drop_database_tables()
        create_database_tables()
        _seed_test_users_sync()
    yield


from src.main import app  # noqa: E402

# (path already added earlier)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:  # noqa: D401
    """Async HTTP client for tests (no auth)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

 # (Removed legacy auth_headers fixture; use auth_client fixture instead)


@pytest_asyncio.fixture
async def db_session():  # noqa: D401
    """Async DB session with per-test transactional isolation when Postgres used.

    If TEST_DB_URL defined: begin a transaction + SAVEPOINT; rollback after test.
    Else: fall back to simple dependency-provided session (SQLite legacy mode).
    """
    test_db_url = os.getenv("TEST_DB_URL")
    if not test_db_url:
        # Legacy path
        async for session in get_async_db_dependency():
            yield session
        return

    # Build async engine separate from global one to ensure proper lifecycle under tests
    async_url = test_db_url
    if async_url.startswith("postgresql+psycopg://"):
        async_url = async_url.replace(
            "postgresql+psycopg://", "postgresql+asyncpg://", 1)
    elif async_url.startswith("postgresql://"):
        async_url = async_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(async_url, echo=False, future=True)
    AsyncTestSession = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)

    async with engine.begin() as conn:
        # (Tables already migrated) Ensure search_path / pragmas if needed
        await conn.execute(text("SELECT 1"))

    async with engine.connect() as conn:
        trans = await conn.begin()
        nested = await conn.begin_nested()
        try:
            # type: ignore[arg-type]
            async with AsyncTestSession(bind=conn) as session:
                yield session
                await session.flush()
        finally:
            # Roll back nested and outer transaction to revert all changes
            if nested.is_active:
                await nested.rollback()
            if trans.is_active:
                await trans.rollback()
            await conn.close()
            await engine.dispose()


# ---------------------------------------------------------------------------
# Password hashing context (reduced rounds for faster tests)
# ---------------------------------------------------------------------------
TEST_BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "4"))
pwd_ctx = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=TEST_BCRYPT_ROUNDS)

# ---------------------------------------------------------------------------
# Early migration application to avoid gevent/locust monkeypatch side-effects
# ---------------------------------------------------------------------------
# Locust's import triggers gevent.monkey.patch_all(), which mutates the 'select'
# module and was breaking psycopg's use of selectors.KqueueSelector on macOS.
# We therefore run synchronous Alembic migrations (and seeding) in
# pytest_configure, which executes BEFORE test collection/import. This ensures
# psycopg connects before gevent monkeypatching occurs in performance tests.

_MIGRATIONS_APPLIED = False


def _apply_migrations_and_seed():
    """Run Alembic migrations & seed users for Postgres test DB (idempotent)."""
    global _MIGRATIONS_APPLIED  # noqa: PLW0603
    if _MIGRATIONS_APPLIED:
        return
    test_db_url = os.getenv("TEST_DB_URL")
    if not test_db_url:
        return
    # Derive sync URL
    sync_url = test_db_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace(
            "postgresql+asyncpg://", "postgresql+pg8000://", 1)
    elif sync_url.startswith("postgresql+psycopg://"):
        sync_url = sync_url.replace(
            "postgresql+psycopg://", "postgresql+pg8000://", 1)
    elif sync_url.startswith("postgresql://") and "+pg8000" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+pg8000://", 1)

    # Run migrations programmatically
    from alembic.config import Config  # inline import to avoid global dependency
    from alembic import command
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")

    # Seed users via sync session
    engine = create_engine(sync_url)
    SyncSession = sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)
    try:
        _seed_test_users_sync(SyncSession)
    finally:
        engine.dispose()
    _MIGRATIONS_APPLIED = True


def pytest_configure(config):  # noqa: D401
    """Pytest hook: apply migrations then register custom markers (single hook)."""
    _apply_migrations_and_seed()
    _register_markers(config)


async def _ensure_admin(session: AsyncSession):
    from src.models.database import User  # noqa: WPS433
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
async def auth_client(db_session) -> AsyncGenerator[AsyncClient, None]:  # noqa: PT019 F811
    """Async client with valid JWT auth header for admin user."""
    await _ensure_admin(db_session)
    # context manager for test client
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


@pytest_asyncio.fixture
async def auth_headers(db_session):  # noqa: D401
    """Provide just the Authorization headers for admin user (for contract tests).

    Separate from auth_client so tests that only need raw headers can still
    use their own AsyncClient fixture if desired.
    """
    await _ensure_admin(db_session)
    from httpx import AsyncClient as _AsyncClient  # local import to avoid confusion
    async with _AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if "data" in body and isinstance(body.get("data"), dict):
            token = body["data"].get("access_token")
        else:
            token = body.get("access_token")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def sample_customer_data():  # noqa: D401
    """Return representative customer payload used across tests."""
    return {
        "name": "Acme Corp",
        "customer_type": "business",
        "contact_name": "Jane Doe",
        "email": "acme@example.com",
        "phone": "+1-555-0100",
        "gst_number": "27ABCDE1234F1Z5",
        "billing_address": "123 Industrial Park",
        "shipping_address": "123 Industrial Park",
        "city": "Pune",
        "state": "Maharashtra",
        "country": "India",
        "postal_code": "411001"
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


# Test markers for categorizing tests (pytest_plugins removed to avoid non-top-level declaration)

def _register_markers(config):  # noqa: D401
    """Internal helper to register custom markers (invoked from hook)."""
    markers = [
        ("contract", "mark test as a contract test"),
        ("integration", "mark test as an integration test"),
        ("unit", "mark test as a unit test"),
        ("slow", "mark test as slow running"),
        ("auth", "mark test as requiring authentication"),
        ("performance", "mark test as a performance benchmark"),
    ]
    for name, desc in markers:
        config.addinivalue_line("markers", f"{name}: {desc}")


# (Removed duplicate pytest_configure; marker registration handled in unified hook above)


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


# ---------------------------------------------------------------------------
# Optimized DB session fixture (engine reuse) - inserted above progress section
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def _test_engine():  # noqa: D401
    """Session-scoped async engine for Postgres tests (reused across tests)."""
    test_db_url = os.getenv("TEST_DB_URL")
    if not test_db_url:
        yield None
        return
    async_url = test_db_url
    if async_url.startswith("postgresql+psycopg://"):
        async_url = async_url.replace(
            "postgresql+psycopg://", "postgresql+asyncpg://", 1)
    elif async_url.startswith("postgresql://"):
        async_url = async_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url, echo=False, future=True)
    # Warm connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_test_engine):  # type: ignore[override]  # noqa: D401
    """Provide per-test transactional isolation using a shared engine.

    Falls back to legacy dependency path when TEST_DB_URL not set (SQLite).
    """
    test_db_url = os.getenv("TEST_DB_URL")
    if not test_db_url:
        # type: ignore[func-returns-value]
        async for session in get_async_db_dependency():
            yield session
        return
    engine = _test_engine
    AsyncTestSession = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)
    async with engine.connect() as conn:  # type: ignore[union-attr]
        outer = await conn.begin()
        nested = await conn.begin_nested()
        try:
            # type: ignore[arg-type]
            async with AsyncTestSession(bind=conn) as session:
                yield session
                await session.flush()
        finally:
            if nested.is_active:
                await nested.rollback()
            if outer.is_active:
                await outer.rollback()
            await conn.close()

# ---------------------------------------------------------------------------
# Progress Percentage Output (with optional disable + per-test duration)
# ---------------------------------------------------------------------------

PROGRESS_CONFIG = None  # Global reference to pytest Config (set after collection)
PROGRESS_START_TIMES = {}  # nodeid -> float start time


def pytest_addoption(parser):  # noqa: D401
    """Add --no-progress flag to disable progress output."""
    parser.addoption(
        "--no-progress",
        action="store_true",
        default=False,
        help="Disable per-test progress percentage output (enabled by default).",
    )


def pytest_collection_finish(session):  # noqa: D401
    """Initialize counters and store config reference for progress reporting."""
    global PROGRESS_CONFIG  # noqa: PLW0603
    cfg = session.config
    cfg._invo_total_tests = len(session.items)  # type: ignore[attr-defined]
    cfg._invo_completed_tests = 0  # type: ignore[attr-defined]
    cfg._invo_last_reported_pct = -1  # type: ignore[attr-defined]
    cfg._invo_progress_enabled = not cfg.getoption("--no-progress")  # type: ignore[attr-defined]
    PROGRESS_CONFIG = cfg


def pytest_runtest_setup(item):  # noqa: D401
    """Record per-test start time for duration reporting."""
    import time as _time
    PROGRESS_START_TIMES[item.nodeid] = _time.time()


def pytest_runtest_logreport(report):  # noqa: D401
    """Emit incremental progress lines with percentage + duration.

    Only processes the call phase for completed tests.
    """
    if report.when != "call":
        return
    config = PROGRESS_CONFIG
    if config is None:
        return
    if not getattr(config, "_invo_progress_enabled", True):  # type: ignore[attr-defined]
        return
    total = getattr(config, "_invo_total_tests", 0)
    if not total:
        return
    completed = getattr(config, "_invo_completed_tests", 0) + 1
    setattr(config, "_invo_completed_tests", completed)
    pct = int(completed / total * 100)
    last_pct = getattr(config, "_invo_last_reported_pct", -1)
    if pct != last_pct or report.failed:
        setattr(config, "_invo_last_reported_pct", pct)
        import sys as _sys, time as _time
        start = PROGRESS_START_TIMES.pop(report.nodeid, None)
        dur = f"{(_time.time() - start):.3f}s" if start else "-"
        print(
            f"[progress] {completed}/{total} ({pct}%) {dur} - {report.nodeid} - {report.outcome}",
            file=_sys.stderr,
            flush=True,
        )
        config._invo_last_progress_time = _time.time()  # type: ignore[attr-defined]


def pytest_report_teststatus(report, config):  # noqa: D401
    """Emit heartbeat if no test finished for >30s (helps perceived 'hang')."""
    if not getattr(config, "_invo_progress_enabled", True):  # type: ignore[attr-defined]
        return
    import time as _time, sys as _sys
    total = getattr(config, "_invo_total_tests", 0)
    if not total:
        return
    last = getattr(config, "_invo_last_progress_time", None)
    now = _time.time()
    if last is None:
        config._invo_last_progress_time = now  # type: ignore[attr-defined]
        return
    if now - last > 30:
        completed = getattr(config, "_invo_completed_tests", 0)
        pct = int(completed / total * 100)
        print(
            f"[progress-heartbeat] still running... {completed}/{total} ({pct}%)",
            file=_sys.stderr,
            flush=True,
        )
        config._invo_last_progress_time = now  # type: ignore[attr-defined]
