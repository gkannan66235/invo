# Feature Specification: Customer & Invoice Localisation + Printable Invoices & Core Management Modules

**Feature Branch**: `003-customer-nsupport-only`  
**Created**: 2025-09-25  
**Status**: Draft  
**Input**: User description: "Customer:\nSupport only india mobile number & address\nInvoice:\nUse Indian Rupees\nAble to print/ download invoice\nModule to manage Inventory, customer and Settings"

## User Scenarios & Testing _(mandatory)_

### Primary User Story

As an operator of the GST Service Center, I want to record customer details (with valid Indian contact information), create invoices denominated in Indian Rupees (₹), and provide a printable/downloadable invoice document so I can serve walk‑in and remote customers efficiently. I also need dedicated modules to view and manage inventory items, customer records, and application settings (tax rates, branding, numbering preferences) in one system.

### Acceptance Scenarios

1. **Given** a new customer form, **When** I enter a mobile number not matching Indian numbering rules, **Then** the system must reject it with a clear validation message referencing allowed format.
2. **Given** an invoice creation flow, **When** I submit valid data, **Then** the saved invoice displays currency amounts with the Indian Rupee symbol (₹) and Indian digit grouping (e.g., 1,23,456.78).
3. **Given** an existing invoice, **When** I click "Print" or "Download", **Then** a document (HTML print view and downloadable PDF) is generated containing all required invoice elements (seller info, customer info, line/service description, tax breakdown, totals, invoice number, issue date) and is visually optimized for A4 printing.
4. **Given** I open the Inventory module, **When** I search or filter, **Then** I can view, add, edit, or deactivate inventory/service items according to role permissions (admin: full, operator: manage items, viewer: read-only).
5. **Given** I open Settings, **When** I adjust default GST rate or company address, **Then** new invoices created thereafter reflect the updated defaults.
6. **Given** a previously downloaded invoice, **When** I re-download after settings (branding/logo) changes, **Then** it shows the original branding captured at issuance (invoices are immutable snapshots).

### Edge Cases

- Customer mobile contains spaces, dashes, or country code (+91); system should normalize and accept if valid after cleaning.
- Attempt to use non-Indian country code: system rejects with explicit "Only Indian mobile numbers supported" message.
- Invoice large monetary values (crores) must render correctly with grouping and without overflow in PDF layout.
- Printing when logo asset missing → fallback placeholder or text title.
- Download request for an invoice that was soft-deleted or cancelled → allowed for cancelled; blocked for soft-deleted.
- Settings change while an invoice print job in progress → clarify whether job uses snapshot or latest.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST validate and accept only Indian mobile numbers: 10 digits starting with 6–9; optional +91 / 91 prefix accepted and stripped; stored canonical form is 10 digits.
- **FR-002**: System MUST store and expose a single address line (max 255 chars) and optional city field.
- **FR-003**: System MUST persist invoices with currency explicitly set/presented as Indian Rupees (symbol ₹ and ISO code INR).
- **FR-004**: System MUST display monetary values on invoice views and documents using INR formatting (symbol placement before amount).
- **FR-005**: System MUST generate a printable invoice view suitable for standard A4 portrait layout with controlled styles (headers, section grouping, tax breakdown).
- **FR-006**: System MUST allow downloading an invoice as a PDF document matching the print layout fidelity.
- **FR-007**: System MUST include on the printable/downloadable invoice: seller identity, seller address, customer name, customer address (if provided), invoice number, issue date, due date (if any), line/service description(s), subtotal, tax rate(s), tax amount(s), total amount, payment status.
- **FR-008**: System MUST display the INR symbol consistently across invoice detail, list, and PDF.
- **FR-009**: System MUST provide an Inventory management module to create, list, search, update, and deactivate inventory or service catalog items.
- **FR-010**: System MUST provide a Customer management module to list, search, create, edit, deactivate customers (without deleting historical invoice associations).
- **FR-011**: System MUST provide a Settings module that permits updating configurable values (e.g., default GST rate, business name, address, logo).
- **FR-012**: System MUST apply updated default GST rate only to invoices created after the change (existing invoices unaffected).
- **FR-013**: System MUST normalize Indian mobile inputs by removing whitespace, dashes, and parentheses before validation.
- **FR-014**: System MUST validate that if address provided then address line is non-empty; city optional; empty address object rejected.
- **FR-015**: System MUST prevent saving a customer without at least one contact method (valid mobile OR email). Email optional if mobile present.
- **FR-016**: System MUST allow printing/downloading invoices in states active or cancelled; deny for soft-deleted/archived/hard-deleted.
- **FR-017**: System MUST log each invoice download event with timestamp and user identity for audit.
- **FR-018**: System MUST generate PDFs on-demand (no persistent storage); optional transient in-memory cache ≤5 minutes permitted.
- **FR-019**: System MUST warn if Inventory item referenced by invoice line becomes deactivated after invoice issued (non-blocking).
- **FR-020**: System MUST ensure User Interface modules (Inventory, Customers, Settings) are reachable via navigation and protected by authentication.
- **FR-021**: System MUST ensure currency handling uses two decimal places with proper rounding (HALF_UP).
- ~~**FR-022**: System MUST support exporting customer list (CSV) including phone normalization~~ (Removed – out of scope for this feature request.)
- **FR-023**: System MUST restrict Settings mutations to admin role; operators/readers lack write permission.
- **FR-024**: System MUST provide validation feedback inline (field-level messages) for mobile and address errors.
- **FR-025**: System MUST include invoice number and total in the PDF filename pattern: `invoice-<number>.pdf`.
- **FR-026**: System MUST surface a non-blocking duplicate warning when creating a customer whose normalized mobile matches an existing active customer; creation MUST still succeed.

