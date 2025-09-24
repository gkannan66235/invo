"""Utility helpers for managing Postgres test databases.

This module can be imported by tests or invoked as a script.

Usage examples:
    python -m tests._tools.manage_test_db create invo_test
    python -m tests._tools.manage_test_db drop invo_test

Environment variables:
    TEST_DB_SUPER_URL - superuser connection string to the postgres maintenance DB
                        (defaults to postgresql://postgres:postgres@localhost:5432/postgres)
"""
from __future__ import annotations

import os
import sys
import argparse
from typing import Optional
from contextlib import contextmanager

import psycopg

DEFAULT_SUPER_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


def _super_url() -> str:
    return os.getenv("TEST_DB_SUPER_URL", DEFAULT_SUPER_URL)


@contextmanager
def _admin_conn():
    conn = psycopg.connect(_super_url(), autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def create_db(name: str) -> None:
    with _admin_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
            )
            if cur.fetchone():
                print(f"[test-db] Database '{name}' already exists")
                return
            cur.execute(f"CREATE DATABASE {name}")
            print(f"[test-db] Created database '{name}'")


def drop_db(name: str) -> None:
    with _admin_conn() as conn:
        with conn.cursor() as cur:
            # Terminate existing connections
            cur.execute(
                "SELECT pid FROM pg_stat_activity WHERE datname=%s", (name,)
            )
            pids = [row[0] for row in cur.fetchall()]
            for pid in pids:
                cur.execute(f"SELECT pg_terminate_backend({pid})")
            cur.execute("DROP DATABASE IF EXISTS " + name)
            print(f"[test-db] Dropped database '{name}' (if it existed)")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage Postgres test databases")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create", help="Create test database")
    c.add_argument("name")

    d = sub.add_parser("drop", help="Drop test database")
    d.add_argument("name")

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    if ns.command == "create":
        create_db(ns.name)
    elif ns.command == "drop":
        drop_db(ns.name)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
