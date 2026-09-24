# ADR-01: S3 landing zone rather than direct load

Status: accepted

Date: 2026-09-24

## Context

The extraction job runs once a day, but the warehouse it feeds is not always available when the extract itself succeeds. Because we must be able to replay five years of history without going back to the source system, the raw data has to survive independently of Snowflake's uptime and retention limits.

## Decision

Every extract is written first to a private, versioned S3 bucket as immutable, partitioned Parquet files. Snowflake then loads only from that landing zone, so extraction and loading are decoupled and no load ever depends on the source system being reachable again.

## Rejected

- **Loading directly from the extractor into Snowflake.** This couples extraction to warehouse availability. On a day Snowflake is down, the delta feeds (open items, cash application) recover on their own: the transactions are still in the source, and the next run's 7-day lookback re-reads them, provided the outage is shorter than the lookback. The snapshot feeds (customer master, disputes) lose that day for good, because the source only holds the current state and the next snapshot replaces it. A credit-grade change gets dated a day late, and a dispute that opened and closed inside the gap never appears at all.
- **Keeping history only in Snowflake RAW.** Time Travel is an undo window, not an archive: at most 90 days on Enterprise and 1 day on Standard. RAW would keep every row, but a bad reload or a dropped table older than that window could never be undone, and when the 30-day trial ends the account takes all of RAW with it. Open Parquet in S3 outlives both and is readable by any engine.

## Consequences

- Gain: replay becomes a matter of pointing the load at an older partition.
- Cost: a second copy of the data, roughly 35 MB, which at about $0.025 per GB-month comes to well under a tenth of a cent per month.
- Accept: one additional hop in the pipeline, and one more system to secure.

## Bucket configuration

- SSE-S3 rather than SSE-KMS (a deviation from the blueprint): KMS would add a $12/year key and an extra `kms:Decrypt` permission in the Day 12 handshake, for data with nothing real to protect. KMS remains the production answer.
- Versioning on, with noncurrent versions expiring after 30 days: this gives the delete-then-write writer an undo window while capping the storage cost of old versions.
- `force_destroy = true`: the data can always be regenerated from seed 42, so tearing down the bucket is safe here; production would use `false` plus `prevent_destroy`.
- Glacier IR at 90 days on `archive/`: this demonstrates the lifecycle pattern, but currently moves nothing because objects under 128 KB are skipped by default.
- Local Terraform state: acceptable for one person on a disposable environment, but on a team state belongs in a remote S3 backend with locking. Logged as a known limitation.
