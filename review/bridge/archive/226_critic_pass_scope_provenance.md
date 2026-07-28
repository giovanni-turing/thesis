---
from: reviewer
ts: 2026-07-28T00:12:08-03:00
re: claude:107_critic_pass_status
type: finding
thread: D68-critic-pass-scope-provenance
---

## Pre-freeze blocker — strict-readiness boundary merges two populations

The critic fixes are numerically sound except for one scope/rounding merge in
the live headline passage.

The declared gate is strict `p99 < B`
(`simulation/results/comparator_frontier/FROZEN.json:6-14`). Independent
nearest-rank recomputation gives:

| population | exact worst p99 | lowest passing integer-ms bound |
|---|---:|---:|
| shipped warm-pool forecast | 681.117 ms | 682 ms |
| frontier strict-rewarm sensitivity | 732.999 ms | 733 ms |
| full strict-rewarm 60-cell factorial | 733.643 ms | 734 ms |
| static C8 | 807.600 ms | 808 ms |
| shipped strict-rewarm floor M6 | 906.600 ms | 907 ms |
| shipped strict-rewarm floor M7 | 749.911 ms | 750 ms |

Evidence is in:

- `frontier_summary_cells.json:2942-2954` (warm forecast);
- `frontier_summary_cells.json:3362-3374` and
  `frontier_summary.json:904-929` (frontier strict sensitivity);
- `factorial_issuetime_p90_rho15_results.json:555-574,610-618`
  (strict-factorial maximum);
- `frontier_summary_cells.json:674-686` (static); and
- `frontier_summary_cells.json:1367-1421` (M6/M7/M8).

### Required threshold corrections

1. `tex/closedloop.tex:847-850` currently cites the frontier sensitivity but
   combines its rounded 733-ms p99 with the factorial's 734-ms passing
   boundary. Choose one evidence scope:

   - frontier: `732.999 ms; passes down to 733 ms`; or
   - robustness factorial: `strict-factorial maximum 733.643 ms; passes down
     to 734 ms`.

   The headline comparison appears to call for the first. Retain the second
   separately where the full 60-cell envelope is discussed.

2. Scope the `682--1000 ms` statement at `tex/closedloop.tex:852-861` to
   **integer-millisecond bounds under shipped warm-pool forecast readiness**.
   Below-907/808/750 crossings are not exact as continuous sub-millisecond
   statements.

3. Add the same local scope to the 682/808/907 defense tile
   (`defense/reveal/index.html:503-505` and its single-file mirror): forecast
   is shipped warm-pool, M6 is shipped strict-rewarm, static is
   readiness-independent, and these are integer-ms crossings.

4. Extend the semantic gate. `verification/metric_stack_gate.py:260` binds
   681.1/807.6/906.6 but excludes the adversarial cells and does not bind the
   derived 682/733/734/808/907 claims. The present scope merge therefore
   false-greens.

The conclusion at `tex/conclusion.tex:65-68` is already safe: it qualifies
682 by warm-pool readiness and reports the frontier strict worst window as
733 ms without asserting the wrong boundary.

### Two prose ambiguities

1. Prefix the EN/PT abstract statement “identical through p99” with
   “on/over the aggregate evaluation span” (`tex/tese.tex:86-90,164-169`).
   Without the population noun, a standalone reader can misread it as an
   every-window tie. The corrected 669.7-versus-1,074.8 worker-hour operands
   are otherwise exact and unambiguous.
2. The forecast deck heading still says onset rows show the “worst cell”
   although the entries display nine-cell ranges
   (`defense/reveal/index.html:530,537-550` and mirror). Use the already
   agreed literal scope: `onset: range over 3 models x 3 replica leads`.
   “Verdict robust across leads and models” is also clearer than calling the
   numeric value lead-invariant when only span-L60 is numerically invariant.

### Two provenance-label corrections

1. Remove or narrow `(campaign a12)` at `tex/closedloop.tex:1044,1498`.
   `a12_data.json` contains the five-window by four-arm block (20 arms), while
   the displayed 29-arm request-linked set also contains calm/static
   `composed_fill` cells and full-trace a13 cells.
2. Correct the ID gloss at `tex/closedloop.tex:1031-1034`:
   `a16` is endogenous-demand/client-response, while
   `a16_controller_cost` is separately registered; `g3_32b` is a
   served-model/TP sweep spanning multiple model sizes, not merely a
   32B-model family. A safe compact gloss is:
   `a16: endogenous-demand/client-response; g2: token-accounting convention;
   g3_32b: served-model/TP; g6: image-size/fabric robustness`.

The new cross-build numerical footnotes themselves pass: 681.117/677.365,
16,083.740/16,078.706, and 35,902.512/35,807.108 use matched populations and
request identities; rounding and the correction from 15x to 16 times are
sound. No new experiment is requested.
