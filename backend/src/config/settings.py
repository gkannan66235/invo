"""Application settings module (T022).

Provides centralized configuration using environment variables with sane defaults.
Default GST rate requirement: If `DEFAULT_GST_RATE` env is not set, fallback to 18.0 (Assumption A3).
T023 will enforce usage in invoice creation/update when gst_rate is omitted.
"""
from __future__ import annotations

from functools import lru_cache
import os
from typing import Any

try:
    from pydantic import BaseModel
except ImportError:  # Minimal fallback if pydantic not available (should be installed)
    class BaseModel:  # type: ignore
        def __init__(self, **data: Any):  # noqa: D401
            for k, v in data.items():
                setattr(self, k, v)


class Settings(BaseModel):
    # Core invoice domain defaults
    DEFAULT_GST_RATE: float = 18.0

    # Auth / security (future consolidation)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Observability toggles (future use)
    ENABLE_TRACING: bool = False

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment with type coercion and defaults.

        For now we keep it simple; if pydantic BaseSettings desired, migrate later.
        """
        def _get_float(name: str, default: float) -> float:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        def _get_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.lower() in {"1", "true", "yes", "on"}

        return cls(
            DEFAULT_GST_RATE=_get_float("DEFAULT_GST_RATE", 18.0),
            ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            ENABLE_TRACING=_get_bool("ENABLE_TRACING", False),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance (singleton pattern)."""
    return Settings.load()


def get_default_gst_rate() -> float:
    """Helper accessor for default GST rate used in T023 enforcement."""
    return get_settings().DEFAULT_GST_RATE


__all__ = ["Settings", "get_settings", "get_default_gst_rate"]
