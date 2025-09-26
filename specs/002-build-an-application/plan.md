# Implementation Plan: BillingBee Core Invoicing & Service Center Foundation

Feature Branch: `002-build-an-application`
Spec Reference: `specs/002-build-an-application/spec.md`
Status: Initial Version (2025-09-24)

## 1. Purpose & Scope

Deliver a production‑ready backend slice for BillingBee enabling secure authentication and GST-compliant invoice lifecycle (create, view, update, payment tracking, soft delete). Frontend exists (Next.js) and will integrate via REST JSON. This plan constrains scope to single-tenant, single-currency, no roles, and no refresh tokens.

## 2. Architectural Overview

Layering (progressive refinement):

- API Layer (`routers/`): FastAPI routers expose HTTP endpoints, perform request validation.
- Service Layer (`services/` – to be introduced): Encapsulates business logic (invoice create/update/payment transitions, soft delete), enabling testability and reuse.
- Persistence Layer (`models/`, `config/database.py`): SQLAlchemy async ORM models + session acquisition.
- Utilities (`utils/`): Error schema helpers, normalization utilities if factored out.
- Cross-Cutting (`config/observability.py`, future `logging.py`): Metrics, logging, performance middleware.

Request Flow: Client → FastAPI Router (validation/normalization) → Service (domain rules) → Repository/ORM → DB → Response mapping (service → DTO) → Standard error schema.

## 3. Data Model (Current + Planned Deltas)

Existing Tables: `users`, `customers`, `invoices`.
Planned Modifications:

- Add `is_deleted BOOLEAN NOT NULL DEFAULT FALSE` to `invoices` (soft delete).
- Add `lifecycle_status` enum (`active`, `cancelled`) aligning with clarified spec FR-012 (replaces earlier `is_cancelled` flag concept). Payment status remains derived independently.
  Indexes (Phase 5):
- Composite index `(invoice_date DESC)` already implicit; add index on `(payment_status)` and `(customer_id)` if performance profiling (T041) indicates.

## 4. Invoice Domain Logic Summary

Computed Fields (Monetary Rounding):

All monetary values use `Decimal` with quantization `Decimal('0.01')` and HALF_UP rounding (NFR-011) to avoid binary float drift and ensure .005 rounds upward.

```
from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal('0.01')

def quantize(v: Decimal) -> Decimal:
  return v.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

subtotal_d = Decimal(str(subtotal))
gst_rate_d = Decimal(str(gst_rate))
gst_amount = quantize(subtotal_d * gst_rate_d / Decimal('100'))
total_amount = quantize(subtotal_d + gst_amount)
outstanding_amount = quantize(total_amount - paid_amount_d)
```

Outstanding amount always recomputed from persisted canonical values; never incrementally mutated to avoid accumulation error.
Payment Status Derivation:

- `PAID` if `paid_amount == total_amount`
- `PARTIAL` if `0 < paid_amount < total_amount`
- `PENDING` if `paid_amount == 0`
  Edits After Payments:
- Allowed (clarification). Recompute totals and recompute payment status (downgrade if necessary).
  Cancellation:
- `lifecycle_status == cancelled` informational; no operational restrictions (still editable & payable).
  Soft Delete:
- Replace hard delete with `is_deleted = TRUE` and timestamp update. Exclude in list queries. Detail returns invoice with `is_deleted` attribute.

## 5. Error Handling & Response Schema

Standard JSON shape (already used by global handlers in `main.py`):

```
{
  "status": "error",
  "error": { "code": "<UPPER_SNAKE_CODE>", "message": "Human readable", "details": <optional structured list/object> },
  "timestamp": <unix_epoch_seconds>,
  "path": "/api/v1/..."
}
```

Helper: `error_response(code: str, message: str, status_code: int = 400, details: Any|None=None)` centralizes shape; routers return/raise via FastAPI `HTTPException` or direct JSONResponse.
Codes (initial set):

- AUTH_INVALID_CREDENTIALS (401)
- AUTH_TOKEN_EXPIRED (401)
- VALIDATION_ERROR (422)
- INVOICE_NOT_FOUND (404)
- OVERPAY_NOT_ALLOWED (400)
- DB_ERROR (500)
- INTERNAL_SERVER_ERROR (500 fallback)

