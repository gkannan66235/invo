# Tasks: Customer & Invoice Localisation + Printable Invoices & Core Management Modules

Feature Directory: `specs/003-customer-nsupport-only/`
Plan Artifacts: research.md, data-model.md, contracts/, quickstart.md

Legend:

- [P] = Can run in parallel with other [P] tasks (different files / no ordering dependency)
- Dependencies listed as task IDs that must complete first
- Contract tests & integration tests precede implementation (TDD)

## High-Level Dependency Flow

Setup → (Contract Tests + Integration Tests + Model Migrations) → Services → Routers/Endpoints → PDF/Observability/Audit → Frontend Adjustments → Performance/Polish → Docs

---

## Numbered Tasks

### Phase A: Setup & Baseline

T001. Ensure branch `003-customer-nsupport-only` is active & sync with main (no uncommitted changes) [X]

- Output: Clean working tree
- File(s): n/a

T002. Backend dependency review: add Playwright dependency & PDF helper placeholder [X]

- File(s): `backend/requirements.txt` (or introduce optional extras), new `backend/src/services/pdf_service.py`
- Dependency: T001

T003. Add lint/test pre-commit hooks update (ruff/black config confirm) [P] [X]

- File(s): `.pre-commit-config.yaml` (if exists) or create
- Dependency: T001

T004. Confirm observability config extensibility for new metrics (pdf_generate, invoice_download, customer_duplicate_warning) [P] [X]

- File(s): `backend/src/config/observability.py`
- Dependency: T001

### Phase B: Data Model & Migrations (Models before services)

T005. Create Alembic migration for new tables & columns [X]:

- Tables: `customer`, `inventory_item`, `invoice_line`, `invoice_download_audit`
- Columns added to `invoice`: branding_snapshot, gst_rate_snapshot, settings_snapshot (if absent)
- Indexes: idx_customer_mobile, idx_invoice_customer, idx_audit_invoice, idx_audit_user
- File(s): `backend/alembic/versions/<timestamp>_customer_inventory_invoice_pdf.py`
- Dependency: T002

T006. SQLAlchemy models (if not present) for Customer, InventoryItem, InvoiceLine, InvoiceDownloadAudit [X]

- File(s): `backend/src/models/database.py`
- Dependency: T005

### Phase C: Contract Tests (One per contract) – Parallelizable

T007. Contract test: Customers API list/create/get/update (duplicate warning field) [P] [X]

- File(s): `backend/src/tests/contract/test_customers_contract.py`
- Dependencies: T005

T008. Contract test: Inventory API list/create/update [P] [X]

- File(s): `backend/src/tests/contract/test_inventory_contract.py`
- Dependencies: T005

T009. Contract test: Invoices API create/list/get, ensures INR fields & snapshot placeholders [P] [X]

- File(s): `backend/src/tests/contract/test_invoices_contract.py`
- Dependencies: T005

T010. Contract test: Invoice PDF download endpoint (content-type, audit log inserted) [P] [X]

- File(s): `backend/src/tests/contract/test_invoice_pdf_contract.py`
- Dependencies: T005

T011. Contract test: Settings API get/patch (GST rate prospective) [P] [X]

- File(s): `backend/src/tests/contract/test_settings_contract.py`
- Dependencies: T005

### Phase D: Integration Tests (User Scenarios) – Parallelizable after migrations

T012. Integration test: Invalid Indian mobile rejected scenario [P] [X]

- File(s): `backend/src/tests/integration/test_customer_mobile_validation.py`
- Dependencies: T005

T013. Integration test: Duplicate mobile warning flow [P] [X]

- File(s): `backend/src/tests/integration/test_customer_duplicate_warning.py`
- Dependencies: T005

T014. Integration test: Invoice creation INR formatting & totals [P] [X]

- File(s): `backend/src/tests/integration/test_invoice_inr_formatting.py`
- Dependencies: T005

T015. Integration test: Printable & PDF generation + audit logged [P] [X]

- File(s): `backend/src/tests/integration/test_invoice_pdf_audit.py`
- Dependencies: T005

T016. Integration test: Settings update prospective GST application [P] [X]

- File(s): `backend/src/tests/integration/test_settings_gst_prospective.py`
- Dependencies: T005

T017. Integration test: Cancelled vs soft-deleted invoice access control [P] [X]

