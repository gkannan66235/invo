"""Structured logging configuration (T031) without shadowing stdlib logging module."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict

try:
    import structlog  # type: ignore
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore

DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JsonFormatter:
    def format(self, record):  # noqa: D401
        base: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in ("request_id", "trace_id", "span_id"):
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        if record.exc_info:
            import traceback
            base["exc_info"] = "".join(
                traceback.format_exception(*record.exc_info))
        return json.dumps(base, ensure_ascii=False)


def configure_logging() -> None:
    if structlog:  # Configure structlog pipeline
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

    handler = logging.StreamHandler(sys.stdout)  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()  # type: ignore[attr-defined]
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(DEFAULT_LEVEL)


def bind_context(logger: logging.Logger, **kwargs: Any) -> logging.Logger:  # noqa: ARG001
    # Simplified (structlog would handle binding elsewhere). Placeholder for future expansion.
    return logger