## 6. Input Normalization Strategy

Already implemented in Pydantic validators (camelCase → snake_case, numeric string coercion, blank to None, ISO datetime parsing). Will document in code comments + unify between create/update by extracting mapping dict if growth continues.

## 7. Configuration & Environment

Environment Variables:

- `DATABASE_URL` (existing)
- `DEFAULT_GST_RATE` (float; fallback 18.0) – used only when gst_rate omitted.
- `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_HOURS=24`.
  Future (Out of Scope): multi-currency, regional tax overrides.

## 8. Security

- Bcrypt password hashing via Passlib.
- JWT access tokens with 24h expiry; no refresh token mechanism.
- Token expiry test crafts expired token (set `exp` in past) to assert 401.
- No role-based authorization (future extension). All authenticated users act as operators.

## 9. Observability

Metrics (NFR-007):

- Counters: `invoice_created_total`, `invoice_updated_total`, `invoice_deleted_total`, `auth_login_success_total`, `auth_login_failure_total`.
- Gauge (optional future): `invoices_outstanding_amount_sum` (aggregate outstanding). Might defer until meaningful.
  Logging:
- Structured (JSON) log lines for auth + invoice lifecycle. Leverage standard logger + custom formatter (Phase 4).
  Performance Middleware: Already records response times and logs slow paths (>100ms). Potential extension: histogram metric.

## 10. Performance Approach

- Lightweight queries (limit 100) for list.
- Lazy addition of indices only after measuring (T018 + T041).
- Avoid N+1: current approach collects customer IDs; adequate for <=100 invoices.
- Consider join optimization later if query count measured >2 per request.

## 11. Testing Strategy

Test Pyramid:

- Contract / API Tests (Phase 2): Validate external behavior & schema (FR mapping).
- Integration Tests: Cross-entity & state transitions (customer reuse, payment recalculation).
- Unit Tests: Pure domain functions (GST math, payment status), error utils, service layer.
- Performance Tests: p95 assertions (best-effort harness using repeated invocation & timing; tolerant threshold exit on CI).
- Observability Verification: Metrics endpoint counters after operations.

Traceability (Expanded Mapping):

Functional Requirements:

- FR-001 Authentication (login) → T007/T008 (+ security hashing validated T060 indirectly)
- FR-003/FR-004/FR-008 Invoice creation & recompute after edits → T009, T015, T035, T049
- FR-005 Invoice numbering uniqueness & format → T057, T062
- FR-009/FR-010/FR-011/FR-025 Payment transitions & overpay prevention → T010, T011, T036
- FR-012 Cancellation semantics (non-restrictive) → T016, T053 (invariants)
- FR-013 Unknown field stripping → T056
- FR-014 Normalization (camelCase → snake_case) → T050
- FR-017 Detail view completeness/editable after payments → T044
- FR-018 Soft delete behavior → T026 (impl), T045 (tests)
- FR-019 Timestamp semantics → T058
- FR-020 Numeric string coercion → T050
- FR-021 Due date validation → T047
- FR-022 Default GST application → T046
- FR-023 Not found handling → T055
- FR-024 Canonical error codes list → Implementation section 5 + validated across contract tests (T007–T013, T044–T048, T055)

Non-Functional Requirements:

- NFR-001 Overall responsiveness (list) → T018
- NFR-002 Performance (creation) → T059, concurrency uniqueness T062
- NFR-003 Coverage thresholds → T004, T040
- NFR-007 Metrics/observability → T006, T028, T032, T054, T064
- NFR-008 Security token expiry → T048, boundary test T063
- NFR-009 Password hashing strength → T060
- NFR-010 Resilience DB error path → T051
- NFR-011 Monetary rounding correctness → T061 (plus implementation snippet above)
- NFR-012 Single currency assumption (documented) → Plan Section 7 (no test)

Accessibility & Meta:

- Accessibility (forms) → T042, T065
- Compliance / Traceability automation → T066

Each requirement now maps to at least one explicit test (or documented constraint where testing is non-applicable, e.g., NFR-012). A generated matrix (future T066) will codify this mapping programmatically.

