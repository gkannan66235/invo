"""Shared API shape helpers for transitional dual response modes.

This module centralizes:
  - success(): standard success envelope
  - error_envelope(): standard error envelope structure (not raised)
  - is_raw_mode(): detection of transitional raw mode (X-Raw-Mode header)

Raw Mode (transitional):
  Used only by early *new_feature* skeleton tests. Activated exclusively via
  the header:    X-Raw-Mode: 1
  Returns the underlying object/list directly (no envelope; some numeric fields
  string-formatted elsewhere). To be deprecated once tests & clients are migrated.
"""
from __future__ import annotations
from typing import Any
from fastapi import Request


def success(data: Any, **meta) -> dict:
    import time as _t
    return {"status": "success", "data": data, "meta": meta or None, "timestamp": _t.time()}


def error_envelope(code: str, message: str) -> dict:
    return {"status": "error", "error": {"code": code, "message": message}}


RAW_HEADER_VALUES = {"1", "true", "raw"}
RAW_HEADER_NAME = "X-Raw-Mode"


def is_raw_mode(request: Request) -> bool:
    """Return True if explicit raw mode header present.

    We have intentionally removed the implicit Authorization token heuristic to
    avoid accidental activation. This keeps raw mode opt-in & easily removable.
    """
    hv = request.headers.get(RAW_HEADER_NAME)
    return hv is not None and hv.lower() in RAW_HEADER_VALUES
