---
from: reviewer
ts: 2026-07-26T21:39:03-03:00
re: 014_d07_fixed
type: response
thread: D07-onset-provenance-regression
---

The riders mapping and calibration-script comment are verified:
`tex/apendice.tex:185-195` now identifies the legacy riders labels and points
statistics to `i_burst_anatomy`, and `simulation/run_lang_calib.sh:10-13`
uses the corrected 53-minute merged onset.

The original evidence-chain finding also named the separately mapped
`results/grid/grid_summary.json`; that file still says burst1=220 and burst6=1,
while its appendix row has no caveat. I therefore cannot call the full D07
chain closed. The remaining concrete mapping defect is split into D17.

