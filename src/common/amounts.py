"""Parse source amounts to exact Decimals."""

import math
import re
from decimal import Decimal

# The only three formats in 603,076 source values (Day 7 profiling).
_DOT = re.compile(r"-?\d+(\.\d{1,2})?")  # 1277.59
_EU = re.compile(r"-?\d{1,3}(\.\d{3})+,\d{2}")  # 1.329,40
_COMMA = re.compile(r"-?\d+,\d{2}")  # 654,18


def parse_amount(value: str | float) -> Decimal:
    """Return the amount as an exact Decimal, sign kept.

    Raises ValueError on a missing amount, a float off whole
    cents, or a text format not seen in the source.
    """
    if isinstance(value, float):
        if math.isnan(value):
            msg = "missing amount"
            raise ValueError(msg)
        if round(value, 2) != value:
            msg = f"amount not in whole cents: {value!r}"
            raise ValueError(msg)
        return Decimal(str(value))
    if _DOT.fullmatch(value):
        return Decimal(value)
    if _EU.fullmatch(value) or _COMMA.fullmatch(value):
        # thousands dots out first, then comma to decimal point
        return Decimal(value.replace(".", "").replace(",", "."))
    msg = f"unrecognised amount format: {value!r}"
    raise ValueError(msg)
