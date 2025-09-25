# Data Model: Customer & Invoice Localisation Feature

## Entities

### Customer

| Field             | Type                  | Constraints    | Notes                             |
| ----------------- | --------------------- | -------------- | --------------------------------- |
| id                | UUID                  | PK             | Generated                         |
| name              | text                  | required       | Display name                      |
| mobile_normalized | char(10)              | indexed        | Not unique; digits only 6-9 start |
| email             | text                  | optional       | Basic format validation           |
| address_line      | text                  | optional       | Max 255                           |
| city              | text                  | optional       |                                   |
| status            | enum(active,inactive) | default active |                                   |
| created_at        | timestamptz           | default now    |                                   |
| updated_at        | timestamptz           | auto update    |                                   |

Validation Rules:

- Mobile: strip +91/91, non-digits, then must be 10 digits starting 6-9.
- At least one of mobile or email present.

### InventoryItem

| Field       | Type          | Constraints  | Notes |
| ----------- | ------------- | ------------ | ----- |
| id          | UUID          | PK           |       |
| name        | text          | required     |       |
| description | text          | optional     |       |
| base_price  | numeric(12,2) | required     | INR   |
| active      | boolean       | default true |       |
| created_at  | timestamptz   | default now  |       |
| updated_at  | timestamptz   | auto update  |       |

### Invoice

| Field             | Type                   | Constraints       | Notes                           |
| ----------------- | ---------------------- | ----------------- | ------------------------------- |
| id                | UUID                   | PK                |                                 |
| number            | text                   | unique            | Existing numbering logic reused |
| customer_id       | UUID                   | FK -> Customer.id |                                 |
| issue_date        | date                   | required          |                                 |
| due_date          | date                   | optional          |                                 |
| currency          | char(3)                | fixed 'INR'       |                                 |
| subtotal          | numeric(14,2)          | required          |                                 |
| tax_rate          | numeric(5,2)           | required          | percent                         |
| tax_amount        | numeric(14,2)          | required          |                                 |
| total             | numeric(14,2)          | required          |                                 |
| branding_snapshot | jsonb                  | required          | {name,address,logo_ref}         |
| gst_rate_snapshot | numeric(5,2)           | required          | from settings at issue          |
| settings_snapshot | jsonb                  | optional          | extra future-proof              |
| created_at        | timestamptz            | default now       |                                 |
| updated_at        | timestamptz            | auto update       |                                 |
| deleted_at        | timestamptz            | soft delete       | nullable                        |
| status            | enum(active,cancelled) | default active    |                                 |

### InvoiceLine

| Field       | Type          | Constraints      | Notes                       |
| ----------- | ------------- | ---------------- | --------------------------- |
| id          | UUID          | PK               |                             |
| invoice_id  | UUID          | FK -> Invoice.id |                             |
| description | text          | required         | From inventory or ad-hoc    |
| quantity    | numeric(10,2) | required         | default 1                   |
| unit_price  | numeric(12,2) | required         | snapshot of item/base price |
| line_total  | numeric(14,2) | required         | quantity \* unit_price      |
| created_at  | timestamptz   | default now      |                             |

### Settings

| Field             | Type         | Constraints   | Notes          |
| ----------------- | ------------ | ------------- | -------------- |
| id                | singleton    | enforced      | Single row     |
| business_name     | text         | required      |                |
| business_address  | text         | required      | Combined       |
| gst_default_rate  | numeric(5,2) | required      |                |
| logo_ref          | text         | optional      | storage ref    |
| pdf_cache_enabled | boolean      | default false | feature toggle |
| created_at        | timestamptz  | default now   |                |
| updated_at        | timestamptz  | auto update   |                |

### InvoiceDownloadAudit

| Field      | Type            | Constraints      | Notes   |
| ---------- | --------------- | ---------------- | ------- |
| id         | UUID            | PK               |         |
| invoice_id | UUID            | FK -> Invoice.id | indexed |
| user_id    | UUID            | FK -> User.id    | indexed |
| action     | enum(print,pdf) | required         |         |
| created_at | timestamptz     | default now      |         |

## Relationships

- Customer 1—\* Invoice
- Invoice 1—\* InvoiceLine
- Settings 1—1 (singleton)
- Invoice 1—\* InvoiceDownloadAudit

## Indexes

- idx_customer_mobile (customer.mobile_normalized)
- idx_invoice_customer (invoice.customer_id)
- idx_audit_invoice (invoice_download_audit.invoice_id)
- idx_audit_user (invoice_download_audit.user_id)

## Derived / Business Rules

- Invoice total = subtotal + tax_amount, persisted for integrity.
- Subtotal computed as sum(line_total).
- Duplicate warning: SELECT 1 FROM customer WHERE mobile_normalized = :m AND status='active' LIMIT 1.

## State & Immutability

- Invoice snapshot fields prevent drift after settings changes.
- Cancelled invoices still downloadable; soft-deleted blocked (deleted_at present).

## Migration Notes

- New tables: customer (if not existing?), inventory_item, invoice_line, invoice_download_audit modifications if partial.
- Add columns to invoice for snapshots (if missing) otherwise create in initial migration for this feature.

## Open Questions (Deferred)

- Future: add pincode/state; email invoice delivery.
