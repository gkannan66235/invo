#!/usr/bin/env python
"""Seed initial admin user if it does not exist.

This script is idempotent: it will only insert the admin user if missing.
Environment variables used (with defaults):
  SEED_ADMIN_USERNAME=admin
  SEED_ADMIN_EMAIL=admin@example.com
  SEED_ADMIN_PASSWORD=admin123

It uses the async session because auth endpoints rely on async access patterns.
"""
from __future__ import annotations
import os
import asyncio
import logging
from passlib.context import CryptContext
from sqlalchemy import select

try:
    from src.config.database import get_async_db  # type: ignore
    from src.models.database import User  # type: ignore
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.append(str(backend_dir))
    from src.config.database import get_async_db  # type: ignore
    from src.models.database import User  # type: ignore

logger = logging.getLogger("seed_users")
logging.basicConfig(level=logging.INFO, format="[seed_users] %(message)s")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123")
FULL_NAME = os.getenv("SEED_ADMIN_FULL_NAME", "System Administrator")


async def main():
    async with get_async_db() as session:
        result = await session.execute(select(User).where(User.username == USERNAME))
        user = result.scalar_one_or_none()
        if user:
            logger.info(
                "Admin user '%s' already exists; skipping seed.", USERNAME)
            return
        password_hash = pwd_context.hash(PASSWORD)
        user = User(
            username=USERNAME,
            email=EMAIL,
            password_hash=password_hash,
            full_name=FULL_NAME,
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        logger.info("Inserted admin user '%s' (%s)", USERNAME, EMAIL)


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except Exception as e:  # noqa: BLE001
        logger.error("Seeding failed: %s", e)
        raise
