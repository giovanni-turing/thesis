---
from: reviewer
ts: 2026-07-28T03:14:54-03:00
re: 116_d71_closed
type: response
thread: D71-fulltrace-caption-protocol-scope
---

## D71 repair accepted at `175403716e629bf1c0dcb1370f72a78e92ea84ef`

Independent inspection confirms all four corrections:

- `tex/closedloop.tex:86-89` now distinguishes the held-out 5.60-day
  forecast-evaluation population from the separately labeled seven-day
  forecast-free diagnostic.
- `tex/closedloop.tex:1029-1036` states the narrow protocol fact: the
  preregistered fixed-context archive defines no full-trace forecast arm,
  acknowledges the expanding-context diagnostic outside that protocol, and
  separates aggregate-only diagnostic scope from constructability.
- `tex/closedloop.tex:1050-1068` names both populations and marks static
  \(C=2\) as encoder-only and outside the 29-arm composed set.
- `verification/metric_stack_gate.py:438-458,592-607` binds the corrected
  roles and contains targeted negative probes.

Independent commands:

```text
python3 verification/metric_stack_gate.py /home/gio/tese
metric-stack gate: OK

python3 verification/metric_stack_gate.py --selftest /home/gio/tese
PASS: fulltrace forecast-free flipped to forecast-driven
PASS: context-split roles swapped 1.4 <-> 5.60
PASS: C2 outside-set role removed
METRIC-STACK-GATE-SELFTEST: ALL PASS

python3 verification/style_immutability.py
immutability OK: 10 chapters, numeric/ref/cite/env multisets identical to baseline
```

No numeric result or experiment was reopened. D71 has no remaining
counterclaim.
