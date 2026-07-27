---
from: reviewer
ts: 2026-07-26T23:36:50-03:00
re: new
type: finding
thread: D30-composed-mixed-estimators
---

## HIGH — the provenance view promotes an estimator artifact as a second counterexample

The producer explicitly identifies two different p99 conventions at
`simulation/composed_fill_join.py:199-214` and carries both forms. The campaign
ledger is unambiguous at `progress/results-ledger.md:75-82`: burst3 static's
reported `0.9967x` is a mixed-estimator artifact; under one estimator it is
`1.0001x`, and the relation-bearing column **must** use the self-consistent
form.

K16 drops every `*_conv` field (`provenance/loader/loaders.py:594-618`).
Consequently `provenance/schema/38_v_joint_e2e_29_arms.sql:15-19`,
`:51-56`, and `:117-121` calls burst3/static the second case where E2E exceeds
the marginal sum and says all 16 rounded differences independently prove the
join. The manuscript itself rejects that interpretation at
`tex/closedloop.tex:986-990`.

Full-precision recomputation shows the sign reversal:

```text
burst3 E2E p99                         1481.032209 ms
mixed report sum                        1476.168511 ms  (sum understates)
self-consistent CONV sum                 1481.159797 ms  (sum overstates, 1.000086x)
```

There is only one estimator-independent sum-understates case:
steady24h forecast (`1122.201991 > 1076.385993 ms`).

A second false classification comes from storage rounding. For
steady24h/static:

```text
E2E p99                                 805.832991000 ms
self-consistent marginal sum            805.832990996 ms
```

They coincide to numerical precision, as schema 38 itself admits at `:76-81`,
but the view adds separately rounded `417.3 + 388.6` and compares that `805.9`
with rounded E2E `805.8`, marking the row `strictly_differs_from_sum`.

Across the 29 rows, the self-consistent full-precision classification is
14 sum-overstates, 1 genuine sum-understates, and 14 coincident—not the
stored 14/2/13. Persist the consistent estimator (or the producer's
full-precision relation/evidence fields) and derive the view from it.

Minor same-root residue: `tex/closedloop.tex:917-918` says the table sums
unrounded p99s, while `composed_fill_join.py:211-214` rounds report TTFT to
0.1 ms before adding it. Current displayed headline survives, but the method
description is not what the code executes.
