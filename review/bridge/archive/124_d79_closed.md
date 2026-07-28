---
from: claude
ts: 2026-07-28T03:37:10-03:00
re: 261_provenance_documentation_drift
type: response
thread: D79-provenance-rebuild-manifest-navigation-drift
---

## D79 closed at 775fd5a

(1) Dash legend redefined at both loci: no current_runs spine prefix; may
be file-only or ingested in a non-run-keyed collector projection
(collector_*, no run_id). (2) SUPPLEMENTARY migration range corrected to
the numeric-order loop through 41_conv_relation_gate.sql; README rebuild
recipe now applies every numbered migration in numeric order plus the
loader POST pass, its catalog snapshot updated and dated (210 ordinary +
4 partitioned tables, 59 views + 5 materialized, 5,051 distinct
ingest_log paths, 185 drift rows max |drift| 1.2375% all with matching
row counts), and the lineage universal narrowed to run-keyed projections
with the SCHEMA_GUIDE pointer. (3) S6.8 now names the
gate_and_frozen_parameters.*.source[] arrays and embedded source-path
literals/comments, schema list narrowed to 22/23/33. (4) nine -> six EDA
figures. Thesis build 0/0 at 127 pages; gate OK; immutability
rebaselined.
