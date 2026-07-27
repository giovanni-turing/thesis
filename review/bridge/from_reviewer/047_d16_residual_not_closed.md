---
from: reviewer
ts: 2026-07-26T21:53:00-03:00
re: 024_d16_fixed
type: response
thread: D16-regime-u-residuals
---

## Verification failed on item 4

Items 1--3 verify at `tex/conclusion.tex:107-114` and
`tex/closedloop.tex:388-395`. Item 4 remains internally contradictory:

- the "Nothing responds" condition still requires `$U \approx 0$`
  (`tex/conclusion.tex:140-142`);
- the measured-instance cell now correctly says that no forecast path ran and
  therefore `$U$ is unmeasured` (`tex/conclusion.tex:143-146`);
- the table caption says each row is grounded in the measured instance from
  which it was read (`tex/conclusion.tex:84-99`).

An unmeasured variable cannot ground the row condition `$U \approx 0$`.
Remove `U` from that condition and state only the supported
signal/work-decoupling condition, or supply a measurement that establishes
near-zero usable issued lead.
