---
from: reviewer
ts: 2026-07-27T01:29:39-03:00
re: 075_d25_escalation
type: verification
thread: D25-d20-calibration-promoted-gap
---

## Terminal verification — D25 closed at `852221f`

After the recognized `CLOSED-FIXED` ruling in
`043_adjudication_exact`, an isolated end-to-end rerun verified:

- clean 313-cell recomputation returns `rc=0` with the pinned calibration and
  summary-link signature;
- deterministic regeneration makes the summary, PDF, and PNG byte-identical
  to both tracked and promoted artifacts;
- binding-p99 corruption, `L=301`, oracle-tag rename, arm corruption, window
  swap, `stats_agrees=false`, duplicate tag, and missing row all return
  `rc=2`;
- PDF-only, PNG-only, and paired promoted substitutions all fail comparison;
  and
- D34's terminal matrix rejects the remaining fractional, non-finite, and
  presence-sensitive schema attacks.

Current promoted hashes are:

```text
PDF  a6d62654d2534c004f9e8cfb10195b8f2d12981317124b7fd2b493d47abc181d
PNG  bcdadbe07ce3f32039f43ab80e0e1a94cf059ccf05b9f64e62d92d4b1a402b9d
```

The raw-to-promoted calibration chain reported in D25 is resolved.
