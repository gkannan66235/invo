# Customers API

Task: T038 — Documentation for customer management endpoints and duplicate warning semantics.

## Overview

Customers represent recipients of invoices. Each customer stores a normalized Indian mobile number (digits only, 10 digits starting 6–9) and optional email plus lightweight address information (single address line & city in this phase). Duplicate mobiles are allowed; a non-blocking `duplicate_warning` flag is surfaced on creation & retrieval when another active customer shares the same normalized mobile (FR-026).

## Authentication

All endpoints require Bearer auth. Missing `Authorization` header returns standardized 401 envelope:

```
{
  "status": "error",
  "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}
}
```

## Normalization & Validation

- Accepts inputs with spaces, dashes, parentheses, +91 / 91 prefix; these are stripped to a canonical 10-digit number.
- Rejects numbers not 10 digits after normalization or not starting 6–9 (FR-001, FR-013).
- At least one contact method (mobile OR email) must be present (FR-015).

## Endpoints

### List Customers

GET `/api/v1/customers`

Query Params:

- `search` (optional) substring on name
- `customer_type` (optional) filter by type (if provided)

Response (success):

```
{
  "status": "success",
  "data": {
    "customers": [ {<customer-object>}, ... ],
    "pagination": { "page": 1, "page_size": N, ... }
  }
}
```

### Create Customer

POST `/api/v1/customers`

Body (example):

```
{
  "name": "Ravi Kumar",
  "mobile": "+91 98765 43210",
  "email": "ravi@example.com",
  "address_line": "12 MG Road",
  "city": "Bengaluru"
}
```

Behavior:

- Normalizes mobile; returns `duplicate_warning=true` if another active customer shares normalized mobile.
- Does NOT block on duplicate.

Response:

```
{
  "status": "success",
  "data": { "customer": { <customer-object-with-duplicate_warning> } }
}
```

Validation Errors (422):

- Missing `name`
- Invalid or absent mobile/email combination
- Invalid mobile format

### Retrieve Customer

GET `/api/v1/customers/{id}`

Returns serialized customer plus recomputed duplicate flag each fetch (ensures stale flags not served after updates by other customers).

### Update Customer

PATCH `/api/v1/customers/{id}`

- Allows updating name, mobile, email, address fields, status.
- If mobile updated to collide with another active customer's normalized mobile, both customers will subsequently surface `duplicate_warning=true`.

### Customer Object Shape

```
{
  "id": "uuid",
  "name": "Ravi Kumar",
  "mobile": "9876543210",
  "email": "ravi@example.com",
  "address_line": "12 MG Road",
  "city": "Bengaluru",
  "status": "active",
  "duplicate_warning": false,
  "created_at": "2025-09-26T09:40:12Z",
  "updated_at": "2025-09-26T09:40:12Z"
}
```

## Duplicate Warning Logic

Query performed (conceptual):

```
SELECT id FROM customer
WHERE mobile_normalized = :mobile AND status='active'
LIMIT 2;
```

If ≥2 rows (including current), set `duplicate_warning=true`.

## Metrics

- `customer_duplicate_warning_total`: incremented when a create operation detects a duplicate.

## Testing References

- Contract: `test_customers_contract.py`
- Integration: `test_customer_duplicate_warning.py`
- Unit: `test_customer_duplicate_warning_flow.py`

## Future Enhancements (Deferred)

- Full address schema (state, postal code)
- Customer merge/dedup workflow
- Export (CSV) capability
