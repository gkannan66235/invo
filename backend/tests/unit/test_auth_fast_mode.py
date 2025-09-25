import os
import pytest

pytestmark = pytest.mark.unit


def test_auth_client_fast_mode(auth_client):
    """Ensure FAST_TESTS shortcut issues a bearer token header without real login."""
    # FAST_TESTS should be set by Makefile in standard runs; assert header format
    assert os.getenv("FAST_TESTS") == "1"
    assert "Authorization" in auth_client.headers
    assert auth_client.headers["Authorization"].startswith("Bearer ")
