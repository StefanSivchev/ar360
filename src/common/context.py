# Purpose of the file is to define a three things that every run needs to know
# A unique ID, the logical date, and the random seed

# This is done to ensure that when backfilling not to produce todays anaswers.

# The purpose of uuid is to generate a unique identifier for each run.
# This ensures that each run can be distinguished from others,
# even if they occur on the same logical date.

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from src.common.logging import bind_run


def new_run_id(logical_date: date) -> str:
    """Sortable, unique run ID for a given logical date."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{stamp}_{uuid.uuid4().hex[:4]}"


@dataclass(frozen=True)
class RunContext:
    """Everything a single run needs to know, including a unique ID,
    the logical date, and the random seed."""

    logical_date: date
    run_id: str = ""
    seed: int = 42
    dag_run_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def cutoff(self) -> date:
        """Last complete day of data as at the logical date: the day before it."""
        return self.logical_date - timedelta(days=1)


def build_context(
    logical_date: date | str, seed: int = 42, dag_run_id: str | None = None
) -> RunContext:
    """Build a RunContext and binds the IDs to the logger context.
    This is used to ensure that every log message has the same run ID and logical date."""
    if isinstance(logical_date, str):
        logical_date = date.fromisoformat(logical_date)

    ctx = RunContext(
        logical_date=logical_date, run_id=new_run_id(logical_date), seed=seed, dag_run_id=dag_run_id
    )
    bind_run(run_id=ctx.run_id, logical_date=ctx.logical_date.isoformat())
    return ctx
