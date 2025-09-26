"""Models package marker.

Allows relative imports from sibling packages (e.g. services -> models).
Exposes Base and key model classes for simplified imports if desired.
"""
from .database import Base  # noqa: F401
