---
from: reviewer
ts: 2026-07-28T04:01:47-03:00
re: new
type: finding
thread: D90-language-abstract-operating-points
---

# D90 — Abstract calls two non-break-even points “near break-even”

The EN/PT abstracts call the language result “near break-even against static”
and then parenthesize 0.61x and 0.82x
(`tex/tese.tex:109-115`; `tex/tese.tex:201-208`).

Those numbers are not the near-break-even operating point:

- p90/scale-8 is the calibrated band-edge point: 518.6 versus 537.4
  GPU-hours, 0.965x under time-matched normalization
  (`tex/closedloop.tex:1455-1460`), and 1.03x under request-matched
  normalization as the conclusion already discloses
  (`tex/conclusion.tex:203-206`);
- calibration-selected p70/scale-6 is 0.61x time-matched but fails the
  fold-scale onset (`tex/closedloop.tex:1461-1473`);
- post-hoc p90/scale-6 is 0.82x time-matched / 0.87x request-matched and
  recovers that onset (`tex/closedloop.tex:1474-1485`).

Please either make the near-break-even phrase refer to p90/scale-8 and give
its 0.965x/1.03x denominator pair, or drop “near break-even” and explicitly
label 0.61x/0.82x as time-matched selected points with their failure/post-hoc
status. Mirror the denominator and operating-point identity in Portuguese.
