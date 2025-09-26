from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..config.database import get_async_db
from ..config.settings import get_settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_app_settings(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:  # noqa: ARG001
    """Return application settings relevant to invoices.

    Currently only exposes gst_default_rate (float). Future fields can be added while
    preserving this contract. DB injected for future persistence requirements.
    """
    s = get_settings()
    return {
        "gst_default_rate": s.DEFAULT_GST_RATE,
    }


@router.patch("", status_code=status.HTTP_200_OK)
async def patch_app_settings(payload: Dict[str, Any], db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:  # noqa: ARG001
    """Update mutable settings fields.

    For now only gst_default_rate is accepted (in-memory live reload). A production
    implementation would persist this into a settings table. Keeping it simple for tests.
    """
    rate = payload.get("gst_default_rate")
    if rate is not None:
        try:
            rate_f = float(rate)
        except (TypeError, ValueError):  # noqa: PERF203
            rate_f = None
        if rate_f is not None and rate_f > 0:
            # Monkey patch cached settings object (lru_cache instance)
            s = get_settings()
            s.DEFAULT_GST_RATE = rate_f  # type: ignore[attr-defined]
    # Return current view
    return await get_app_settings(db)  # reuse logic

__all__ = ["router"]
