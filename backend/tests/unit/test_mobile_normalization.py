import pytest
from backend.src.models.database import Customer

# Unit test skeleton (T037) covering edge mobile normalization logic.


@pytest.mark.parametrize('raw,expected', [
    ('+91 9876543210', '9876543210'),
    ('98765 43210', '9876543210'),
    ('919876543210', '9876543210'),
    ('+91-98765-43210', '9876543210'),
])
def test_mobile_normalization(raw, expected):
    c = Customer(name='X', phone=raw)
    # Accessing phone triggers validation; mobile_normalized set
    assert c.mobile_normalized == expected


@pytest.mark.parametrize('raw', [
    '+91 1234567890',  # starts with 1 invalid
    '1234567890',      # starts with 1 invalid
    '5555555555',      # starts with 5 invalid
])
def test_mobile_invalid(raw):
    with pytest.raises(ValueError):
        Customer(name='X', phone=raw)
