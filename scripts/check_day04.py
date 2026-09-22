"""Day 4 - payments, disputes and dunning against the frozen baseline"""

import numpy as np
import pandas as pd

from src.common.context import build_context
from src.generate.calendar import date_spine
from src.generate.customers import customers
from src.generate.disputes import dispute_flags, disputes, settlement_lateness
from src.generate.dunning import dunning
from src.generate.invoices import invoices
from src.generate.payments import cash_application

ctx = build_context("2026-09-11", seed=42)
cust = customers(ctx)
dates = date_spine(ctx)
inv = invoices(ctx, cust, dates)
rows = cash_application(ctx, inv, cust)


BASELINE = {
    "rows": 799119,
    "invoices": 580100,
    "applied_total": 587378323.99,
    "parts_1": 433952,
    "parts_2": 73277,
    "parts_3": 72871,
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
    "part_paid": 0,
    "contacts": 896714,
    "dunned_invoices": 370275,
    "first_is_reminder": True,
    "promises": 178491,
    "promises_kept": 109632,
    "promise_lead_days": 1746566,
    "promise_after_contact": True,
    "open_invoices": 19976,
    "open_share": 0.0333,
    "open_total": 22199975.82,
    "over90_share": 0.1296,
    "dso_classic": 53.6,
}

parts_per_invoice = rows.groupby("invoice_id").size()
part_counts = parts_per_invoice.value_counts()
per_payment = rows.groupby("payment_id").invoice_id.nunique()
multi = per_payment[per_payment > 1]

d_rng = np.random.default_rng(ctx.seed + 3)
lateness = settlement_lateness(inv, rows)
disputed = dispute_flags(inv, lateness, d_rng)
d = disputes(ctx, inv, rows)
dl = dunning(ctx, inv, rows, cust)
pr = dl[dl.promised_date.notna()]
settled = rows.groupby("invoice_id").payment_date.max()
applied = rows.groupby("invoice_id").applied_amount.sum()
gross = inv.set_index("invoice_id").gross_amount.loc[applied.index]
first_level = dl.sort_values("contact_date").groupby("invoice_id").contact_level.first()

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
    "part_paid": int(((applied - gross).abs() > 0.005).sum()),
    "contacts": len(dl),
    "dunned_invoices": dl.invoice_id.nunique(),
    "first_is_reminder": bool((first_level == "REMINDER").all()),
    "promises": len(pr),
    "promises_kept": int((pr.invoice_id.map(settled) <= pr.promised_date).sum()),
    "promise_lead_days": int((pr.promised_date - pr.contact_date).dt.days.sum()),
    "promise_after_contact": bool((pr.promised_date >= pr.contact_date).all()),
}

# --- open book at cutoff: evidence for Deviation #10 ---
cutoff = pd.Timestamp(ctx.cutoff)
applied = rows.groupby("invoice_id")["applied_amount"].sum()
book = inv.set_index("invoice_id")
open_amt = (book["gross_amount"] - applied.reindex(book.index, fill_value=0)).round(2)
is_open = open_amt != 0

overdue_days = (cutoff - book["due_date"]).dt.days
last_90 = book["invoice_date"] > cutoff - pd.DateOffset(days=90)
open_total = open_amt[is_open].sum()
over90_total = open_amt[is_open & (overdue_days > 90)].sum()
sales_90 = book.loc[last_90, "gross_amount"].sum()

actual.update(
    {
        "open_invoices": int(is_open.sum()),
        "open_share": round(float(is_open.mean()), 4),
        "open_total": round(float(open_total), 2),
        "over90_share": round(float(over90_total / open_total), 4),
        "dso_classic": round(float(open_total / sales_90 * 90), 1),
    }
)


for name, expected in BASELINE.items():
    got = actual[name]
    if got == expected:
        print(f"{name: <15} match {got:>15,}")
    else:
        print(f"{name:<15} MISMATCH expected {expected:>15,} got {got:>15,}")
