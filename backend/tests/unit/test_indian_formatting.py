from decimal import Decimal
from src.utils.indian_format import format_indian_number, format_inr


def test_indian_number_basic_groups():
    cases = [
        (0, '0'),
        (12, '12'),
        (123, '123'),
        (1234, '1,234'),
        (12345, '12,345'),
        (123456, '1,23,456'),
        (1234567, '12,34,567'),
        (12345678, '1,23,45,678'),
        (123456789, '12,34,56,789'),
    ]
    for value, expected in cases:
        assert format_indian_number(value) == expected


def test_indian_number_negative_and_fraction():
    assert format_indian_number(-1234567.89) == '-12,34,567.89'


def test_format_inr_rounding_half_up():
    # 2 decimal quantize half-up
    assert format_inr(1.005) == '₹1.01'
    assert format_inr(1.004) == '₹1.00'


def test_format_inr_large_values():
    assert format_inr(9876543210.5) == '₹9,87,65,43,210.50'


def test_format_inr_symbol_toggle():
    assert format_inr(1234.5, symbol=False) == '1,234.50'


def test_format_inr_decimal_input():
    assert format_inr(Decimal('1234.50')) == '₹1,234.50'


def test_format_inr_exact_two_decimals_no_extra():
    assert format_inr(100) == '₹100.00'


def test_format_inr_fraction_truncation():
    # Ensure extra precision truncated not rounded again after quantize
    assert format_inr(Decimal('1.239')) == '₹1.24'
