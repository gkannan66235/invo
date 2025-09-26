# Response Modes (Transitional)

The backend currently supports **two response modes** to satisfy overlapping legacy and new-feature contract test expectations.

## 1. Enveloped Mode (Default)

All production / authenticated requests and most contract tests receive the standard envelope:

```
{
  "status": "success",
  "data": { ... },
  "meta": null,
  "timestamp": 1730000000.123
}
```

Errors follow:

```
{
  "status": "error",
  "error": { "code": "UNAUTHORIZED", "message": "Authentication required" }
}
```

Helpers live in `src/utils/api_shapes.py` (`success`, `error_envelope`).

## 2. Raw Mode (Transitional / Test-Only)

Activated explicitly by sending header:

```
X-Raw-Mode: 1
```

Used only by early _new_feature_ skeleton tests which expect:

- No envelope (list or object returned directly)
- Some monetary / numeric fields string-formatted elsewhere (e.g. invoices)

Raw mode is intentionally isolated and will be **removed** once all tests are migrated to envelopes.

## Detection Logic

Centralized in `api_shapes.is_raw_mode(request)`: only checks `X-Raw-Mode` header. Previous implicit Authorization-token heuristic has been retired to avoid accidental activation.

## Migration / Decommission Plan

1. Update remaining skeleton tests to assert enveloped responses.
2. Remove `X-Raw-Mode` usage in fixtures (`app_client`).
3. Delete raw-mode branches in `invoices.py` and `customers.py`.
4. Remove helper `is_raw_mode` and this document section.

## Rationale

This approach allowed parallel development of richer contract schemas (pagination, snapshots, audit fields) while not breaking early iteration tests that validated core flows. Encapsulating logic + explicit header keeps surface area small and auditable.

## Related Files

- `src/utils/api_shapes.py`
- `src/routers/invoices.py`
- `src/routers/customers.py`
- `backend/tests/conftest.py` (adds header in `app_client` fixture)

## Future Improvements

- Introduce global exception handler returning `error_envelope` consistently.
- Add pagination metadata utility (avoid duplicating structure).
- Remove transitional raw mode after consolidation.
