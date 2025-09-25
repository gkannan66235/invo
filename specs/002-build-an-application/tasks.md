# Tasks: BillingBee Core Invoicing & Service Center Foundation

Feature Directory: `specs/002-build-an-application/`
Source Branch: `002-build-an-application`

NOTE: `plan.md` now created (T001) — remove A1 once validated; tasks updated to reflect clarifications (soft delete, editable tax after payments, cancellation non-restrictive).

Assumptions:

- A1 (to be retired): Tech stack already implemented (FastAPI backend, PostgreSQL, Next.js frontend) so setup tasks adapt to existing structure.
- A2: Error response schema standardized via helper (T002) adopted across routers.
- A3: Default GST rate provided by `DEFAULT_GST_RATE` env (T022) else 18.0.

## Numbered Tasks

### Phase 1: Setup & Quality Gates

- [x] T001 Create `specs/002-build-an-application/plan.md` capturing tech stack, layering (routers/services/models), testing approach. (File: `specs/002-build-an-application/plan.md`)
- [x] T002 Add shared error schema utility with helper `error_response(code, message, details=None)` (File: `backend/src/utils/errors.py`)
- [x] T003 [P] Add lint/test tasks to `Makefile` or `pyproject` (File: `backend/Makefile`) ensuring targets: `lint`, `test`, `format`.
- [x] T004 [P] Add coverage threshold enforcement in `pytest.ini` (>=80% total, >=90% invoice domain) (File: `backend/pytest.ini`).
- [x] T005 [P] Add performance test harness skeleton (locustfile or pytest performance markers) (File: `backend/tests/performance/test_invoice_perf.py`).
- [x] T006 [P] Add observability metrics counters for auth & invoices (File: `backend/src/config/observability.py`).

### Phase 2: Tests First (TDD)

Contract & scenario tests created before (or refactored in place). Existing implementation will cause some passes; enhance assertions (error schema, soft delete, default GST omission, token expiry) so new tests fail prior to implementation adjustments.

- [x] T007 Contract test: login success returns token & structure (File: `backend/tests/contract/test_auth_login.py`). (Depends: T001, T004)
- [x] T008 [P] Contract test: login failure wrong password returns 401 error schema (File: `backend/tests/contract/test_auth_login_fail.py`).
- [x] T009 [P] Contract test: POST /api/v1/invoices creates invoice & GST math (File: `backend/tests/contract/test_invoices_create.py`).
- [x] T010 [P] Contract test: PATCH /api/v1/invoices/{id} partial payment transitions status (File: `backend/tests/contract/test_invoices_payment_transition.py`).
- [x] T011 [P] Contract test: PATCH /api/v1/invoices/{id} overpay → 400 with error schema (File: `backend/tests/contract/test_invoices_overpay.py`).
- [x] T012 [P] Contract test: GET /api/v1/invoices list ordering newest first (File: `backend/tests/contract/test_invoices_list.py`).
- [x] T013 [P] Contract test: Validation missing customer/amount returns 422 structured error (File: `backend/tests/contract/test_invoices_validation.py`).
- [x] T014 [P] Integration test: Reuse existing customer on duplicate create (File: `backend/tests/integration/test_customer_dedup.py`).
- [x] T015 [P] Integration test: Update amount & gst_rate triggers recompute (File: `backend/tests/integration/test_invoice_recompute.py`).
- [x] T016 [P] Integration test: Cancellation sets `lifecycle_status=cancelled` and still allows subsequent payment (File: `backend/tests/integration/test_invoice_cancel.py`). (Maps FR-012)
- [x] T017 [P] Integration test: Numeric string coercion (amount, gst_rate) (File: `backend/tests/integration/test_invoice_numeric_string.py`).
- [x] T018 [P] Performance test: list 100 invoices <200ms p95 harness (File: `backend/tests/performance/test_invoice_perf.py`). (Depends: T005)

### Phase 3: Core Implementation Adjustments

(Apply only after ensuring tests fail on stricter expectations.)

