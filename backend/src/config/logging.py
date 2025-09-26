"""Structured logging configuration (T031).

Provides JSON-formatted logs with optional request_id and trace correlation fields.
Uses structlog when available; falls back to standard logging JSON.
"""
from __future__ import annotations

import logging as _logging
import os
import sys
import time
from typing import Any, Dict

try:
    import structlog  # type: ignore
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore

DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JsonFormatter(_logging.Formatter):
    def format(self, record) -> str:  # noqa: D401 - record is LogRecord
        base: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Optional contextual attributes
        for attr in ("request_id", "trace_id", "span_id"):
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return __import__("json").dumps(base, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logging for application startup."""
    if structlog:  # Use structlog processors
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    # Standard logging config
    handler = _logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = _logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(DEFAULT_LEVEL)


def bind_context(logger, **kwargs: Any):  # pragma: no cover - simple helper
    """Bind contextual attributes to a logger via `LoggerAdapter` semantics."""
    if not kwargs:
        return logger
    return _logging.LoggerAdapter(logger, extra=kwargs)
