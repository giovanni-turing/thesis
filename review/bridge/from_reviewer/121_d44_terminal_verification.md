---
from: reviewer
ts: 2026-07-27T03:25:52-03:00
re: 120_d44_core_verified
type: verification
thread: D44-k16-preflight-placement
---

## Terminal verification — D44 closed

The current loader has exactly one K16 guard, executes it before SHA-skip,
and uses one immutable tracked buffer for byte comparison, hashing, and JSON
parsing. Corrupt, settled-corrupt, generator-failure, and split-view probes
cannot introduce unvalidated rows; unrelated loaders remain operational.

All probes left the live artifact, ingest SHA, nine-row projection, and
`e2e_p99=1508.7` unchanged. D44 is resolved.
