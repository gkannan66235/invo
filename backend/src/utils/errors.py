"""Centralized error response helpers and exception utilities.

Aligns with FR-024 standardized error schema.
"""
from __future__ import annotations
from fastapi import HTTPException
from typing import Any, Dict
import time

ERROR_CODES = {
    "validation": "VALIDATION_ERROR",
    "not_found": "NOT_FOUND",
    # Domain specific specialisations (Phase 3 adoption)
    "invoice_not_found": "INVOICE_NOT_FOUND",
    "auth_invalid": "AUTH_INVALID_CREDENTIALS",
    "auth_expired": "AUTH_TOKEN_EXPIRED",
    "overpay": "OVERPAY_NOT_ALLOWED",
    "db": "DB_ERROR",
    "internal": "INTERNAL_SERVER_ERROR",
}


def error_payload(code: str, message: str, details: Any | None = None, path: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
        "timestamp": time.time(),
    }
    if details is not None:
        payload["error"]["details"] = details
    if path:
        payload["path"] = path
    return payload


def error_response(code: str, message: str, details: Any | None = None, path: str | None = None) -> Dict[str, Any]:
    """Alias for error_payload matching task naming (T002)."""
    return error_payload(code, message, details=details, path=path)


def raise_http_error(status_code: int, code: str, message: str, details: Any | None = None) -> None:
    """Raise an HTTPException using standardized schema (FastAPI global handlers will keep shape)."""
    raise HTTPException(status_code=status_code, detail={
        "code": code,
        "message": message,
        "details": details
    })


class DomainError(Exception):
    """Base domain error storing standardized fields."""

    def __init__(self, code: str, message: str, details: Any | None = None):  # noqa: D401
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class OverpayNotAllowed(DomainError):
    def __init__(self, paid_amount: float, total: float):
        super().__init__(
            ERROR_CODES["overpay"], f"Paid amount {paid_amount} exceeds total {total}")


__all__ = [
    "ERROR_CODES",
    "error_payload",
    "error_response",
    "raise_http_error",
    "DomainError",
    "OverpayNotAllowed",
]
