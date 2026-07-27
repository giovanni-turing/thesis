---
from: reviewer
ts: 2026-07-26T21:08:03-03:00
re: 009_rereview_request
type: finding
thread: D07-onset-provenance-regression
---

## Major provenance regression — Finding 8 is correct in prose but not in the mapped reproduction chain

The manuscript now gives the corrected population and onsets: 18 episodes,
median 6.5 minutes, six within 1--2 minutes
(`tex/trace-eda.tex:234-260`). The authoritative regenerated artifact agrees:
burst1 is `404` minutes and burst6 is `53`
(`analysis/trace_eda/i_burst_anatomy_stats.json:6-12,24-33,75-83`).

However, the appendix explicitly maps onset detection to
`simulation/detect_onsets_44.py` and
`simulation/results/riders44/detection_delay.json`
(`tex/apendice.tex:185-190`). Those mapped objects still encode burst1 as
`220` minutes (`detect_onsets_44.py:30-37`;
`detection_delay.json:4-7`). The mapped grid artifact likewise retains
burst1 `220` and burst6 `1`
(`simulation/results/grid/grid_summary.json:9-14,65-69`), and
`simulation/run_lang_calib.sh:10-13` still describes burst6 as a one-minute
onset.

Thus the corrected scientific statement survived the restructure, but its
declared artifact/script path can regenerate or report the superseded values.
This fails strict preservation of old Finding 8's evidence chain even though
the visible prose is correct. The appendix must point to the authoritative
generator/artifact or the mapped objects must be regenerated consistently.

