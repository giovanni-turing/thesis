---
from: reviewer
ts: 2026-07-28T03:30:42-03:00
re: new
type: finding
thread: D77-artifact-commit-lineage-refresh
---

## D77 — two current DB rows carry stale archival commit lineage

The schema defines `runs.artifact_commit_sha` as the latest commit archiving
the primary artifact, literally `git log -1 -- <source_path>`
(`provenance/schema/23_config_columns.sql:102-108`;
`provenance/loader/load_config_backfill.py:22-23`).

A read-only DB query returns:

```text
eda:i_burst_anatomy | current | analysis/trace_eda/i_burst_anatomy_stats.json
  stored artifact_commit_sha = 4e8553708a6bb1a9cb5f35feaa983625bab7afb7

eda:j_classes | current | analysis/trace_eda/j_classes_stats.json
  stored artifact_commit_sha = 4e8553708a6bb1a9cb5f35feaa983625bab7afb7
```

For both paths:

```text
git log -1 --format=%H -- <path>
67bd44a820785e184cd4ad2450e58ce0e30e72a9
```

The newer commit is substantive, not a formatting-only touch:

- `i_burst_anatomy_stats.json`: onset p50 6.0 -> 6.5, burst1 onset
  220 -> 404 minutes, burst6 1 -> 53 minutes, plus decay/ramp corrections.
- `j_classes_stats.json`: adds `nonsquare` (53 requests) and corrects class
  counts/shares and burst attribution.

`git diff 4e855370 67bd44a -- <both paths>` verifies those changes. The loaded
DB values and ingest content are current; this is a false lineage annotation,
not measurement drift. A repo-local census found exactly 2 mismatches among
1,040 distinct non-null artifact pins.

### Root cause

`provenance/loader/load_config_backfill.py:265-275` applies
`COALESCE(existing, staged)` to every column. That is correct for immutable
measured/config fields, but wrong for the recomputed archival lineage: once
`artifact_commit_sha` is non-null, a later artifact commit can never refresh
it. C413 at `provenance/schema/24_config_column_checks.sql:160-187` checks only
that `commit_sha` was not conflated with `artifact_commit_sha`; it does not
test Git freshness.

### Narrow closure

1. Special-case `artifact_commit_sha`: when the staged Git SHA is non-null,
   write it (or `COALESCE(staged, existing)`), while retaining fill-only
   semantics for measured/config fields and merging the matching
   `config_provenance` token.
2. Rerun K34 and verify these two rows advance to `67bd44a...`.
3. Add a filesystem/Git freshness gate for every tracked repo-local source
   with a non-null archival SHA; SQL alone cannot derive live Git history.
4. Add a negative self-test that seeds an older SHA, requires K34 to advance
   it, then requires the next pass to be idempotent.

No manuscript number changes.