### Key Entities

- **Customer**: Represents an individual or business receiving services. Attributes: name, normalized mobile, optional email, structured address (city), status (active/inactive). No hard database uniqueness constraint on mobile (duplicates allowed). Application issues non-blocking warning on create when normalized mobile matches an existing active customer. Relationships: multiple Invoices.
- **Invoice**: Commercial record with unique number, issue date, due date (optional), service/line descriptions, subtotals, tax rate, tax amount, total, currency (INR), links to Customer.
- **Inventory Item**: Catalog entry for a product/service with name, description, base price, active flag.
- **Settings**: Configuration aggregate including default GST rate, business name, business address, logo/branding artifacts, currency (fixed to INR in this scope).
- **Download Audit Event**: Log entry capturing invoice id, user id, timestamp, action (print/pdf).

### Non-Functional Requirements

- **NFR-001**: Validation error responses MUST be returned within 300ms at p95 under nominal load.
- **NFR-002**: Invoice PDF generation MUST complete within 2 seconds p95 for single invoice.
- **NFR-003**: System MUST ensure mobile normalization & validation logic achieves ≥99% accuracy against valid Indian number patterns (false positive <1%).
- **NFR-004**: UI forms MUST provide instantaneous (≤100ms) visual feedback when validation fails client-side.
- **NFR-005**: Printable layout MUST remain visually consistent across modern Chromium-based browsers and Firefox (differences limited to font rendering).
- **NFR-006**: Audit logging for downloads MUST not add more than 50ms overhead p95.
- **NFR-007**: Accessibility – Printable view and management modules MUST meet WCAG 2.1 AA (focus order, contrast, semantic headings).
- **NFR-008**: Observability – Download and PDF generation operations MUST emit structured metrics (count, duration histogram).
- **NFR-009**: Security – Settings module MUST require authenticated session and reject unauthenticated access with standard error.
- **NFR-010**: Internationalization – System MUST explicitly declare INR as fixed currency (no multi-currency switching in this scope).
- **NFR-011**: Audit – Invoice download audit entries MUST be retained for ≥12 months.

## Clarifications & Decisions

| ID  | Decision                                                                                                                                                                                  | Date       | Rationale                                                                                                                                                                                                                                            | Impact                                                                                                                                                    |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Customer mobile uniqueness: Option D – No hard DB uniqueness; allow duplicates; show non-blocking duplicate warning on create when normalized mobile matches an existing active customer. | 2025-09-25 | Operators may create provisional or partially known customer records rapidly without being blocked; real-world reuse of a shared phone (family / business front desk) is common. Enforces flexibility while still highlighting potential duplicates. | Added FR-026; adjusted Customer entity; database: do NOT add unique index on customer.mobile; requires application-level lookup (indexed) and warning UI. |

Assumptions Added:

1. Future customer merge / dedup workflow is OUT OF SCOPE for this feature (may be scheduled later).
2. Duplicate detection uses exact normalized mobile equality only (no fuzzy match) for p95 <300ms performance.
3. A B-Tree index on `customer.mobile` will be introduced at implementation time for efficient duplicate warning checks (non-functional detail, not a requirement line item).

## Review & Acceptance Checklist

### Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

### Constitutional Compliance

- [x] Performance benchmarks specified (p95 constraints defined)
- [x] Test coverage requirements included (inherit baseline 80% line / 90% critical path)
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
- [ ] Review checklist passed (pending clarifications)

---

SUCCESS: Specification finalized (assumptions accepted as confirmed by user). Ready for planning.

## Clarifications

### Session 1

Resolved Topic: Customer mobile uniqueness handling.

- Decision: Adopt Option D (no hard DB uniqueness; warn only) – captured as Decision C1 above.
- Rationale: Avoid blocking rapid entry; shared numbers common.
- Open Risks: Potential data clutter if operators over-create; mitigated later by future merge tool (out of scope).

No further high-impact ambiguities identified; proceeding to implementation planning.