- [x] T019 Implement plan.md decisions (codify layering notes) (File: `specs/002-build-an-application/plan.md`). (Depends: T001) # Layering annotations & env-driven auth added.
- [x] T020 Standard error response builder & adopt in auth router (File: `backend/src/routers/auth.py`). (Depends: T002, T007, T008) # Auth now sets standardized codes; global handler shapes envelope.
- [x] T021 [Sequential] Adopt error response builder in invoices router (File: `backend/src/routers/invoices.py`). (Depends: T020, tests T009-T013) # Invoices uses domain-specific INVOICE_NOT_FOUND code + standardized error codes.
- [x] T022 Add default GST rate config in settings (File: `backend/src/config/settings.py`). (Depends: T001)
- [x] T023 Enforce default GST when omitted and use config value (File: `backend/src/routers/invoices.py`). (Depends: T022, T021)
- [ ] T024 (REMOVED) Clarification allows tax edits after payment — no lock task.
- [ ] T025 (REMOVED) Cancellation remains non-restrictive — no payment block implementation.
- [x] T026 Introduce soft delete (is_deleted flag) instead of hard delete (File: `backend/src/models/database.py`, `backend/src/routers/invoices.py`). (Depends: T021)
- [x] T027 List invoices endpoint filter out soft-deleted (File: `backend/src/routers/invoices.py`). (Depends: T026)
- [x] T028 Add invoice metrics emission (create/update/delete counters) (File: `backend/src/routers/invoices.py`, `backend/src/config/observability.py`). (Depends: T006) # Counters emitted on create/update/delete.

### Phase 4: Integration & Observability

- [x] T029 Ensure migrations reflect soft delete & GST default changes (File: `backend/alembic/versions/<new>.py`). (Depends: T026, T022) # Soft delete migration exists; GST default is config-only.
- [x] T030 Remove legacy `create_database_tables_async()` from startup post-migration confidence (File: `backend/src/main.py`). (Depends: Alembic validated)
- [x] T031 Add structured logging for auth + invoice lifecycle (File: `backend/src/config/logging.py`, `backend/src/routers/*`). (Depends: T020, T021)
- [x] T032 Add Prometheus metrics registration for new counters (File: `backend/src/config/observability.py`). (Depends: T028)
- [x] T033 Add health & readiness endpoints (File: `backend/src/routers/system.py`).

### Phase 5: Quality & Polish

- [x] T034 [P] Add unit tests for error utils (File: `backend/tests/unit/test_errors.py`). (Depends: T002)
- [x] T035 [P] Add unit tests for GST calculation edge (0, high values) (File: `backend/tests/unit/test_gst_math.py`).
- [x] T036 [P] Add unit tests for payment transitions logic (File: `backend/tests/unit/test_payment_status.py`).
- [x] T037 [P] Refactor duplication in invoices router (extract service layer) (File: `backend/src/services/invoice_service.py`). (Depends: T021)
- [x] T038 [P] Add service layer unit tests (File: `backend/tests/unit/test_invoice_service.py`). (Depends: T037)
- [x] T039 [P] Documentation update: API endpoints & examples (File: `docs/api/invoices.md`). (Depends: T021)
- [x] T040 [P] Coverage report verification & thresholds gate CI (File: `.github/workflows/ci.yml`). (Depends: T004, tests complete)
  - Note: Post-implementation stabilization included unifying async DB session fixtures to resolve teardown hang (no new task ID assigned; recorded for traceability).
- [x] T041 [P] Performance optimization pass (DB indices on invoice date, payment status) (File: `backend/alembic/versions/20250925_0003_add_perf_indexes.py`). (Depends: profiling results T018) # Added partial & date indexes + COUNT optimization.
- [ ] T042 [P] Accessibility checklist update for frontend forms (File: `frontend/docs/accessibility.md`).
- [ ] T043 [P] Final constitutional compliance audit log (File: `specs/002-build-an-application/compliance-report.md`).

## Dependencies Summary

- T001 precedes any plan dependent tasks (T019, T022)
- Error utility (T002) precedes router adoptions (T020, T021)
- Tests (T007-T018) precede modifications (T020-T028)
- Soft delete implementation (T026) before filtering and migration adjustments (T027, T029)
- Observability counters (T006) before metrics emission (T028, T032)
- Service layer refactor after stable router (T037 after T021)

## Parallelizable Groups Examples

Group A (after T001, T002, T004 ready):

- T008, T009, T010, T011, T012, T013 (contract tests) [P]

Group B (after T021):

- T034, T035, T036, T037, T039 [P]

Group C (observability after T028):

- T032, T031 (partial overlap but avoid same file conflicts) — mark only T032 [P]

## Execution Hints

- Ensure each test task initially asserts new error schema so it fails before implementation modifications.
- Commit after each task or coherent parallel batch.
- Update migrations with new revisions; never edit old revision files.

### Phase 6: Clarification-Driven Additions