- File(s): `backend/src/tests/integration/test_invoice_soft_delete_access.py`
- Dependencies: T005

### Phase E: Service Layer Implementations (Sequential per shared file)

T018. Implement Customer service: create (normalize, duplicate check), update [X]

- File(s): `backend/src/services/customer_service.py`
- Dependencies: T007 T012 T013

T019. Implement Inventory service CRUD (activate/deactivate) [X]

- File(s): `backend/src/services/inventory_service.py`
- Dependencies: T008

T020. Extend Invoice service for snapshot fields & lines, settings snapshot [X]

- File(s): `backend/src/services/invoice_service.py`
- Dependencies: T009 T014 T016

T021. Implement PDF service (HTML render + Playwright print) & caching hook [X]

- File(s): `backend/src/services/pdf_service.py`
- Dependencies: T010 T015 T018 T020

T022. Implement Settings service (get/update with prospective GST logic) [X]

- File(s): `backend/src/services/settings_service.py`
- Dependencies: T011 T016

T023. Implement Audit logging service (async write) for downloads [X]

- File(s): `backend/src/services/audit_service.py`
- Dependencies: T010 T015 T021

### Phase F: Routers / API Endpoints

T024. Add `customers.py` router (list/create/get/update) wiring to service [X]

- File(s): `backend/src/routers/customers.py`
- Dependencies: T018

T025. Add `inventory.py` router (list/create/update/deactivate) [X]

- File(s): `backend/src/routers/inventory.py`
- Dependencies: T019

T026. Extend existing `invoices.py` router: create/list/get use new service logic & add lines snapshot [X]

- File(s): `backend/src/routers/invoices.py`
- Dependencies: T020

T027. Add PDF download route `/api/v1/invoices/{id}/pdf` using pdf_service & audit service [X]

- File(s): `backend/src/routers/invoices.py`
- Dependencies: T021 T023

T028. Add `settings.py` router (get/patch) admin-only guard [X]

- File(s): `backend/src/routers/settings.py`
- Dependencies: T022

### Phase G: Observability & Metrics

T029. Add new metrics instruments (counters/histograms) and integrate into services [X]

- File(s): `backend/src/config/observability.py`, service files
- Dependencies: T021 T023

T030. Add performance test for PDF generation p95 (<2s) & duplicate lookup (<50ms) [P] [X]

- File(s): `backend/src/tests/performance/test_pdf_performance.py`
- Dependencies: T021

### Phase H: Frontend Integration

T031. Frontend API layer additions: customers, inventory, settings, invoice PDF fetch [X]

- File(s): `frontend/src/lib/api.ts`, new util modules
- Dependencies: T024 T025 T027 T028
- Notes: Added customersApi, inventoryApi, settingsApi, invoiceApi.downloadPdf plus supporting types.

T032. UI Components: Customer management screens (list/create/edit), duplicate warning toast [X]

- File(s): `frontend/src/app/customers/page.tsx`
- Dependencies: T031
- Notes: Implemented list + create with duplicate_warning toast indicator.

T033. UI Components: Inventory management screens [X]

- File(s): `frontend/src/app/inventory/page.tsx`
- Dependencies: T031
- Notes: Basic CRUD subset (create + deactivate + list) aligned with backend endpoints.

T034. UI Components: Settings screen (GST update, branding) [X]

- File(s): `frontend/src/app/settings/page.tsx`
- Dependencies: T031
- Notes: Supports viewing & updating default GST rate; branding placeholder.

T035. Invoice printable view & print button + PDF download integration [X]

- File(s): `frontend/src/app/invoices/[id]/print/page.tsx`
- Dependencies: T027 T031
- Notes: Printable layout with print + PDF download button; pulls invoice & renders summary.

### Phase I: Polish & Documentation

T036. Add unit tests for formatting util (Indian digit grouping) [P] [X]

- File(s): `backend/src/tests/unit/test_indian_formatting.py`
- Dependencies: T020

T037. Add unit tests for mobile normalization edge cases [P] [X]

- File(s): `backend/src/tests/unit/test_mobile_normalization.py`
- Dependencies: T018

T038. Documentation: `docs/api/customers.md`, update invoices doc with PDF endpoint & metrics [P] [X]

