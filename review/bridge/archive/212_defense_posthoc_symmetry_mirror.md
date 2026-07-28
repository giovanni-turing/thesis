---
from: reviewer
ts: 2026-07-27T21:05:24-03:00
re: new
type: ack
---

## Pre-freeze wording correction: mirror the post-hoc symmetry caveat in defense

The manuscript now states the policy-class boundary correctly:

- `tex/closedloop.tex:674-682` calls the common-warm rows a
  reactive-favorable post-hoc sensitivity with an unexpanded forecast design
  space, and says the forecast-plus-minimum-floor family was not run.
- `tex/closedloop.tex:1490-1496` repeats that limitation and specifies how a
  deployable symmetric extension would be calibrated and graded held-out.

The defense still compresses the result past that boundary:

- `defense/reveal/index.html:511` and
  `defense/deck_single.html:912` say only that the cheapest passing reactive
  sibling costs 1.20x the forecast.
- `defense/reveal/index.html:615-618` and
  `defense/deck_single.html:1016-1019` repeat “reactive's best readiness
  footing” / “cheapest equal-compliance floor costs 1.20x” without disclosing
  that only reactive received the ex-post floor sweep.

Please attach the qualification at first use in both deck sources. A compact
defense-safe form is:

> In the reactive-favorable post-hoc floor envelope, the cheapest
> every-window-passing floor costs 1.20x the frozen forecast; a symmetric
> forecast-plus-floor family was not swept.

This preserves the useful observed operating-point comparison while preventing
it from reading as a complete or forecast-disfavorable policy-class
comparison. It is a wording mirror only; no new computation is requested.
