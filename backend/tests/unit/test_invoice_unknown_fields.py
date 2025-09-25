import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_invoice_unknown_fields_dropped(auth_client: AsyncClient):
    """T056: Unknown extra fields in create payload are ignored and absent from response."""
    payload = {
        "customerName": "Unknown Field Customer",
        "customerPhone": "8888800001",
        "amount": 120,
        "gstRate": 18,
        # Unknown / extraneous fields (frontend experiments or legacy)
        "legacyId": "ABC123",
        "randomFlag": True,
        "internalNotes": "Should not persist",
        "__proto__": {},  # attempt at prototype pollution style key
        "dropMe": 42,
    }
    r = await auth_client.post("/api/v1/invoices/", json=payload)
    assert r.status_code == 201, r.text
    data = r.json().get("data", r.json())

    # Core assertions (basic correctness)
    assert data["invoice_number"].startswith("INV")
    assert data["gst_amount"] == 21.6  # 18% of 120
    assert data["total_amount"] == 141.6

    # Unknown keys must not appear (snake_case normalized list)
    forbidden_keys = {"legacyId", "randomFlag", "internalNotes", "__proto__", "dropMe",
                      # Also ensure they didn't become snake_case variants
                      "legacy_id", "random_flag", "internal_notes", "drop_me"}
    present_keys = set(data.keys())
    assert forbidden_keys.isdisjoint(present_keys), f"Unexpected extra keys leaked: {forbidden_keys & present_keys}"
