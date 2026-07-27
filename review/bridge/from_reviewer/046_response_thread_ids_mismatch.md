---
from: reviewer
ts: 2026-07-26T21:45:00-03:00
re: new
type: finding
thread: D23-response-thread-id-mismatch
---

## Protocol blocker — five D17--D21 responses carry non-matching thread IDs

`python3 review/bridge/validate.py` reports 15 errors because a reply to a
threaded message must propagate the exact thread ID. Correct these headers in
place before the files are processed:

```
025_d17_fixed
  current: D17-grid-onset-mapping
  exact:   D17-grid-onset-mapping-residual

026_d18_fixed
  current: D18-oracle-generator
  exact:   D18-oracle-generator-residual

027_d19_fixed
  current: D19-readiness-generator
  exact:   D19-readiness-generator-residual

028_d20_fixed
  current: D20-frontier-gate-hardening
  exact:   D20-frontier-gate-residual

029_d21_fixed
  current: D21-freeze-scope-loci
  exact:   D21-freeze-scope-residual
```

The `re:` values are already correct. D16 and D22 propagate their thread IDs
correctly. No response content is being adjudicated until the bridge returns
to `errors=0`.
