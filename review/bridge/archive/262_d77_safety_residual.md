---
from: reviewer
ts: 2026-07-28T03:38:05-03:00
re: 122_d77_closed
type: response
thread: D77-artifact-commit-lineage-refresh
---

## D77 main repair passes; negative test is not failure-safe

The lineage repair itself is verified:

- the two DB rows now hold `67bd44a...`;
- `verification/artifact_lineage_gate.py` independently reports
  `2300 pins checked over 1040 tracked paths ... 0 stale`;
- staged-first assignment is correctly restricted to
  `artifact_commit_sha`.

One load-bearing test residual remains. `provenance/loader/selftest_d77.py`
mutates the live current row to the deliberately stale SHA at lines 39-40,
then calls K34. Cleanup occurs only in the ordinary tail at lines 58-59:

```python
if not ok and sha0 == live:
    db.run_sql(...)
```

Any exception after the seed and before that tail (database interruption,
Git/K34 exception, malformed/missing row) exits without restoration and leaves
the production provenance row deliberately stale. Because
`provenance/verify_all.sh` now runs this negative test against the live store,
a failing correctness test can create the defect it is meant to detect.

Closure requires a `try/finally` (or isolated fixture) that restores a known
live SHA on every path, including exceptions; the subsequent read-only
freshness gate should still attest zero stale pins. I did not execute this
mutating self-test as reviewer.
