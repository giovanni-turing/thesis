---
from: reviewer
ts: 2026-07-26T21:08:06-03:00
re: 009_rereview_request
type: finding
thread: D10-overlapping-evaluation-units
---

## Major evaluation-contract defect — two of the five declared independent episodes overlap

The contract names an evaluation episode as the independent unit and says the
evidential units are five episodes (`tex/closedloop.tex:38-49,325-334`).
But burst4 and burst5 are not disjoint:

```
burst4 = [565664, 565664 + 25639) = [565664, 591303)
burst5 = [558386, 558386 +  8983) = [558386, 567369)
overlap = [565664, 567369) = 1705 requests
```

The operands are in `simulation/windows.json:35-55`. The time annotations show
the same overlap (burst4 begins 15:37 while burst5 ends 15:53). The duplicated
population is 1,705 / 25,639 = 6.65% of burst4 and
1,705 / 8,983 = 18.98% of burst5.

This does not change the current all-pass/all-fail verdict of any arm, but it
invalidates the explicit independence language and overstates "five
evidential units." Either rebuild disjoint episode blocks or call them five
evaluation windows and disclose the overlap; they cannot support an
independent-unit interpretation as presently written.

