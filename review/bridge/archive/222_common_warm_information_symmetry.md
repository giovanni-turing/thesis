---
from: reviewer
ts: 2026-07-27T23:32:54-03:00
re: new
type: ack
---

## Author reconfirmation: common-warm selection is post-hoc knowledge

The author sharpens the fairness argument: selecting the minimum warm floor
that passes the evaluation span uses outcome knowledge unavailable to an
operational controller. If that privilege is granted to the reactive family,
information symmetry would also permit an ex-post sweep of
`max(forecast_schedule, M)` and selection of its minimum passing member.

The live manuscript already captures this correctly:

- `tex/closedloop.tex:676-684` labels common-warm a reactive-favorable
  post-hoc sensitivity with an unexpanded forecast design space; and
- `tex/closedloop.tex:1545-1551` names the symmetric forecast-plus-floor
  family, requires calibration selection plus held-out grading for a
  deployable comparison, and makes no unrun numerical claim.

Preserve that boundary in the final compression. Its exact implication is:

1. warm M1's lower delay does not establish reactive policy-class
   superiority because M1 fails the declared held-out every-window gate;
2. warm M2 at 801.8 worker-hours versus the frozen forecast at 669.7
   worker-hours is a conservative observed operating-point fact inside a
   reactive-favorable post-hoc envelope, not a complete symmetric frontier;
3. the operational claim must rest on parameters selected using only
   calibration/deployment-available information and then graded held-out;
   and
4. the unrun forecast-plus-floor sweep is a limitation/future robustness
   experiment, not a closeout dependency and not grounds for speculation.

The defense currently preserves the caveat at
`defense/reveal/index.html:619-622`. No new experiment is requested. This is
the information-symmetry rule that should govern any final wording about
“best” or “minimum” common-warm comparators.
