import pytest
import jwt
from datetime import datetime, UTC, timedelta
from httpx import AsyncClient
from fastapi import status
import os

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_expired_token_rejected(auth_client: AsyncClient):
    """T048: Expired JWT returns 401 AUTH_TOKEN_EXPIRED (FR/NFR-008).

    Steps:
      1. Perform normal login to get a valid token (to discover secret & alg via env/config consistency).
      2. Manually craft a token with exp in the past.
      3. Call a protected endpoint (/api/v1/invoices/) with expired token.
      4. Assert 401 and standardized code AUTH_TOKEN_EXPIRED if envelope present.
    """
    # 1. Login
    if os.getenv("FAST_TESTS") == "1":
        pytest.skip(
            "JWT expiry path bypassed in FAST_TESTS mode (synthetic user). Run without FAST_TESTS to exercise.")

    # 2. Craft expired token using same secret & algorithm env config.
    secret = os.getenv("JWT_SECRET", "dev-insecure-secret-change")
    alg = os.getenv("JWT_ALGORITHM", "HS256")
    past_exp = datetime.now(UTC) - timedelta(hours=1)
    expired_token = jwt.encode(
        {"sub": "admin", "exp": past_exp}, secret, algorithm=alg)

    # 3. Request protected resource
    headers = {"Authorization": f"Bearer {expired_token}"}
    protected_resp = await auth_client.get("/api/v1/invoices/", headers=headers)
    assert protected_resp.status_code == status.HTTP_401_UNAUTHORIZED, protected_resp.text
    body = protected_resp.json()
    # 4. Assert error code if standardized wrapper set by exception handling middleware
    if isinstance(body, dict) and body.get("status") == "error":
        assert body.get("error", {}).get("code") == "AUTH_TOKEN_EXPIRED"
    else:
        # Fallback: ensure some indicator of expiry
        text_repr = str(body).lower()
        assert "expired" in text_repr or "token" in text_repr
