# Invoices API

Task: T039 — Documentation of core invoice endpoints after service layer refactor.

## Overview

Invoices represent billable work or services. Each invoice references a `Customer` and tracks subtotal, GST tax, total, paid and outstanding amounts, plus lifecycle/payment status.

The backend exposes flexible payload schemas that accept both legacy backend fields and current frontend shape. Unknown / extraneous fields are ignored (Pydantic model `extra='ignore'`). Numeric strings are coerced. Omitted `gst_rate` applies the default from settings (`DEFAULT_GST_RATE`, fallback 18.0%).

All responses are wrapped in a success envelope:

```
{
  "status": "success",
  "data": { ... },
  "meta": null | { ... },
  "timestamp": <unix-seconds>
}
```

Errors use standardized schema (see Error Codes section):

```
{
  "status": "error",
  "error": { "code": "INVOICE_NOT_FOUND", "message": "...", "details": {...}? },
  "timestamp": <unix-seconds>
}
```

## Authentication

All endpoints require a Bearer JWT (or FAST_TESTS synthetic header during test mode). Use `/api/v1/auth/login` to obtain a token.

## Endpoints

### List Invoices

GET `/api/v1/invoices/`

Returns up to 100 most recent (by `created_at`) non-deleted invoices.

Response `data`: Array of invoice objects (see Object Model) with `meta.total` count.

### Create Invoice

POST `/api/v1/invoices/`

Flexible request body — frontend style example:

```
{
  "customer_name": "Alice",
  "customer_phone": "9123456789",
  "service_type": "consulting",
  "service_description": "Monthly advisory retainer",
  "amount": 10000,
  "gst_rate": 18   // optional; if omitted default applied
}
```

Backend style (alternate) — supplying calculated fields (rarely needed):

```
{
  "customer_id": "<uuid>",
  "subtotal": 10000,
  "gst_rate": 18,
  "gst_amount": 1800,
  "total_amount": 11800
}
```

Behavior:

- If `customer_id` absent, attempts to find existing customer by (name, phone); otherwise creates one.
- If `gst_rate` is null or omitted, uses default rate.
- Computes tax math (gst_amount, total_amount) when not provided.
- Initializes `payment_status = PENDING`, `paid_amount = 0`.

Response: 201 Created, invoice object.

Error Cases:

- Missing `customer_name` / `customer_phone` / `amount` → `VALIDATION_ERROR` (422)
- Customer not found (backend style path) → `NOT_FOUND` (404)

### Retrieve Invoice

GET `/api/v1/invoices/{invoice_id}`

Response: 200 with invoice object (even if cancelled or soft deleted? — soft deleted invoices are still retrievable by id as per spec FR-018).

Error: `INVOICE_NOT_FOUND` (404)

### Update Invoice (Partial)

PATCH `/api/v1/invoices/{invoice_id}`

Body may include any of create fields plus:

```
{
  "paid_amount": 500,
  "status": "paid" | "draft" | "sent" | "cancelled",
  "payment_status": "PENDING" | "PARTIAL" | "PAID"
}
```

Rules:

- Adjusting `amount` or `gst_rate` recomputes tax math.
- `paid_amount` transition logic sets `payment_status` to PENDING / PARTIAL / PAID.
- Setting `status: "cancelled"` toggles `is_cancelled` but doesn't block payments (clarification tasks T024/T025 removed).
- Overpay (paid_amount > total_amount) raises `OVERPAY_NOT_ALLOWED` (400).

### Replace Invoice (PUT)

PUT `/api/v1/invoices/{invoice_id}`

Semantics mirror PATCH because fields are optional; acts as partial update for current client.

### Delete Invoice (Soft Delete)

DELETE `/api/v1/invoices/{invoice_id}`

Marks `is_deleted=true`. Multiple calls are idempotent (second returns success with no counter increment). Soft deleted invoices are excluded from list endpoint but accessible directly (FR-018).

Response: 204 style semantics but envelope returns `{ data: null }` with status success.

Error: `INVOICE_NOT_FOUND` (404)

### Download / Generate PDF

GET `/api/v1/invoices/{invoice_id}/pdf`

Returns `200 OK` with `Content-Type: application/pdf` and a minimal PDF body (current sprint stub). Side effects:

