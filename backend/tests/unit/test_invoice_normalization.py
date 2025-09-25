import pytest
from datetime import datetime

from src.routers.invoices import InvoiceCreate, InvoiceUpdate  # type: ignore

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_invoice_create_normalization_camelcase_and_numeric_strings():
    """T050: Normalize camelCase + numeric strings (FR-013/FR-014/FR-020).

    Verifies InvoiceCreate model validator:
      - Maps camelCase to snake_case (customerName -> customer_name, serviceDescription -> service_description)
      - Coerces numeric strings to floats (amount, gstRate, discount_amount)
      - Empty string numeric fields -> None (gst_rate when sent as "") handled upstream (here we send a real value)
      - Empty string date -> None (due_date)
      - Unknown extra fields ignored (extraField)
    """
    payload = {
        "customerName": "CamelUser",
        "customerPhone": "9123401234",
        "serviceDescription": "Camel Desc",
        "amount": "150.50",
        "gstRate": "18",
        "discount_amount": "5",  # numeric string
        "due_date": "",  # becomes None
        "extraField": "ignored",  # should be dropped (extra='ignore')
    }
    model = InvoiceCreate(**payload)

    assert model.customer_name == "CamelUser"
    assert model.customer_phone == "9123401234"
    assert model.service_description == "Camel Desc"
    assert isinstance(model.amount, float) and model.amount == 150.50
    assert isinstance(model.gst_rate, float) and model.gst_rate == 18.0
    assert model.discount_amount == 5.0
    assert model.due_date is None
    dumped = model.model_dump()
    assert "extraField" not in dumped


@pytest.mark.asyncio
async def test_invoice_update_normalization_camelcase_paid_amount_and_dates():
    """T050: Normalize InvoiceUpdate camelCase + numeric strings + empty string fields.

    Checks:
      - camelCase mapping (customerName, customerPhone, serviceDescription, gstRate, paidAmount, dueDate)
      - numeric coercion (amount, gst_rate, paid_amount)
      - empty string status -> None
      - ISO date parsing for dueDate
      - unknown field ignored
    """
    iso_dt = "2025-09-30T10:15:00"
    payload = {
        "customerName": "CamelUser2",
        "customerPhone": "9123401235",
        "serviceDescription": "Updated Desc",
        "amount": "200",
        "gstRate": "5",
        "paidAmount": "50",
        "status": "",  # becomes None
        "dueDate": iso_dt,
        "someUnknown": "value",  # ignored
    }
    model = InvoiceUpdate(**payload)

    assert model.customer_name == "CamelUser2"
    assert model.customer_phone == "9123401235"
    assert model.service_description == "Updated Desc"
    assert model.amount == 200.0
    assert model.gst_rate == 5.0
    assert model.paid_amount == 50.0
    assert model.status is None
    assert isinstance(
        model.due_date, datetime) and model.due_date.isoformat().startswith(iso_dt)
    dumped = model.model_dump()
    assert "someUnknown" not in dumped
