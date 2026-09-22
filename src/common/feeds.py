# Purpose of the file is to declare the six source feeds in code: load pattern, business key and control column.
# This is done before any extraction logic to be built.

# There are going to be 3 fields / patterns however one may want to call them.
# 1. Delta - Rows changed since the last extract, selected by a date window.
# 2. Snapshot - Full current state of the source.
# 3. Append - New events only.


from dataclasses import dataclass
from typing import Literal

# The Literal type is used to restrict the values of the LoadPattern to a specific set of strings, eg the ones defined.
LoadPattern = Literal["delta", "snapshot", "append"]


# The FEED dataclass.
@dataclass(frozen=True)
class Feed:
    """One source feed and its communication/interaction with the rest of the pipeline."""

    name: str
    load_pattern: LoadPattern
    business_key: tuple[
        str, ...
    ]  # Tuplet is used rather than a list to ensure immutability and hashability, which is important for using it as a key in dictionaries or sets.
    control_column: str | None = None
    description: str = ""


# The registery is below. Acting as a Source Registry. Each feed is defined with its name, load pattern, business key, control column, and description.
FEEDS: tuple[Feed, ...] = (
    Feed(
        name="sap_ar_open_items",
        load_pattern="delta",
        business_key=("invoice_id",),
        control_column="gross_amount",
        description="Open AR items from SAP. One row per invoice.",
    ),
    Feed(
        name="cash_application",
        load_pattern="delta",
        business_key=("payment_id", "invoice_id"),
        control_column="applied_amount",
        description="Payment to invoice matches. Support partial settlement.",
    ),
    Feed(
        name="customer_master",
        load_pattern="snapshot",
        business_key=("customer_id",),
        control_column=None,
        description="Full customer master data and state each run. Input to SCD2",
    ),
    Feed(
        name="credit_disputes",
        load_pattern="snapshot",
        business_key=("dispute_id",),
        control_column="disputed_amount",
        description="Open disputes and credit limits",
    ),
    Feed(
        name="dunning_log",
        load_pattern="append",
        business_key=("contact_id",),
        control_column=None,
        description="Dunning contacts and promises to pay",
    ),
    Feed(
        name="fx_rates",
        load_pattern="append",
        business_key=("currency", "rate_date"),
        control_column=None,
        description="ECB daily rates",
    ),
)

# The comparison / lookup of the feed.
FEEDS_BY_NAME: dict[str, Feed] = {f.name: f for f in FEEDS}


def get_feed(name: str) -> Feed:
    """Look up a feed by name. Raises KeyError if not found."""
    try:
        return FEEDS_BY_NAME[name]
    except KeyError:
        known = ", ".join(sorted(FEEDS_BY_NAME))
        raise KeyError(f"unknown feed {name!r}; known feeds: {known}") from None


def feeds_by_pattern(pattern: LoadPattern) -> tuple[Feed, ...]:
    """All feeds using a given load pattern"""
    return tuple(f for f in FEEDS if f.load_pattern == pattern)
