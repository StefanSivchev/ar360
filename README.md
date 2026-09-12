# AR-360

Order to Cash ELT pipeline.

Six sources feeds are send in S3 as Parquet, loaded into Snowflake and are modelled as a Kimball star serving DSO ( Days Sells Outstanding ), ageing and collection metrics. Orchestrated by Airflow.

## Stack

Python 3.13, AWS S3, Snowflake, Apache Airflow, Terraform, GitHub

## Quickstart

```powershell
uv sync --extra dev
```
