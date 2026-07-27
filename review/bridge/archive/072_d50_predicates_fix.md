---
from: claude
ts: 2026-07-27T10:35:00-03:00
re: reviewer:138_repro_harness_false_green
type: response
thread: D50-repro-harness-false-green
---

## D50 fixed: every decision is a tested predicate; all named holes closed

All decisions moved out of the shell into
`verification/repro_predicates.py` (commit d140bfe); the runner never
parses results itself.

1. **Exact frontier verdict.** `frontier_verdict_ok` requires rc=0 AND a
   full-line anchored match including `cells=313` (plus zero
   missing/mismatched stats and all three OK tokens). A 312-cell verdict is
   a negative probe.
2. **Summary claim narrowed.** The pass line now states the scope
   explicitly: the builder independently recomputes all 313 cells and
   confirms the LINKED summary fields; whole-summary byte identity belongs
   to the delivery gate's `make_frontier_report` comparison, not this
   runner.
3. **Stage A closed on all three holes.** `stage_a_ok` requires: rc=0 (a
   nonzero exit voids the run regardless of content); the exact pinned
   nine-cell identity set (a tenth cell or a missing cell fails --
   cardinality is pinned, not relative to the committed object); exactly
   the five pinned successes, each field-equal to the committed cells; and
   each of the four pinned failures a `FileNotFoundError` naming ITS
   documented checkout-local input path -- an unrelated path fails with
   `BAD error-path`.
4. **Fresh outputs enforced.** Both join outputs are removed and verified
   absent before each run; the stale-output + preload hazard cannot arise.
5. **Negative probes.** `repro_predicates.py --selftest` runs 11 probes:
   verdict good/312-cells/mismatch/nonzero-rc, Stage-A good,
   nonzero-rc-with-plausible-content, unrelated-missing-path, tenth-cell,
   missing-cell, value-drift, and all-cells-successful-when-archives-absent.
   11/11 PASS.

Evidence: live-repo run at beb8db2 and a fresh-clone run at d140bfe (see
D51 response) both report 5/5 with `HEADLINES: OK` under the new
predicates.
