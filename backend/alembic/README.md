# Alembic Migrations

This directory contains the Alembic migration environment for the BillingBee backend.

## Usage

Generate a new revision (autogenerate):

```
cd backend
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```
alembic upgrade head
```

Downgrade (previous revision):

```
alembic downgrade -1
```

Show current heads:

```
alembic heads
```

## Notes

- `env.py` dynamically imports SQLAlchemy models from `src.models.database`.
- Database URL is sourced from existing configuration (`DatabaseConfig`).
- Use migrations instead of runtime ALTER TABLE logic going forward.
