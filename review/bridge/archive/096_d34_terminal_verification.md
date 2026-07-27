---
from: reviewer
ts: 2026-07-27T01:26:46-03:00
re: 092_d34_escalation
type: verification
thread: D34-calibration-type-finiteness
---

## Terminal verification — D34 closed at `852221f`

After the recognized `CLOSED-FIXED` ruling in
`049_adjudication_d34_d37`, an isolated current-tree matrix verified:

- clean corpus with explicit oracle `M:null`: `rc=0`, full green signature;
- missing oracle `M`: `rc=2`, with `M must be present and null, got
  <absent>`;
- oracle `M=4.5` and `M=Infinity`: `rc=2`;
- finite binding-p99 and oracle-worker-time drift: `rc=2`; and
- fractional floor `M`/`L`, p99 NaN, fractional counts, infinite
  worker-time, and adjacent missing numeric fields: all `rc=2`.

No remaining presence, type, finiteness, or exact-value bypass was found in
the tracked calibration schema. D34 is resolved.
