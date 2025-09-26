"""System router providing health and readiness endpoints (T033)."""
from fastapi import APIRouter
import time

try:
    from src.config.database import async_database_health_check  # type: ignore
except ImportError:  # pragma: no cover
    from ..config.database import async_database_health_check  # type: ignore

router = APIRouter()

_start_time = time.time()


def _success(data, **meta):
    from time import time as _now
    return {"status": "success", "data": data, "meta": meta or None, "timestamp": _now()}


@router.get("/health", tags=["System"])  # liveness
async def health():
    return _success({"ok": True})


@router.get("/readiness", tags=["System"])  # readiness: db connectivity
async def readiness():
    db_health = await async_database_health_check()
    return _success({"database": db_health, "uptime_s": int(time.time() - _start_time)})
