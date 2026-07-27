---
from: reviewer
ts: 2026-07-26T21:08:11-03:00
re: 009_rereview_request
type: finding
thread: D15-temporal-split-attribution
---

## Low/moderate — the temporal-split text assigns warm-floor calibration to forecast policies

The contract says forecast policies replay burst2/burst6 "solely to calibrate
the warm floor and the language operating point"
(`tex/closedloop.tex:38-49`; repeated at `tex/closedloop.tex:303-309`).
The warm-floor calibration contains no forecast arm: it invokes the reactive
schedule and oracle generators over `M x L x {burst2,burst6}`
(`simulation/comparator_frontier_calibrate.sh:34-44,56-58,74-106`).
Forecast replay of the calibration episodes is used for the language
quantile/conversion sweep (`simulation/run_lang_calib.sh:1-14`).

The split itself is not contaminated; this is a role-attribution error in the
evaluation contract. It should say that burst2/burst6 calibrate the reactive
warm floor, while forecast policies replay them only for the language
operating-point calibration.

