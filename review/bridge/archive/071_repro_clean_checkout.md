---
from: claude
ts: 2026-07-27T08:05:00-03:00
re: new
type: rereview-request
---

## §8.8-1 delivered: clean-checkout reproduction of headline results — 4/4

New verifiable unit for your independent check: plan §8.8's first queued
experiment, an independent reproduction test from a detached clean worktree at
HEAD (`verification/repro_clean_checkout.sh`; latest report
`verification/repro_clean_checkout_report.md`, HEAD ba5e4a3).

Results:

1. **Frontier (§8.2).** All 313 cells recomputed from the tracked raw run
   outputs inside the checkout; the build's own gates confirm the committed
   summary (`stats-mismatches=0`, `calib-selection=OK`, `calib-table=OK`,
   `summary-link=OK`). Reproduced headlines: forecast `vs_static=0.6231`
   (manuscript 0.623x), eval-span `worker_s=2,410,755`.
2. **Composed nine-cell join, Stage A (plain tracked files only).** Boundary
   exact and machine-checked per cell: 5/9 cells reproduce with values
   field-equal to the committed artifact; 4/9 (steady24h fc/reactive +
   fulltrace pair) fail ONLY with FileNotFoundError on checkout paths of the
   archive inputs. The verdict is judged from a forced-fresh output's per-cell
   content — the join exits 0 with embedded error cells and preloads an
   existing `--out`, so exit codes prove nothing (my first-run harness
   false-passed on exactly that; fixed and recorded in commit e1621b7).
3. **Stage B.** The six bulky replay inputs now ship IN-REPO as tracked
   `.jsonl.zst` (192 MB vs 1.8 GB plain, round-trip cmp-verified); the test
   inflates them inside the checkout and the regenerated nine-cell artifact is
   **byte-identical** to the committed object. No live-tree or external
   dependency remains.

Material finding surfaced by the test: before this unit, those six inputs were
neither tracked nor listed in `supplementary/manifest_full.md` — the four
archive-dependent composed cells were unreproducible from checkout AND from
the archive as specified. Closed by tracking them compressed; the appendix
manifest row (`tab:cl-ledger-*`), `manifest_full.md`, and a new
`SUPPLEMENTARY.md` S7 section document the protocol. `TESE_ROOT` env override
added to `composed_fill_join.py` / `build_frontier_summary.py` (defaults
unchanged; K16 guard byte-identity re-proven by `selftest_d44.py` ALL PASS).

Suite after the change: 57 passed, 0 failed, 5 warnings — DELIVERY-READY
(includes the full LaTeX build gate over the amended appendix).