1. Records an audit row (`invoice_download_audit`) with action `pdf` (FR-017).
2. Increments `invoice_download_total` counter (if metrics configured).

Future (next sprint): Full HTML → PDF rendering via Playwright with Indian digit grouping applied using `format_inr` util and snapshot fields for branding and tax rate. Filename pattern (planned FR-025) `invoice-<invoice_number>-<total>.pdf` may be exposed via `Content-Disposition`.

Error Cases:

- Soft deleted invoice (future enforcement) → 403/404 per FR-016.
- Missing invoice → 404 (`INVOICE_NOT_FOUND`).

## Object Model (Response Shape)

Example invoice response object:

```
{
  "id": "uuid",
  "invoice_number": "INV20250924XXXX",
  "customer_id": "uuid",
  "customer_name": "Alice",
  "customer_phone": "9123456789",
  "customer_email": null,
  "service_type": "consulting",
  "service_description": "Monthly advisory retainer",
  "amount": 10000.0,
  "gst_rate": 18.0,
  "gst_amount": 1800.0,
  "total_amount": 11800.0,
  "status": "PENDING",          // mirrors payment_status currently
  "payment_status": "PENDING",
  "place_of_supply": "KA",
  "gst_treatment": "taxable",
  "reverse_charge": false,
  "outstanding_amount": 11800.0,
  "is_cancelled": false,
  "is_deleted": false,
  "created_at": "2025-09-24T12:00:00Z",
  "updated_at": "2025-09-24T12:00:00Z",
  "due_date": null
}
```

Notes:

- `service_description` is currently stored in `notes` column (planned dedicated column future migration).
- `outstanding_amount = total_amount - paid_amount` (computed model attribute).
- `invoice_number` format `INVYYYYMMDDNNNN` ensures daily uniqueness (tested in future T057).

## Error Codes

| Code                     | Meaning                                  |
| ------------------------ | ---------------------------------------- |
| VALIDATION_ERROR         | Input schema or required field violation |
| NOT_FOUND                | Generic resource not found               |
| INVOICE_NOT_FOUND        | Invoice id not found                     |
| OVERPAY_NOT_ALLOWED      | Paid amount exceeds total                |
| AUTH_INVALID_CREDENTIALS | Login failure                            |
| AUTH_TOKEN_EXPIRED       | JWT expired                              |
| DB_ERROR                 | Persistence layer exception              |
| INTERNAL_SERVER_ERROR    | Unhandled server failure                 |

## Metrics & Observability

Prometheus/OpenTelemetry counters emitted:

- `invoice_create_counter` (labels: place_of_supply)
- `invoice_update_counter` (labels: payment_status)
- `invoice_delete_counter` (no labels)
- `invoice_download_total` (action pdf/print in future; currently pdf only)
- `pdf_generate_total` & `pdf_generate_duration_ms` (histogram) — currently stub generation path trivial; instrumentation present for future full rendering
- Native deterministic: `invoice_operations_total` (labels: operation=create|update|delete)

Traces include spans for request lifecycle (middleware) and DB calls if OTEL enabled.

### Audit Logging

Each PDF download call writes a row to `invoice_download_audit` capturing `invoice_id`, optional `user_id`, action (`pdf`), and timestamp. This satisfies FR-017 and supports future compliance queries.

### Indian Currency Formatting

Server stores numeric fields as decimals; presentation formatting for PDF will use `format_inr` (see `src/utils/indian_format.py`) ensuring grouping pattern (e.g., `12,34,567.00`). API responses currently return raw numeric values; clients may apply symbol display (FR-003/FR-004). Snapshot fields (`branding_snapshot`, `gst_rate_snapshot`) ensure reproduced historical values after settings changes.

## Versioning & Stability

Current version: initial (v1). Backward-incompatible changes to payloads will require either new fields (additive) or versioned path in the future (`/api/v2/`).

## Testing References

Key tests exercising behaviors:

- Contract: creation `test_invoices_create.py`, list ordering, overpay rejection, payment transitions.
- Unit: GST math edges, payment status logic, service layer, error utilities.
- Integration: customer deduplication, invoice recompute, cancel flow.

## Changelog Highlights

- T026/T027: Soft delete introduced and list filtering.
- T023: Default GST rate config applied when omitted.
- T028/T032: Metrics counters & registration.
- T037/T038: Service layer extraction and dedicated unit tests.
