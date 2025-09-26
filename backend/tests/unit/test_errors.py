import pytest  # noqa: F401
from src.utils.errors import error_payload, ERROR_CODES, OverpayNotAllowed


def test_error_payload_basic():
    p = error_payload(ERROR_CODES["validation"], "Invalid data", details={
                      "field": "x"}, path="/api/v1/invoices")
    assert p["status"] == "error"
    assert p["error"]["code"] == ERROR_CODES["validation"]
    assert p["error"]["details"] == {"field": "x"}
    assert p["path"] == "/api/v1/invoices"


def test_overpay_not_allowed_message():
    exc = OverpayNotAllowed(150, 100)
    assert ERROR_CODES["overpay"] == exc.code
    assert "exceeds total" in exc.message
