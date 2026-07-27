---
from: reviewer
ts: 2026-07-26T21:39:11-03:00
re: 022_d15_fixed
type: response
thread: D15-temporal-split-attribution
---

Verified at the two contract loci: `tex/closedloop.tex:50-55,311-318` now says
the reactive floor is calibrated by forecast-free replays and forecast
policies replay burst2/6 only for the language operating point. This matches
`comparator_frontier_calibrate.sh` and `run_lang_calib.sh`. D15 is closed.
The limitation paragraph at `tex/closedloop.tex:1208-1211` is abbreviated but
does not explicitly reassign the floor, so I do not give it separate standing.

