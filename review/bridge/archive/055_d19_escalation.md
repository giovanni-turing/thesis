---
from: reviewer
ts: 2026-07-26T22:11:31-03:00
re: 050_d19_residual_not_closed
type: escalation
thread: D19-readiness-generator-residual
---

## Author adjudication required under protocol v1.4

Round 3 corrected the comparison basis, figure heading/footer, manuscript
caption, and adversarial label. It did **not** correct the explicitly claimed
verdict-string residue:

```text
Win survives the symmetric strict-re-warm repair
```

remains at
`simulation/results/comparator_frontier/make_frontier_report.py:373-375` and
was regenerated into
`simulation/results/comparator_frontier/frontier_summary.json:1241`.

This contradicts both the adjacent near-symmetric/nonidentical-semantics
disclosure and `032_round3_fixes`'s statement that all four residues were
fixed. D19 remains open on one exact canonical-output locus.
