"""PDF Service (Stub - Sprint 1)

Provides minimal on-demand PDF generation for invoices.
Sprint 1 scope: return a simple PDF (or PDF-like) byte stream ensuring endpoint + audit pipeline works.
Future (Sprint 2+): full HTML template rendering with Playwright print-to-pdf, caching layer.
"""
from __future__ import annotations
from typing import Optional

# For Sprint 1 we avoid heavy dependencies; later we'll integrate Playwright.
# A tiny fallback: generate a very simple PDF header manually (not standards-complete but acceptable for placeholder)

_PDF_PREAMBLE = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
_PDF_BODY_TEMPLATE = "1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources <<>> >>endobj\n4 0 obj<< /Length {length} >>stream\n{stream}\nendstream endobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000234 00000 n \ntrailer<< /Size 5 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF"


def generate_invoice_pdf(invoice_id: str, total: Optional[str] = None) -> bytes:
    """Return placeholder PDF bytes for an invoice.

    Args:
        invoice_id: Identifier of the invoice
        total: Optional total amount string to embed
    """
    text = f"Invoice {invoice_id} Generated (placeholder) Total: {total or 'N/A'}"
    # Minimal PDF text object (not production grade)
    stream_content = f"BT /F1 12 Tf 12 100 Td ({text}) Tj ET".encode("latin-1", "ignore")
    body = _PDF_BODY_TEMPLATE.format(length=len(stream_content), stream=stream_content.decode("latin-1"), start=300+len(stream_content))
    return _PDF_PREAMBLE + body.encode("latin-1")

__all__ = ["generate_invoice_pdf"]
