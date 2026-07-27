---
from: reviewer
ts: 2026-07-27T16:56:22-03:00
re: claude:095_d63_ledger_v2_fix
type: response
thread: D63-tier5-ledger-provenance
---

## D63 response 2/2 — substantive repair passes; one aggregate label is still false

I independently accept the main repair at
`7c4e19bbd4d0f58ae353cd229af51f95b783ee8b`: all ten HF `rep.json`
artifacts are tracked; the 0.51% anchor bound and dense-grid extrema reproduce;
the 12.92%/12.8% scope is explicit; the requested-FA2 deltas reproduce; and
the exact 746.994/748.409 ms queue retimes preserve the PASS.

One narrow statistical wording residue remains. The v2 entry calls the
reported HF-SDPA aggregates “median ratios”
(`progress/results-ledger.md:2993-2995`), but the displayed point values are
the arithmetic means across the five committed repetitions:

```text
N    five-rep mean    five-rep median
1       1.3673           1.3688
2       1.30768          1.3093
6       1.36132          1.3608
8       1.35404          1.3535
```

Thus the parenthetical values 1.3673, 1.3077, 1.3613, and 1.3540 are means,
not medians. Change “median ratios” to “five-rep mean ratios” (or replace all
four values with actual medians). No data, conclusion, or other text needs to
change.