- File(s): `docs/api/customers.md`, `docs/api/invoices.md`
- Dependencies: T024 T027 T029

T039. Update README and feature spec progress checklist (mark tasks & artifacts) [P] [X]

- File(s): `README.md`, `specs/003-customer-nsupport-only/spec.md`
- Dependencies: T038

T040. Final lint & coverage gate execution, adjust any missing tests

- File(s): n/a (CI pipeline)
- Dependencies: T036 T037 T030 T035

### Phase J: Validation

T041. Run quickstart walkthrough & record results (attach run log) – ensure all scenarios pass

- File(s): `specs/003-customer-nsupport-only/quickstart.md` (append results section)
- Dependencies: T040

---

## Parallel Execution Guidance

Example parallel batches:

- Batch 1 (after T005): T007 [P], T008 [P], T009 [P], T010 [P], T011 [P], T012 [P], T013 [P], T014 [P], T015 [P], T016 [P], T017 [P]
- Batch 2 (later): T030 [P], T036 [P], T037 [P], T038 [P], T039 [P]

Ensure shared-file sequential tasks not parallelized (e.g., T026 & T027 both modify `invoices.py`).

## Task Agent Command Examples

To execute a task (conceptual examples):

- Implement migration (T005): "Apply migration creating customer/inventory/invoice_line/audit tables plus invoice snapshot columns"
- Create contract test (T007): "Write failing test for /api/v1/customers create duplicating normalized mobile warning"

## Completion Criteria

- All contract & integration tests initially fail then pass after implementation tasks
- Performance test demonstrates PDF p95 <2s and duplicate lookup <50ms
- Audit logging entries verifiable
- Documentation updated and quickstart scenarios validated

---

## Initial Sprint Subset (Focused Vertical Slice)

Purpose: Deliver core backend functionality (customers, invoices with INR & snapshots, settings, minimal PDF + audit, duplicate warning) quickly while deferring inventory, full PDF polish, frontend UI, and performance benchmarking.

### Included Task IDs

- Setup/Foundation: T001, T002 (skip T003/T004 for later unless trivial)
- Migrations & Models: T005, T006 (Inventory table optional – can defer)
- Contract Tests: T007, T009, T010, T011 (skip T008)
- Integration Tests: T012, T013, T014, T015, T016 (skip T017)
- Services: T018, T020, T021 (stub/minimal PDF), T022, T023 (synchronous insert first)
- Routers: T024, T026, T027, T028 (skip inventory router T025)
- Observability: T029 (partial metrics for implemented services only)
- Unit Tests: T037 (mobile normalization) (defer T036)
- Validation & Wrap: T040 (partial – ignore performance gating), T041 (partial quickstart results for scenarios 1–5 only)

### Deferred to Later Sprints

- Inventory (T008, T019, T025, related UI tasks)
- Soft-delete access control test (T017)
- Full PDF styling/caching & performance test (T030, advanced part of T021)
- Digit grouping util & tests (T036)
- Frontend integration & UI (T031–T035)
- Docs & polish (T038, T039 full scope)

### Sprint Acceptance Criteria

1. All included contract & integration tests pass.
2. Creating second customer with same normalized mobile returns `duplicate_warning=true`.
3. Invoice creation returns currency='INR' and stores snapshot placeholders.
4. Settings GST rate change affects only subsequent invoices.
5. PDF endpoint returns non-empty PDF bytes and writes audit record.
6. Metrics objects registered (no runtime errors on import) for: customer_create, duplicate_warning, pdf_generate, invoice_download.
7. Mobile normalization unit tests pass (T037).

### Recommended Execution Order

1. T001 → T002 → T005 → T006
2. Author failing tests: T007, T009, T010, T011, T012–T016, T037
3. Implement services/endpoints: T018 → T020 → T022 → T024 → T026 → T021 (stub) → T023 (sync) → T027 → T028 → T029 (partial)
4. Run full test suite & fix (T040 partial)
5. Execute quickstart scenarios 1–5 (T041 partial) and record outcomes.

### Notes

- PDF service (T021) may initially return a simple PDF (e.g., generated via minimal HTML + headless Chromium) without full styling or caching.
- Audit logging (T023) synchronous now; can be optimized later with background tasks.
- If Inventory model/table deferred, adjust migration (T005) to exclude it to reduce scope.

---
