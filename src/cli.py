"""Command line entry point: ar360 generate --years 5 --seed 42 --out data/."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from src.common.context import build_context
from src.generate.calendar import YEARS_OF_HISTORY
from src.generate.dataset import source_feeds

app = typer.Typer(help="AR-360 pipeline commands.")
DEFAULT_OUT = Path("data")


@app.callback()
def main() -> None:
    """AR-360 pipeline commands."""


@app.command()
def generate(
    years: Annotated[int, typer.Option(help="Years of history.")] = YEARS_OF_HISTORY,
    seed: Annotated[int, typer.Option(help="Same seed and date give identical files.")] = 42,
    out: Annotated[Path, typer.Option(help="Output folder.")] = DEFAULT_OUT,
    logical_date: Annotated[str | None, typer.Option(help="YYYY-MM-DD; default today.")] = None,
) -> None:
    """Write the six source feeds as Parquet, plus the defect report."""

    ctx = build_context(logical_date or datetime.now(UTC).date().isoformat(), seed=seed)
    typer.echo(f"run {ctx.run_id}")
    feeds, report = source_feeds(ctx, years)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in feeds.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        typer.echo(f"{name:<18} {len(df):>9,} rows")
    (out / "_defects.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    typer.echo(json.dumps(report, indent=2))


if __name__ == "__main__":
    app()
