# Feature Specification: BillingBee Core Invoicing & Service Center Foundation

**Feature Branch**: `002-build-an-application`  
**Created**: 2025-09-24  
**Status**: Draft  
**Input**: User description: "Develop BillingBee - a Service Center Management System (GST-compliant) starting with secure login and ability to create, view, update, and manage service invoices (with GST calculations) for customers."

## Clarifications

### Session 2025-09-24

- Q: What is the canonical deletion behavior for invoices? → A: Soft delete (is_deleted flag); excluded from list endpoints; detail endpoint still returns invoice with `is_deleted=true`.
- Q: After payments begin, can amount/gst_rate be modified? → A: Always editable; recompute totals & payment status each change.
- Q: What is the access token expiry strategy? → A: 24 hours (no refresh tokens in this feature scope).
- Q: What are the operational effects of cancelling an invoice? → A: Cancellation is a lifecycle marker only; all edits & payments remain allowed; visibility unchanged unless a future filter hides cancelled.
- Q: How is the default GST rate defined & overridden? → A: Environment variable `DEFAULT_GST_RATE` (numeric) with fallback 18%.

**Applied Changes:**

- Adopted soft delete strategy (no hard purge in this feature scope).
- Listing endpoints MUST filter out `is_deleted=true` invoices unless an explicit admin/audit filter is added later.
- `GET /api/v1/invoices/{id}` MUST return soft-deleted invoices including `is_deleted=true` so historical references remain resolvable.

## User Scenarios & Testing _(mandatory)_

### Primary User Story

A service center operator logs into BillingBee, creates a new service invoice for a walk-in or returning customer (capturing customer contact, service performed, taxable amount, and GST), reviews computed GST and total, optionally edits or updates payment status later, and tracks outstanding amounts.

### Acceptance Scenarios

1. **Given** a valid operator account exists, **When** the operator logs in with correct credentials, **Then** the system authenticates and returns an access token enabling protected invoice operations.
2. **Given** the operator is authenticated and enters customer name, phone, service description, amount, and GST rate, **When** they submit the form, **Then** the system creates an invoice, auto-computes GST amount and total, assigns an invoice number, and shows it in the invoice list.
3. **Given** an existing invoice with pending status, **When** the operator records a partial payment, **Then** the outstanding amount reflects the remaining balance and status indicates a partial payment state.
4. **Given** an existing invoice, **When** the operator updates the amount or GST rate, **Then** the system recalculates GST and total and preserves historical invoice identity (same invoice number).
5. **Given** an invoice marked fully paid, **When** the operator attempts to set a paid amount exceeding total, **Then** the system rejects the action with a validation message.
6. **Given** a list of invoices, **When** the operator retrieves the list, **Then** invoices are ordered newest first and include computed outstanding amounts.
7. **Given** invalid invoice input (missing mandatory customer identity or amount), **When** submitted, **Then** the system rejects it with clear validation messaging.

### Edge Cases

