"""
Database configuration and connection management.
"""

import logging
import os
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from ..models.database import Base


logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration management."""

    def __init__(self):
        self.database_url = self._get_database_url()
        self.async_database_url = self._get_async_database_url()
        self.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))

    def _get_database_url(self) -> str:
        """Get synchronous database URL from environment."""
        if os.getenv("TESTING", "false").lower() == "true":
            # Use file-based SQLite for persistence across connections in tests
            return "sqlite:///./test.db"
        url = os.getenv("DATABASE_URL")
        if not url:
            # Default local PostgreSQL configuration
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            database = os.getenv("DB_NAME", "invoice_system")
            username = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "postgres")
            # Explicit psycopg v3 driver URL (was postgresql:// which triggered psycopg2)
            url = f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"
        return url

    def _get_async_database_url(self) -> str:
        """Get asynchronous database URL from environment."""
        if os.getenv("TESTING", "false").lower() == "true":
            return "sqlite+aiosqlite:///./test.db"
        url = os.getenv("ASYNC_DATABASE_URL")
        if not url:
            # Convert sync URL to async URL
            sync_url = self._get_database_url()
            if sync_url.startswith("postgresql+psycopg://"):
                # Replace psycopg driver with asyncpg driver
                url = sync_url.replace(
                    "postgresql+psycopg://", "postgresql+asyncpg://")
            elif sync_url.startswith("postgresql://"):
                url = sync_url.replace(
                    "postgresql://", "postgresql+asyncpg://")
            else:
                # Fallback: if already async or different db, reuse
                url = sync_url
        return url


# Global database configuration
db_config = DatabaseConfig()

# Create engines with driver-specific connection arguments
if db_config.database_url.startswith("sqlite"):
    # SQLite doesn't support the PostgreSQL specific connect args
    engine = create_engine(
        db_config.database_url,
        echo=db_config.echo,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        db_config.database_url,
        echo=db_config.echo,
        poolclass=QueuePool,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_timeout=db_config.pool_timeout,
        pool_recycle=db_config.pool_recycle,
        connect_args={
            "application_name": "invoice_system",
            "options": "-c timezone=UTC"
        }
    )

if db_config.async_database_url.startswith("sqlite+aiosqlite"):
    async_engine = create_async_engine(
        db_config.async_database_url,
        echo=db_config.echo,
        connect_args={"check_same_thread": False}
    )
else:
    async_engine = create_async_engine(
        db_config.async_database_url,
        echo=db_config.echo,
    )

# Create session factories
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations on connect."""
    # This is for PostgreSQL, so we don't need SQLite pragmas
    # But we can set PostgreSQL-specific settings here if needed
    pass


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for performance monitoring."""
    import time
    context._query_start_time = time.time()


@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for performance monitoring."""
    import time
    total = time.time() - context._query_start_time

    # Log queries that take longer than 100ms (constitutional requirement is 200ms total)
    if total > 0.1:
        logger.warning(
            f"Slow query detected: {total:.3f}s - {statement[:100]}..."
        )


def create_database_tables():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def create_database_tables_async():
    """Create all database tables asynchronously."""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully (async)")
    except Exception as e:
        logger.error(f"Failed to create database tables (async): {e}")
        raise


def drop_database_tables():
    """Drop all database tables."""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get database session context manager.

    Usage:
        with get_db() as db:
            # Use db session
            pass
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session context manager.

    Usage:
        async with get_async_db() as db:
            # Use async db session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_db_dependency():
    """
    FastAPI dependency for database session.

    Usage in FastAPI endpoints:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_dependency)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db_dependency():
    """
    FastAPI dependency for async database session.

    Usage in FastAPI endpoints:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_async_db_dependency)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def check_async_database_connection() -> bool:
    """Check if async database connection is working."""
    try:
        async with get_async_db() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Async database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """Get database connection information for monitoring."""
    return {
        # Hide credentials
        "database_url": db_config.database_url.split("@")[-1],
        "pool_size": db_config.pool_size,
        "max_overflow": db_config.max_overflow,
        "pool_timeout": db_config.pool_timeout,
        "pool_recycle": db_config.pool_recycle,
        "echo": db_config.echo,
        "engine_info": {
            "pool_size": engine.pool.size(),
            "pool_checked_in": engine.pool.checkedin(),
            "pool_checked_out": engine.pool.checkedout(),
        }
    }


# Health check functions for monitoring
def database_health_check() -> dict:
    """Comprehensive database health check."""
    try:
        # Check connection
        connection_ok = check_database_connection()

        # Get pool statistics
        pool_stats = {
            "size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
        }

        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "connection": connection_ok,
            "pool_stats": pool_stats,
            "database_info": get_database_info()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": False,
            "error": str(e)
        }


async def async_database_health_check() -> dict:
    """Comprehensive async database health check."""
    try:
        # Check connection
        connection_ok = await check_async_database_connection()

        # Get pool statistics
        pool_stats = {
            "size": async_engine.pool.size(),
            "checked_in": async_engine.pool.checkedin(),
            "checked_out": async_engine.pool.checkedout(),
            "overflow": async_engine.pool.overflow(),
        }

        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "connection": connection_ok,
            "pool_stats": pool_stats,
            "database_info": get_database_info()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": False,
            "error": str(e)
        }
