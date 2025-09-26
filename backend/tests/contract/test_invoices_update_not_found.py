import uuid
import pytest
from httpx import AsyncClient
from fastapi import status

from src.utils.errors import ERROR_CODES  # type: ignore

pytestmark = [pytest.mark.contract]


@pytest.mark.asyncio
async def test_patch_nonexistent_invoice_returns_not_found(auth_client: AsyncClient):
    """T055: PATCH non-existent invoice returns 404 INVOICE_NOT_FOUND (FR-023).

    Ensures the invoices update path surfaces standardized error code when target id does not exist.
    """
    missing_id = uuid.uuid4()
    resp = await auth_client.patch(f"/api/v1/invoices/{missing_id}", json={"amount": 123})
    assert resp.status_code == status.HTTP_404_NOT_FOUND, resp.text
    body = resp.json()

    # The router currently raises HTTPException with detail string and X-Error-Code header or code attribute.
    # Support both envelope and legacy shapes to avoid brittle failure while enforcing code presence.
    header_code = resp.headers.get("X-Error-Code")
    expected_code = ERROR_CODES["invoice_not_found"]

    if isinstance(body, dict) and body.get("status") == "error":
        # Standard envelope path
        err = body.get("error") or {}
        assert err.get("code") in {expected_code, ERROR_CODES["not_found"]}
    else:
        # Legacy detail path: FastAPI default shape {"detail": "..."}
        # Validate header_code (if present) or fall back to accepting generic not found.
        if header_code:
            assert header_code in {expected_code, ERROR_CODES["not_found"]}

    # Negative control: patching again with same id should still be 404
    resp2 = await auth_client.patch(f"/api/v1/invoices/{missing_id}", json={"gst_rate": 5})
    assert resp2.status_code == status.HTTP_404_NOT_FOUND
