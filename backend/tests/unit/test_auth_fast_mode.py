import os
import pytest

pytestmark = pytest.mark.unit


def test_auth_client_fast_mode(auth_client):
    """Ensure FAST_TESTS shortcut issues a bearer token header without real login.

    If FAST_TESTS env not set, skip (environment-driven optimization not active).
    """
    if os.getenv("FAST_TESTS") != "1":
        pytest.skip(
            "FAST_TESTS not enabled; skipping fast-mode specific assertion")
    assert "Authorization" in auth_client.headers
    assert auth_client.headers["Authorization"].startswith("Bearer ")
