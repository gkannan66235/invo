"""Indian number formatting utilities.

Implements Indian digit grouping (3,2,2 pattern from right after the first group of 3) and
helpers for currency (INR) display. This supports FR-003/FR-004 and T036.

Rules:
- Preserve sign
- Always format with two decimal places for currency helper
- Pure string manipulation (avoid locale dependence)
- Handles large values (crores) and fractional parts

Examples:
>>> format_indian_number(123)
'123'
>>> format_indian_number(1234)
'1,234'
>>> format_indian_number(12345)
'12,345'
>>> format_indian_number(123456)
'1,23,456'
>>> format_indian_number(1234567)
'12,34,567'
>>> format_inr(1234567.5)
'₹12,34,567.50'
"""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Number = Union[int, float, Decimal]

__all__ = ["format_indian_number", "format_inr"]


def _split_number_str(num_str: str) -> tuple[str, str]:
    if '.' in num_str:
        left, right = num_str.split('.', 1)
    else:
        left, right = num_str, ''
    return left, right


def format_indian_number(value: Number) -> str:
    """Format a number using Indian digit grouping.

    Does not add decimals; use :func:`format_inr` for currency.
    """
    # Normalize to string integer/fraction
    if isinstance(value, Decimal):
        num_str = format(value, 'f')
    else:
        num_str = ('{0}'.format(value))
    sign = ''
    if num_str.startswith('-'):
        sign, num_str = '-', num_str[1:]
    left, right = _split_number_str(num_str)
    if len(left) <= 3:
        grouped = left
    else:
        # Last 3 digits stay together; preceding part grouped in 2s
        head = left[:-3]
        tail = left[-3:]
        head_groups: list[str] = []
        while len(head) > 2:
            head_groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            head_groups.insert(0, head)
        grouped = ','.join(head_groups + [tail])
    return sign + (grouped + ('.' + right if right else ''))


def format_inr(value: Number, symbol: bool = True) -> str:
    """Format a number as INR currency with Indian digit grouping and two decimals.

    Rounds HALF_UP at 2 decimal places.
    """
    dec = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    base = format_indian_number(dec)
    if '.' not in base:
        base = base + '.00'
    else:
        # Ensure exactly 2 decimals (Decimal quantize guarantees but safe to enforce)
        whole, frac = base.split('.')
        frac = (frac + '00')[:2]
        base = whole + '.' + frac
    return ('₹' + base) if symbol else base
