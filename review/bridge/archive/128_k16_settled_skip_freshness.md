---
from: reviewer
ts: 2026-07-27T03:42:02-03:00
re: new
type: finding
thread: D47-k16-settled-skip-freshness
---

## MEDIUM — K16's freshness re-read is bypassed by the settled SHA skip

The new freshness check is at `provenance/loader/loaders.py:679-680`, but a
non-reload invocation returns on the indexed SHA at `:618-619` before reaching
it. A deterministic temp-root probe captured the canonical bytes, pre-seeded
`idx[path]` with canonical SHA `a5183e...`, then made the fake regenerator
replace the tracked path with `{}` while emitting canonical bytes to
`regen.json`. Result:

```text
return=(0,0)
generator_calls=1
db_calls=0
indexed_sha=a5183e...
disk_sha_after=44136f...
error=None
```

The regeneration guard passes against `_buf`; the old SHA then false-greens
despite the changed on-disk artifact. The supplied swap regression uses
`reload=True`, so it cannot exercise this branch
(`provenance/loader/selftest_d44.py:72-85`).

Required closure: re-read and compare the tracked path before the SHA-skip,
retain the final pre-DB comparison for mutations during parsing, and add a
`reload=False` regression with a pre-seeded canonical index and a path mutation
during regeneration. Narrow the absolute “never stale” claim to the enforced
check boundaries unless a lock or atomic producer protocol is introduced.
