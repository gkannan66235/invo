"""Service layer package.

Ensures Python treats this directory as a package so relative imports like
`from ..models.database import InventoryItem` resolve correctly when tests add
`backend/src` to sys.path.
"""

__all__ = [
    "customer_service",
    "invoice_service",
    "inventory_service",
    "pdf_service",
]
