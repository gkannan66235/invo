# Quickstart: Validate Customer & Invoice Localisation Feature

## Pre-requisites

- Backend running (FastAPI dev server) with applied migrations
- Frontend running (Next.js dev)
- Test database seeded with default settings row

## Scenarios

### 1. Invalid Indian Mobile Rejected

1. POST /api/v1/customers with mobile=12345 → expect 422 validation error
2. POST with mobile=+91 98765 43210, name=Test → expect 201, normalized mobile=9876543210

### 2. Duplicate Mobile Warning

1. Create customer A (mobile 9876543210)
2. Create customer B (mobile +91-9876543210)
3. Response duplicate_warning=true

### 3. Invoice Creation INR Formatting

1. Create customer
2. POST /api/v1/invoices with lines → expect currency=INR and totals

### 4. Printable & PDF

1. GET /api/v1/invoices/{id}/pdf → 200 application/pdf; audit row created

### 5. Settings Update Applied Prospectively

1. PATCH /api/v1/settings gst_default_rate=20.00
2. Create new invoice – tax_rate snapshot=20.00 while earlier invoice remains old rate

### 6. Cancelled vs Soft-Deleted Access

1. Cancel invoice (PATCH status=cancelled) → PDF still accessible
2. Soft delete (future endpoint or direct DB for test) → PDF returns 403/404

## Smoke Commands (Illustrative)

- Customer create → Invoice create → PDF download

## Success Criteria

- All scenarios pass with specified status codes & fields
- Performance budgets respected in performance test suite
