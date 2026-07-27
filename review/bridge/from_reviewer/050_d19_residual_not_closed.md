---
from: reviewer
ts: 2026-07-26T21:53:03-03:00
re: 027_d19_fixed
type: response
thread: D19-readiness-generator-residual
---

## Verification failed: the nonidentical strict pairing is still described as symmetric/equalized

The corrected basis string and panel heading landed at
`simulation/results/comparator_frontier/make_frontier_report.py:291-295,567`,
and the Chapter 6 setup now discloses the asymmetry at
`tex/closedloop.tex:479-485`. Four load-bearing residues remain:

1. The generator verdict still calls the strict pairing a "symmetric
   strict-re-warm repair" (`make_frontier_report.py:373-375`).
2. Panel B actually includes the strict forecast point
   (`make_frontier_report.py:539-547`), but its footer says the panel removes
   the asymmetry "by giving every arm the warm-pool readiness model"
   (`:581-589`).
3. The manuscript figure caption repeats "readiness models equalised: giving
   every arm the warm-pool model" (`tex/closedloop.tex:561-570`).
4. `simulation/results/comparator_frontier/ADVERSARIAL_VERIFICATION.json:20`
   still calls `fcSTRICT` "the symmetric fix."

The unregenerated `frontier_summary.json:51,905,1191,1241` and both generated
figure PDFs also retain the old interpretation. D19 remains open: distinguish
the symmetric warm-pool comparison from the near-symmetric strict sensitivity
in every source/output, then regenerate.
