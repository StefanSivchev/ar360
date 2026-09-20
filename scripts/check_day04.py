"""Day 4 part 2 - cash application againts the frozen baseline"""

import numpy as np

from src.common.context import build_context
from src.generate.calendar import date_spine
from src.generate.customers import customers
from src.generate.disputes import dispute_flags, disputes, settlement_lateness
from src.generate.invoices import invoices
from src.generate.payments import cash_application

ctx = build_context("2026-09-11", seed=42)
cust = customers(ctx)
dates = date_spine(ctx)
inv = invoices(ctx, cust, dates)
rows = cash_application(ctx, inv, cust)


BASELINE = {
    "rows": 802173,
    "invoices": 580100,
    "applied_total": 587378323.99,
    "parts_1": 432026,
    "parts_2": 74075,
    "parts_3": 73999,
    "payments": 740942,
    "multi_invoice": 55145,
    "rows_in_multi": 113322,
    "largest_remittance": 5,
    "disputed_share_of_open": 0.0728,
    "disputes": 17753,
    "disp_total": 12427536.06,
    "disp_open_share": 0.0635,
    "disp_min_amt": 4.59,
    "raised_after_invoice": True,
    "resolved_after_raised": True,
}

parts_per_invoice = rows.groupby("invoice_id").size()
part_counts = parts_per_invoice.value_counts()
per_payment = rows.groupby("payment_id").invoice_id.nunique()
multi = per_payment[per_payment > 1]

d_rng = np.random.default_rng(ctx.seed + 3)
lateness = settlement_lateness(inv, rows)
disputed = dispute_flags(inv, lateness, d_rng)
d = disputes(ctx, inv, rows)


actual = {
    "rows": len(rows),
    "invoices": rows.invoice_id.nunique(),
    "applied_total": round(rows.applied_amount.sum(), 2),
    "parts_1": int(part_counts.get(1, 0)),
    "parts_2": int(part_counts.get(2, 0)),
    "parts_3": int(part_counts.get(3, 0)),
    "payments": len(per_payment),
    "multi_invoice": len(multi),
    "rows_in_multi": int(multi.sum()),
    "largest_remittance": int(per_payment.max()),
    "disputed_share_of_open": round(float(disputed[lateness.isna()].mean()), 4),
    "disputes": len(d),
    "disp_total": round(d.disp_amt.sum(), 2),
    "disp_open_share": round(float(d.resolved_date.isna().mean()), 4),
    "disp_min_amt": round(float(d.disp_amt.min()), 2),
    "raised_after_invoice": bool(
        (
            d.raised_date >= inv.set_index("invoice_id").loc[d.invoice_id].invoice_date.to_numpy()
        ).all()
    ),
    "resolved_after_raised": bool(
        (d.resolved_date.dropna() > d.raised_date[d.resolved_date.notna()]).all()
    ),
}

for name, expected in BASELINE.items():
    got = actual[name]
    if got == expected:
        print(f"{name: <15} match {got:>15,}")
    else:
        print(f"{name:<15} MISMATCH expected {expected:>15,} got {got:>15,}")
