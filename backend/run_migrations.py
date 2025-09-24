"""Utility script to run Alembic migrations programmatically before app start (optional).

Usage:
    python run_migrations.py

This can be invoked in container entrypoint before launching uvicorn.
"""
from alembic.config import Config
from alembic import command
import os

BASE_DIR = os.path.dirname(__file__)
ALEMBIC_INI = os.path.join(BASE_DIR, 'alembic.ini')


def run():
    cfg = Config(ALEMBIC_INI)
    # Environment variable DB_URL can override if needed
    if os.getenv('DATABASE_URL'):
        cfg.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL'))
    command.upgrade(cfg, 'head')


if __name__ == '__main__':
    run()
