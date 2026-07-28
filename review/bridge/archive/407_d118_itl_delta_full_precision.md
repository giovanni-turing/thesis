---
from: reviewer
ts: 2026-07-28T17:04:09-03:00
re: 191_itl_delta_units_notice
type: finding
thread: D118-itl-delta-full-precision
---

# D118 — Keep the dual-unit cell, but derive the percentage before rounding

Percentage-first plus the absolute delta is the clearer presentation. The new
`18.6%`, however, is a regression: it is computed from the rounded display
cells rather than the governed full-precision operands.

The current DB gives:

```
provenance.live_arm
  live_fc.itl_p99_ms = 11.469605181217391

provenance.llm_run_summary
  live:twin_fc_p90_cap4.p99_tpot_ms = 9.718327791667738
```

Using the table's `(live - offline) / offline` convention:

```
absolute = 11.469605181217391 - 9.718327791667738
         = 1.751277389549653 ms  ->  +1.8 ms

relative = 1.751277389549653 / 9.718327791667738
         = 18.020357%            ->  +18.0%
```

The proposed `18.6%` comes only from rounded values:
`(11.5 - 9.7) / 9.7 = 18.56%` (equivalently `1.8 / 9.7`), which rounds twice
before deriving the percentage.

This exact distinction was already resolved in
`progress/results-ledger.md:591-596`: full precision gives 18.0%, while
18.6% is explicitly identified as rounded-cell arithmetic. The governed
audit repeats the operands, 18.020% recomputation, and “keep 18.0%” ruling at
`provenance/audit/verified/validation.json:621-626`.

Correct:

- `tex/metodologia.tex:711` to
  `$+18.0\%$ ($+1.8$\,ms)`; and
- `tex/metodologia.tex:792` back to `18.0\%`.

Retain the dual-unit presentation. No data rerun is needed; this is one cell,
one prose numeral, and a build check.
