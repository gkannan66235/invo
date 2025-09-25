# Research: Customer & Invoice Localisation + Printable Invoices

**Feature Branch**: 003-customer-nsupport-only  
**Date**: 2025-09-25  
**Scope**: Phase 0 research decisions resolving technology and approach selections.

## Decisions

### 1. PDF Generation Strategy

- **Decision**: Use Playwright headless Chromium `page.pdf()` for invoice PDF generation.
- **Rationale**: Reuses existing HTML invoice view → single source of truth for layout & CSS. High fidelity fonts and print CSS support. Avoids wkhtmltopdf dependency complexity.
- **Alternatives Considered**:
  - WeasyPrint: Pure Python but partial CSS support → risk for complex layout.
  - wkhtmltopdf: Mature but requires system package; adds ops burden.
  - ReportLab: Low-level; higher dev effort to match design.

### 2. INR Number Formatting

- **Decision**: Implement server-side utility for Indian digit grouping (e.g., 1,23,456.78) for PDF; frontend continues client formatting using same algorithm for consistency.
- **Rationale**: Ensures consistent invoice representation independent of client locale settings.
- **Alternatives**: Rely solely on client – risks mismatch if future server emails PDF.

### 3. Duplicate Customer Mobile Detection

- **Decision**: Exact normalized 10-digit string equality search with B-Tree index; warning only.
- **Rationale**: Meets p95 <50ms easily; avoids false positives.
- **Alternatives**: Fuzzy match (edit distance) unnecessary complexity; performance overhead.

### 4. Address Model Simplicity

- **Decision**: Single line + city field only (no pin code/state) this phase.
- **Rationale**: Reduces validation/error complexity; matches minimal user request.
- **Alternatives**: Full address schema (line2, state, pincode) deferred to later feature.

### 5. Audit Logging Implementation

- **Decision**: New table `invoice_download_audit` with async insertion (background task) to keep request latency under 50ms overhead.
- **Schema Draft**: id (UUID PK), invoice_id (FK), user_id (FK), action (enum: print|pdf), created_at (UTC timestamp).
- **Rationale**: Structured querying for compliance & analytics.
- **Alternatives**: Flat file logs – harder aggregation; existing generic audit not present.

### 6. PDF Caching

- **Decision**: Optional in-memory LRU cache (max 100 entries or 5m TTL). Disabled by default; enable if sustained repeated downloads observed.
- **Rationale**: Avoid premature optimization; provides escape hatch under print-heavy sessions.
- **Alternatives**: Redis cache introduces external dependency out-of-scope.

### 7. Invoice Immutability Snapshot

- **Decision**: Snapshot branding & seller settings (name, address, GST rate used) at invoice issue time into invoice record JSON fields.
- **Rationale**: Guarantees reproducible historical documents after settings changes.
- **Alternatives**: Recompute dynamically – risk of historical drift.

### 8. PDF Styling

- **Decision**: Dedicated print CSS with minimal color usage, A4 portrait, avoid pagination widows/orphans via CSS page-break rules.
- **Rationale**: Professional output & predictable pagination.

### 9. Performance Instrumentation

- **Decision**: Add metrics: `pdf_generate_duration_seconds` (histogram), `invoice_download_total`, `customer_duplicate_warning_total`.
- **Rationale**: Observability NFR coverage.

## Open (Deferred) Items

- Customer merge/dedupe workflow (future feature).
- Extended address fields & postal code validation.
- Email delivery of PDF invoices.
- Multi-currency support.

## Summary

All critical unknowns resolved; no remaining blockers for Phase 1 design.
