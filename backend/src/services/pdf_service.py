"""PDF Service (Stub - Sprint 1)

Provides minimal on-demand PDF generation for invoices.
Sprint 1 scope: return a simple PDF (or PDF-like) byte stream ensuring endpoint + audit pipeline works.
Future (Sprint 2+): full HTML template rendering with Playwright print-to-pdf, caching layer.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime, UTC
import logging

LOGGER = logging.getLogger("pdf_service")

# Minimal single-page PDF template with dynamic fields.
_PDF_TEMPLATE = ("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
                 "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                 "2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
                 "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
                 "4 0 obj<</Length {length}>>stream\n{stream}\nendstream endobj\n"
                 "5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
                 "xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000055 00000 n \n0000000108 00000 n \n0000000279 00000 n \n0000000400 00000 n \n"
                 "trailer<</Size 6/Root 1 0 R>>\nstartxref\n{start}\n%%EOF")


def generate_invoice_pdf(invoice, customer: Optional[object] = None) -> bytes:  # type: ignore[no-untyped-def]
    """Return placeholder PDF bytes for an invoice.

    Args:
        invoice: ORM invoice instance with invoice_number, total_amount attributes
        customer: optional customer instance (unused in stub)
    """
    try:
        inv_num = getattr(invoice, "invoice_number", "UNKNOWN")
        total = getattr(invoice, "total_amount", None)
        ts = datetime.now(UTC).isoformat()
        text_lines = [
            f"Invoice {inv_num}",
            f"Generated: {ts}",
            f"Total: {total}" if total is not None else "Total: N/A",
            "-- Placeholder PDF --",
        ]
        # Build PDF text drawing commands (simple text lines separated vertically by 14pt)
        y = 170
        parts = ["BT /F1 12 Tf"]
        for line in text_lines:
            parts.append(f"72 {y} Td ({line}) Tj")
            y -= 14
            parts.append("T*")  # move to next line (simplistic)
        parts.append("ET")
        stream_content = " ".join(parts).encode("latin-1", "ignore")
        body = _PDF_TEMPLATE.format(length=len(stream_content), stream=stream_content.decode("latin-1"), start=500+len(stream_content))
        return body.encode("latin-1")
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Failed to generate stub PDF: %s", exc)
        raise RuntimeError("PDF generation failed") from exc

__all__ = ["generate_invoice_pdf"]
