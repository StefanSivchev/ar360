# AR-360

Order to Cash ELT pipeline.

Six sources feeds are send in S3 as Parquet, loaded into Snowflake and are modelled as a Kimball star serving DSO ( Days Sells Outstanding ), ageing and collection metrics. Orchestrated by Airflow.

## Stack

Python 3.13, AWS S3, Snowflake, Apache Airflow, Terraform, GitHub

## Quickstart

```powershell
uv sync --extra dev
```


**Status:** Phase 1 of 6 completed - Synthetic source data (v0.1.0)

## Data

One command generates five years of order-to-cash data for six source feeds.
Same seed and logical date give byte-identical files.

```
ar360 generate --years 5 --seed 42 --logical-date 2026-09-11 --out data/
```

| Feed | Pattern | Grain | Rows |
|---|---|---|---|
| sap_ar_open_items | delta | invoice | 603,076 |
| cash_application | delta | payment × invoice | 803,115 |
| customer_master | snapshot | customer | 2,994 |
| credit_disputes | snapshot | dispute | 17,753 |
| dunning_log | append | contact | 896,714 |
| fx_rates | append | currency × weekday | 2,608 |

Payment behaviour sits on the customer, so days late differ by segment
(median / p90): key accounts −2 / 4, wholesale 6 / 18, convenience 9 / 25,
HoReCa 14 / 34.

At the cut-off, 19,976 invoices (3.3%) are open, about €22.2m, 13% of it
over 90 days. Classic DSO on the last 90 days' sales is 53.6 days; on the
average day's sales it would be about 61. That gap is the summer peak, and
it is why Week 6 also builds countback DSO.

### Defects injected on purpose

| Defect | Feed | Injected | Caught later by |
|---|---|---|---|
| Duplicates | invoices, cash | 3,000 / 3,996 (0.5%) | staging dedupe, post-load key check |
| Late arrival | cash | 23,974 (3%), posted 1–5 days late | 7-day extract lookback |
| Type drift | invoices | 6,001 (1%) in Greek format `1.234,50` | staging parser |
| Orphan FK | customer master | 6 customers withheld: 1,205 invoice and 1,551 cash rows | unknown member (−1), orphan check |
| Negative lines | invoices | 24,231 credit notes (4.04%) | signed control totals |
| Schema drift | invoices | `sales_org` from March 2024 (308,107 rows) | additive RAW, schema warning |

Every count is exact and frozen in `tests/test_defects.py`; each run writes
them to `data/_defects.json`.
