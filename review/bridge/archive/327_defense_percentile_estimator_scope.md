---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D97-defense-percentile-estimator-scope
---

# D97 — The defense universalizes one percentile estimator beyond its scope

The new theory paragraph and quick-facts card say that **every** reported p99
uses the converter's non-interpolating order-statistic rule and that every p99
is an observed request delay (`defense/defense-qa.tex:1848-1862`;
`defense/defense-qa.tex:2545-2548`). Both universal claims are false.

- The trace's reported 99th-percentile image-rate threshold,
  224 images/s (`tex/trace-eda.tex:233-235`), is computed with default
  `numpy.quantile` (`analysis/trace_eda/i_burst_anatomy.py:23-24`), whose
  default is linear interpolation. It is also a rate, not a request delay.
- The modeled ingress-to-first-token p99 reported at
  `tex/metodologia.tex:83-86` is produced with default
  `numpy.percentile` (`verification/scripts/e2e_ingress_to_first_token.py:50-52`;
  `verification/scripts/e2e_ingress_to_first_token.py:116-118`).
- Even inside the replay stack, the report and converter can use adjacent
  order statistics; this mixed-estimator boundary is explicitly documented at
  `simulation/composed_fill_join.py:214-227`.

The exact
`sorted[min(n-1, floor(np/100))]` rule is supported for the encoder
converter/frontier recompute (`workload/trace_to_two_pool.py:401-405`;
`simulation/results/comparator_frontier/build_frontier_summary.py:79-81`).
Please scope the defense statement, including the 589.301 ms plateau
explanation, to that encoder comparator/metric-stack family rather than to
every p99 in the thesis.
