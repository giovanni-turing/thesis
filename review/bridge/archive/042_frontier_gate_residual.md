---
from: reviewer
ts: 2026-07-26T21:39:16-03:00
re: new
type: finding
thread: D20-frontier-gate-residual
---

## Major — the new raw frontier gate still has false-green and broken-link paths

The current corpus passes, but the implementation does not establish the
claimed chain:

- If a per-cell stats file is absent, `work()` leaves `stats_agrees=None`
  (`build_frontier_summary.py:182-190`); the mismatch set selects only
  `== False` (`:203-207`). Missing evidence therefore prints
  `stats-mismatches=0` and passes `verify_all.sh:321-325`.
- `verify_all.sh` does not assert the parsed cell count; its PASS message
  hard-codes "169 cells." A shortened inventory can still print green.
- `cells()` inventories `eval/`, `eval_family/`, `adversarial/`, and one check
  (`build_frontier_summary.py:122-148`), not `calib/`. Thus M4's selection on
  burst2/6 and calibration/evaluation split membership remain ungated.
- The builder overwrites `frontier_summary_cells.json` but does not rebuild or
  compare `frontier_summary.json` (`build_frontier_summary.py:193-209`).
  `verify_all.sh:277-301` still reads derived fields from that separate
  summary, so the raw-cell recompute is not linked to the object supplying the
  printed-value checks.

Require every expected stats file, assert exactly the declared cell identities
and count, recompute/verify calibration selection, and either rebuild the
summary from those cells or compare a deterministic aggregate of the cells
against it. The current 51/0/5 run proves present consistency, not these
mutation cases.
