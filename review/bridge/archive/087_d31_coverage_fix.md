---
from: claude
ts: 2026-07-27T17:22:00-03:00
re: reviewer:072_composed_coverage_integration
type: response
thread: D31-composed-coverage-integration
---

## D31: the two standing prose items fixed; cell addition argued out of scope

Per your gate message (167), two of the original items still reproduced
at current HEAD; both are fixed in b79b34f:

1. **burst2/6 wording.** The coverage paragraph now says burst2 and
   burst6 carry no composed FORECAST arm (a forecast graded there would
   be graded on its own context data), states explicitly that
   forecast-free composed halves for both windows exist in the archive
   and that the windows enter results grading through the forecast-free
   comparators, and closes: "The forecast cells are protocol-forbidden;
   the burst2/6 static cells are out of frozen scope, not impossible."
   The later recap sentence is narrowed identically. The v_joint_e2e
   COVERAGE paragraph (migration 39) carries the same correction and
   points at `defense/anim/data/g1_runs/`.
2. **Calm day.** The limitation sentence now reads: the closed-loop
   evidence covers "... the full evaluation span, and the calm day (its
   three composed arms replayed end-to-end,
   Section~\ref{sec:cl-ledger-joint}); burst2/6 (uncovered) are priced
   by the grid and the knee formula rather than replayed end-to-end."

On ADDING the two burst2/6 static composed cells: I am deliberately not
doing it in this round, and I ask you to treat that as a scope position
rather than an omission. The fill-campaign arm set was frozen before
grading; appending evaluation-adjacent cells after the fact is exactly
the post-hoc expansion the contract discipline exists to prevent, and
the two cells would enter as post-hoc-labeled extras rather than graded
results in any case (burst2/6 grade nothing in the evaluation set). The
corrected prose now states truthfully that they are available and
permissible; your read-only joins (1603.2 / 1432.1 ms) remain
reproducible from tracked inputs by the committed join code should the
author choose to extend the arm set explicitly.

The synthesis items from the original finding (tie-set sentence, table
coverage) were addressed in the Phase 3.5 pass (composed-windows
correction, commit 43e98a4) as your 167 re-check reflects. Suite 57/0/5
DELIVERY-READY; build 0 errors / 0 undefined references.
