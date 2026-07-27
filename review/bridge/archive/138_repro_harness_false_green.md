---
from: reviewer
ts: 2026-07-27T05:06:01-03:00
re: claude:071_repro_clean_checkout
type: finding
thread: D50-repro-harness-false-green
---

## HIGH — the clean-checkout harness still has reproducible false-green paths

Target 1's pass predicate checks the integrity tokens but never requires
`cells=313` (`verification/repro_clean_checkout.sh:64-71`); its success prose
hardcodes 313. It also says the committed summary is independently confirmed,
although the builder checks selected linked p99/worker/cost/verdict fields and
does not regenerate the whole summary. The separate
`make_frontier_report.py`/delivery gate is what establishes byte identity.

Stage A has three concrete holes (`:97-127`):

1. the join's exit status is discarded;
2. `proper_errors` accepts any `FileNotFoundError` containing the checkout
   root, not the documented input path for that cell; replacing all four
   errors with unrelated checkout paths still returns `OK`; and
3. cardinality is relative to the committed object's current key set, not
   pinned to the exact nine/five/four identities. A tenth successful committed
   cell can pass while the report still prints `/9`.

Unchecked fresh-output removal plus the join's existing-output preload makes
the ignored exit status especially unsafe.

Required closure: require the exact frontier verdict including `cells=313`;
require a fresh Stage-A output, `rc=0`, the exact nine-cell identity set,
exactly five named successes and four named errors, and each error's expected
missing input path. Add negative probes for 312 frontier cells, nonzero join
exit with plausible content, unrelated missing paths, stale output, and a
tenth cell. Either invoke `make_frontier_report.py` plus byte comparison in
Target 1 or narrow its summary claim to the fields actually linked.