Coverage Targets (NFR-003): enforce via `pytest --cov` gate (T004/T040).

## 12. Migration Strategy

- New revision for `is_deleted` column.
- No destructive changes to existing columns in this feature.
- Future: Additional revision(s) for indices (T041) if needed.
- Startup Removal: After Alembic confidence (T029 completed), remove legacy table creation call in `lifespan` (T030).

## 13. Soft Delete Implementation Details

- Modify DELETE route: set `invoice.is_deleted = True` and `invoice.updated_at = now`; DO NOT physically delete.
- List query adds `where(Invoice.is_deleted == False)`.
- Detail endpoint returns regardless of `is_deleted` (for referential integrity; FR-018).
- Responses include `is_deleted` field; update transformation function.

## 14. Remaining Ambiguities / Open Items

(Not blocking MVP but tracked for future clarification.)

- (Resolved) FR-001: Login accepts `identifier` (username OR email) + password; uniqueness enforced separately.
- (Resolved) FR-024: Canonical error codes enumerated; further additions treated as backlog items not blocking.
- Roles / permissions model (deferred).
- Multi-currency & currency formatting (NFR-012). Current assumption: single INR currency, store numeric decimals.

## 15. Out of Scope (Explicit Exclusions)

- Refresh tokens / session revocation.
- Role-based authorization & RBAC UI.
- Inventory, orders, and reporting endpoints (stubbed out only).
- Multi-currency, multi-tenant partitioning.
- Advanced tax regimes (IGST/CGST split) beyond single GST rate.

## 16. Risks & Mitigations

| Risk                                                       | Impact                        | Mitigation                                                        |
| ---------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------- |
| Changing invoice totals post-payment may confuse operators | Data inconsistency perception | Provide audit log later, display recalculated outstanding clearly |
| Soft delete omission in queries causing leakage            | Incorrect UI display          | Centralize query function / enforce filter in service layer       |
| Performance metrics not representative locally             | False negatives in CI         | Use relaxed thresholds & dataset generation helper                |
| Unstandardized error schema drift                          | Client parsing errors         | Central error helper + contract tests (T007–T013)                 |

## 17. Execution Phases (Task Alignment)

- Phase 1: Foundation (plan, error utils, metrics scaffolding)
- Phase 2: Contract & integration tests (fail-first for gaps)
- Phase 3: Implementation adjustments (soft delete, default GST integration, error schema adoption)
- Phase 4: Observability & migrations hardening
- Phase 5: Polish (refactors, docs, performance tuning, compliance report)

## 18. Tooling & Commands (Indicative)

```
# Run tests with coverage
printf "[tests]" && pytest -q --cov=backend/src --cov-report=term-missing
# Run performance tests subset
pytest -q -m perf
# Run lint/format (to be added)
make lint && make format
```

## 19. Service Layer Introduction (Refactor Plan)

Introduce `services/invoice_service.py` encapsulating:

- `create_invoice(data, db)`
- `update_invoice(invoice, changes, db)`
- `soft_delete_invoice(invoice, db)`
- `derive_payment_status(subtotal, gst_rate, paid_amount)` (pure function – unit tested)
  Routers delegate to service; tests for domain logic target pure functions where possible.

## 20. Glossary (Key Terms)

- Invoice Subtotal: Pre-tax amount entered by operator.
- GST Rate: Percentage applied to subtotal.
- GST Amount: Computed tax value.
- Total Amount: Subtotal + GST Amount.
- Paid Amount: Cumulative payments recorded.
- Outstanding Amount: Remaining balance.
- Payment Status: Derived state (PENDING, PARTIAL, PAID).
- Soft Delete: Logical deletion via boolean marker.
- Cancellation: Non-destructive marker flagging invoice as void-of-business-intent but still editable.

## 21. Validation & Exit Criteria

Delivery complete when:

- All Phase 1–5 tasks closed or explicitly deferred.
- Tests green with coverage thresholds met.
- Performance test indicates p95 under targets for synthetic dataset.
- Soft delete operational & verified by tests.
- Metrics endpoint exposes counters and increments validated.
- Compliance report (T043) generated referencing spec & requirements mapping.

---

End of Plan.