- [x] T044 Contract test: GET /api/v1/invoices/{id} detail includes required fields & editable after payments (File: `backend/tests/contract/test_invoices_detail.py`). (Maps FR-017, FR-008)
- [ ] T045 Contract + integration tests: Soft delete hides from list but detail accessible (File: `backend/tests/contract/test_invoices_soft_delete.py`, `backend/tests/integration/test_invoices_soft_delete_flow.py`). (Depends: T026/T027; Maps FR-018)
- [x] T045 Contract + integration tests: Soft delete hides from list but detail accessible (File: `backend/tests/contract/test_invoices_soft_delete.py`, `backend/tests/integration/test_invoices_soft_delete_flow.py`). (Depends: T026/T027; Maps FR-018)
- [x] T046 Contract test: Omitted gst_rate applies DEFAULT_GST_RATE env (File: `backend/tests/contract/test_invoices_default_gst.py`). (Maps FR-022)
- [x] T047 Contract test: Malformed due_date rejected with VALIDATION_ERROR (File: `backend/tests/contract/test_invoices_due_date_validation.py`). (Maps FR-021)
- [x] T048 Contract test: Expired JWT returns 401 AUTH_TOKEN_EXPIRED (File: `backend/tests/contract/test_auth_token_expired.py`). (Maps NFR-008)
- [x] T049 Unit test: Payment status downgrade after amount/gst edit (File: `backend/tests/unit/test_payment_status_downgrade.py`). (Maps FR-008)
- [ ] T050 Unit test: Normalization of camelCase & numeric strings (File: `backend/tests/unit/test_invoice_normalization.py`). (Maps FR-013/FR-014/FR-020)
- [ ] T051 Integration test: Simulated DB failure returns standardized DB_ERROR (File: `backend/tests/integration/test_db_failure_resilience.py`). (Maps NFR-010)
- [ ] T052 Service layer unit tests post-refactor (File: `backend/tests/unit/test_invoice_service_refactored.py`). (Depends: T037)
- [ ] T053 Unit test: Cancelled invoice invariants (only allowed fields editable; payments still permitted) (File: `backend/tests/unit/test_cancel_invariants.py`). (Maps FR-016, FR-017)
- [ ] T054 Metrics test: Counters increment after operations (File: `backend/tests/integration/test_metrics_counters.py`). (Depends: T028, T032; Maps NFR-007)

### Phase 7: Remediation (Coverage & Clarifications)

- [ ] T055 Contract test: PATCH non-existent invoice returns 404 `INVOICE_NOT_FOUND` (File: `backend/tests/contract/test_invoices_update_not_found.py`). (Maps FR-023)
- [ ] T056 Unit test: Unknown extra fields dropped & absent in response (File: `backend/tests/unit/test_invoice_unknown_fields.py`). (Maps FR-013)

### Phase 8: Expanded Coverage & Performance Hardening

- [ ] T057 Contract test: Invoice number format & uniqueness `INV-YYYYMMDD-NNNN` (File: `backend/tests/contract/test_invoice_numbering.py`). (Maps FR-005)
- [ ] T058 Integration test: `created_at` immutable; `updated_at` changes on update (File: `backend/tests/integration/test_invoice_timestamps.py`). (Maps FR-019)
- [ ] T059 Performance test: invoice creation p95 <300ms (File: `backend/tests/performance/test_invoice_creation_perf.py`). (Maps NFR-002)
- [ ] T060 Security test: bcrypt hash cost factor >=12 (File: `backend/tests/unit/test_password_hash_cost.py`). (Maps NFR-009)
- [ ] T061 Unit test: Monetary rounding HALF_UP edge cases (.005, .004, large values) (File: `backend/tests/unit/test_rounding.py`). (Maps NFR-011)
- [ ] T062 Concurrency test: Parallel invoice creation preserves uniqueness (File: `backend/tests/integration/test_invoice_number_race.py`). (Maps FR-005, NFR-002)
- [ ] T063 Unit test: JWT TTL boundary (token valid just before 24h, invalid after) (File: `backend/tests/unit/test_jwt_ttl.py`). (Maps NFR-008)
- [ ] T064 Metrics audit test: Counter & labels naming consistency (File: `backend/tests/unit/test_metrics_naming.py`). (Maps NFR-007)
- [ ] T065 Accessibility test: Keyboard-only navigation & ARIA labels invoice form (File: `frontend/tests/a11y/test_invoice_form_accessibility.ts`). (Maps A11Y)
- [ ] T066 Traceability script: auto-generate FR/NFR → task matrix (File: `scripts/gen_traceability_matrix.py`). (Meta compliance)

## Removed / Superseded Tasks Log

- T024 (lock tax edits) removed per clarification allowing post-payment edits.
- T025 (block payment after cancel) removed per clarification: cancellation non-restrictive.

## Validation Checklist

- All FR-001..FR-025 mapped to at least one test or implementation task (including remediation tasks T044–T056 and expanded coverage T057–T066).
- NFR performance & coverage tasks included (T005, T018, T040, T041).
- Observability tasks (T006, T028, T032, T031, T054) present.
- Accessibility & documentation tasks (T042, T039) included.
- Compliance audit task (T043) ensures final review.
