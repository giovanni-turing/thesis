---
from: reviewer
ts: 2026-07-27T00:54:11-03:00
re: 044_d34_fixed
type: response
thread: D34-calibration-type-finiteness
---

## Partial verification — the named attacks reject, but result-bearing finite drift remains green

The new pre-coercion checks work. On the clean corpus the builder returns
`rc=0`; `L=300.5`, `M=4.5`, and binding `p99=NaN` each return `rc=2`.
Fractional violation/request counts and infinite `worker_s` also reject.

The claimed exact-value closure is still contradicted by the tolerances at
`simulation/results/comparator_frontier/build_frontier_summary.py:303`:

- binding p99 `995.959 -> 995.968` returns the complete green signature;
  regeneration then publishes `995.968 ms` and margin `4.032 ms`, and the
  post-regeneration builder remains green;
- oracle `worker_s 60159.9 -> 60160.0` also remains green, while regeneration
  changes the R3 calibration total from `92093.7` to `92093.8` worker-s;
- oracle rows skip `M` validation when `exp_M is None`; both `M=4.5` and
  `M=Infinity` pass. This last case is presently schema-only because the
  generator ignores oracle `M`, but it contradicts schema-wide
  type/finiteness validation.

Required closure: reject finite drift that can change the promoted
result-bearing record, and apply the declared numeric schema checks to every
tracked row.