- What happens when amount is zero? → Allow draft; GST = 0; total = 0.
- How does system handle duplicate customer (same name + phone)? → Reuse existing customer record (no duplicate created).
- What if GST rate is omitted? → Apply `DEFAULT_GST_RATE` env value if set, else 18% (see FR-022).
- What if user updates GST rate after partial payment? → Edits allowed; recompute totals & possibly downgrade payment status (FR-008a).
- Attempt to overpay (paid_amount > total). → Reject with standardized error schema (OVERPAY_NOT_ALLOWED).
- Attempt to mark cancelled invoice as paid. → Allowed; cancellation is informational (FR-012).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST authenticate users via credential-based login (username and/or email + password). [NEEDS CLARIFICATION: Is email login officially supported long-term or only username?]
- **FR-002**: System MUST issue a secure session token upon successful authentication for protected operations.
- **FR-003**: System MUST allow creation of a service invoice with minimally: customer name, customer phone, service description, taxable amount.
- **FR-004**: System MUST compute GST amount = round(amount \* gst_rate / 100, 2) and total = amount + GST.
- **FR-005**: System MUST assign a unique sequential invoice number pattern including date prefix.
- **FR-006**: System MUST reuse existing customer records when name and phone match exactly.
- **FR-007**: System MUST allow updating invoice fields: amount, gst_rate, service description, due date, notes, paid amount, status (draft/sent/paid/cancelled).
- **FR-008**: System MUST recalculate GST and totals whenever amount or gst_rate changes.
- **FR-008a**: Amount and gst_rate remain editable even after partial or full payments; after any edit the system MUST recompute gst_amount, total_amount, outstanding_amount and re-derive payment_status (if paid_amount now < total_amount, downgrade status appropriately).
- **FR-009**: System MUST prevent paid_amount from exceeding total_amount or being negative.
- **FR-010**: System MUST derive payment status automatically based on paid_amount vs total (pending/partial/paid) unless explicitly overridden by an allowed status control.
- **FR-011**: System MUST show outstanding amount = total_amount - paid_amount for each invoice.
- **FR-012**: System MUST support a `lifecycle_status` value `cancelled` as a non-destructive lifecycle marker; cancellation does NOT freeze edits or payments and cancelled invoices remain visible in standard listings (future filters may optionally exclude them).
- **FR-013**: System MUST ignore unrecognized extra fields in invoice create/update submissions (forward compatibility).
- **FR-014**: System MUST normalize camelCase and snake_case invoice payload fields equivalently.
- **FR-015**: System MUST validate required fields (customer identity + amount) for invoice creation.
- **FR-016**: System MUST allow retrieving a list of recent invoices ordered newest first.
- **FR-017**: System MUST provide detail view for a single invoice by id.
- **FR-018**: System MUST soft delete invoices using an `is_deleted` boolean flag; soft-deleted invoices are excluded from standard list retrieval and still retrievable via detail view (`GET /api/v1/invoices/{id}`) with `is_deleted=true` in the payload.
- **FR-019**: System MUST retain audit timestamps (created/updated) for invoices.
- **FR-020**: System MUST ensure numeric inputs accept numeric strings where logically convertible (UX resilience).
- **FR-021**: System MUST reject malformed date inputs for due dates with clear validation error.
- **FR-022**: System MUST default gst_rate to the float value of environment variable `DEFAULT_GST_RATE` if set, otherwise 18.0, when omitted; returned invoice payloads MUST include the applied gst_rate.
- **FR-023**: System MUST prevent update attempts on non-existent invoices with a not found response.
- **FR-024**: System MUST provide clear error messaging for validation failures (field-specific cause where possible) using the standardized error schema (`status`, `error.code`, `error.message`, optional `error.details`, plus `timestamp` & `path`).
- **FR-025**: System MUST allow partial payments and reflect partial status.

### Key Entities

- **User**: Represents an operator authorized to manage invoices; attributes include identity credentials and role (future extension for roles/permissions). [NEEDS CLARIFICATION: Roles required?]
- **Customer**: Represents a service recipient with identifying contact info (name, phone, optional email) reused across invoices.
- **Invoice**: Commercial document capturing service details, tax computation (subtotal, gst_rate, gst_amount, total_amount), payment tracking (paid_amount, outstanding_amount, payment_status), lifecycle state (status/cancellation), and due date.

### Non-Functional Requirements

- **NFR-001**: Performance - Standard invoice list retrieval MUST respond within 200ms (95th percentile) for <= 100 invoices.
- **NFR-002**: Performance - Invoice creation MUST complete within 300ms (95th percentile) including customer lookup/creation.
- **NFR-003**: Quality - Automated tests MUST cover core invoice creation, update (GST recompute), payment transitions, and validation edge cases (>= 90% coverage of invoice domain functions, >= 80% overall line coverage).
- **NFR-004**: UX - Validation errors MUST specify offending field and reason in plain language.
- **NFR-005**: Accessibility - Web UI MUST follow WCAG 2.1 AA for form controls and focus management (error messaging accessible to screen readers).
- **NFR-006**: Observability - System MUST emit structured logs for invoice create/update/delete and authentication events.
- **NFR-007**: Observability - Basic metrics MUST include invoice count, create rate, update rate, error rate, auth failures.
- **NFR-008**: Security - Access JWT tokens MUST expire in 24 hours (no refresh token mechanism in this feature scope); post-expiry any protected endpoint access MUST return 401 with standardized error schema.
- **NFR-009**: Security - Password handling MUST use strong one-way hashing (bcrypt or better). (Informational; no implementation detail expansion.)
- **NFR-010**: Reliability - System MUST gracefully handle database connectivity loss with explicit error response (no silent failures).
- **NFR-011**: Data Integrity - Tax calculations MUST round consistently using standard rounding to 2 decimal places.
- **NFR-012**: Internationalization - Monetary fields MUST store exact numeric values (no floating precision drift beyond 2 decimals). [NEEDS CLARIFICATION: Currency multi-support needed?]

## Review & Acceptance Checklist

### Content Quality

- [ ] No implementation details (languages, frameworks, APIs) beyond unavoidable domain precision
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

### Constitutional Compliance

- [ ] Performance benchmarks specified
- [ ] Test coverage requirements included
- [ ] User experience consistency addressed
- [ ] Accessibility requirements specified
- [ ] Observability requirements included

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed (pending clarification resolution)
