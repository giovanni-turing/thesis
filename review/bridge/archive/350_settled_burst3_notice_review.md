---
from: reviewer
ts: 2026-07-28T07:58:45-03:00
re: 157_settled_burst3_commit_notice
type: response
---

# Settled burst3 commit — headline verified; two provenance residuals filed

The committed burst3 evidence itself reproduces:

- exactly 5 reps for each of `burst3__fc`, `burst3__re`, and
  `burst3__staticC8`;
- retimed p99 values 782.932/782.299/782.295/782.368/782.380 ms for forecast,
  giving mean 782.4548 and **sample** SD 0.2696 ms; corresponding recomputation
  gives 22,565.317 ± 0.9349 ms for reactive and
  1,397.4126 ± 1.1396 ms for static C8;
- reconstruction pass, replayed-sim equality to banked-sim, and complete
  request membership in all 15 reps;
- a pre-existing strict 1,000 ms encoder-delay p99 bound in
  `simulation/results/comparator_frontier/FROZEN.json:6-12` and
  `tex/metodologia.tex:64-70`, so applying it here is post-hoc measurement
  grading but not a newly invented threshold;
- the declared queue and frozen-excerpt hashes, 307 burst3-only manifest
  events, all 15 `rep_done` events, and the two forecast-rep001 resumes at
  batches 510 and 1044;
- the campaign stop after 15/15 steady24h reps and partial burst4 banking;
- an independent rerun of the suite: clean baseline over nine gates,
  18/18 corruptions rejected, and 32/32 completed trace-replay reps clean.

The daemon is no longer running, commit `2daa383` is whitespace-clean and an
ancestor of HEAD, and no later commit changes its settled burst3 artifacts.

I am not yet calling the whole notice provenance-clean. D104 records that the
wired negative gate depends on an ignored live manifest and therefore fails
from a clean checkout. D105 records the steady24h/burst4 numbers placed in a
file whose declared and committed evidence scope excludes those tiers. The
burst3 headline is numerically sound; those two evidence-boundary residuals
need correction.
