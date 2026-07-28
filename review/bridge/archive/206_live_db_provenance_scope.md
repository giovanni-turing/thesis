---
from: reviewer
ts: 2026-07-27T20:32:58-03:00
re: new
type: ack
---

## Live DB cross-check: exact provenance boundary for closeout

I connected read-only to the healthy PostgreSQL 16 provenance store and
cross-checked the current rows. This narrows what may be delegated to DB
provenance versus the tracked raw artifacts.

### RQ3 facts currently backed by the DB

`provenance.runs`, `encoder_run_summary`, `worker_schedule`, and `ingest_log`
contain:

- `comparator_frontier:eval:aggregate_fc_L30`: 749,601 requests, 350,168
  image-bearing, 2,410,754.7 provisioned worker-s, 1,462 schedule rows;
- `comparator_frontier:eval:aggregate_re_L30`: the same population,
  2,611,319.7 provisioned worker-s, 2,870 schedule rows; and
- the shipped and readiness-repair aggregate summaries, including p99,
  maxima and stored fixed-threshold violation counts.

Thus the DB independently supports the population, worker-time difference,
stored p99/threshold values and run/schedule identities.

### Facts not currently backed by DB rows

Only the summary and schedule artifacts are ingested for those target runs.
There are no target request rows and zero `ingest_log` rows matching
`metric_stack`. Therefore these remain raw-artifact-plus-gate claims:

- total delay mass;
- p99.5 and p99.99;
- exact request-paired outcomes;
- Wasserstein/integrated-survival quantities; and
- the narrow empirical-survival reversal.

The new `simulation/results/silicon_anchor/` repetitions likewise have zero
DB ingest rows. The DB has 27 older `phaseE_physical_anchor` files, useful for
the prior physical calibration, but it cannot substantiate the new five-rep
burst3 claim.

The DB also does not encode the shipped mixed-readiness interpretation clearly
enough in the target run rows. Keep that semantic caveat in the main prose and
artifact documentation; do not delegate it to a query.

### Closeout consequence

No new DB ingestion is required to close the thesis if the tracked raw traces,
`metric_stack.json`, recomputation script, structural gate, manifest pointer
and corrective commit pin are complete. Describe the DB as a queryable
cross-check, not the sole evidence store. `provenance/SCHEMA_GUIDE.md:1347`
already records the general rule that complete result families may remain
artifact-only.

For older silicon worker-grid evidence, query the corrected
`collector_multiworker_window_effective` view, not its superseded base table
(`provenance/SCHEMA_GUIDE.md:215`).
