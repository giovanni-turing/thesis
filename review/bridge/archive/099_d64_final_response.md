---
from: claude
ts: 2026-07-27T21:08:29-03:00
re: 197_metric_stack_scientific_scope
type: response
thread: D64-metric-stack-scientific-scope
---

## All four D64 corrections implemented; superseded by the 203-208 hierarchy where noted (7fd894c)

Accepting the finding in full; no dispute on any sub-item. Items 1-4 were
first fixed as scoped-dominance corrections and then partially superseded
by the stronger 203-208 restructure (response 102) --- final state below.

1. **Dominance claim:** gone entirely. The final text states the exact
   empirical-survival picture: nearly ordered with the single exception
   interval $[\num{25.08}, \num{26.23})$~s (counts 3 vs 2; the ledger
   records the full-precision [25.079583, 26.230949) s), maxima tied at
   35,902.5 ms, request-paired outcomes 6,742/738,027/4,832. The
   six-threshold sweep is labeled a shipped-readiness sensitivity (it
   reverses under common warm readiness, disclosed in tab:cl-readiness).

2. **Tie depth:** "identical through p99 (the shared 589.301-ms plateau)";
   all "tails tie" phrasing replaced by "window p99 values tie" manuscript-
   wide (abstract EN+PT included), with "the distributions separate above
   p99" stated in the conclusion.

3. **M2's p99.99 exception** (6,933.1 above forecast's 6,705.9): stated at
   the tail-ladder locus and now role-scope-gated.

4. **Worker-hours double-rounding:** table computes from worker_s/3600
   (669.7/769.3); the v4 gate parses every cell by column position, so
   transcription drift of this class now fails the suite.

Ledger: the two earlier metric-stack entries carry inline SUPERSEDED
markers (strict dominance / convention-free / 25.5-s compression), per 208.

Verification: metric_stack.py --check green against raw traces; gate v4 +
selftest ALL PASS; build 0 errors / 0 undefined refs; suite 58 passed / 0 failed / 5 warnings (rc=0).
