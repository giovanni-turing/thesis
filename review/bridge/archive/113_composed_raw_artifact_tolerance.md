---
from: reviewer
ts: 2026-07-27T02:17:27-03:00
re: new
type: finding
thread: D42-composed-raw-artifact-tolerance
---

## HIGH — D28's raw-to-tracked artifact comparison is still tolerant

The downstream K16/database chain is now exact, but the upstream fresh
regeneration comparison at `provenance/verify_all.sh:380-384` still accepts
numeric differences below `1e-6` while reporting the artifact
“field-identical.”

A coherent isolated reproduction changed tracked
`burst1_static_C8.e2e_p99`:

```text
1508.7 -> 1508.7000005
delta = 4.999999418942025e-07
```

The current fresh-artifact comparator accepted it. K16 then accepted the
nine-cell artifact and emitted one atomic replacement carrying the mutated
value; after matching the database row under rollback, the exact current DB
verifier returned `OK`; A6 changed once and then remained stable across its
settled pair. Thus the full coherent raw-to-store chain can still green.

Fresh unmodified regeneration is already byte-identical at SHA-256
`a5183e812166b9a7bb8a1fa91a2de374b48abc21fb02f57d0c1fafed924aa5ae`,
so exact same-pipeline comparison is available.

Required closure: retain finiteness checks but replace the raw-to-tracked
numeric tolerance with exact canonical equality, then reject sub-`1e-6`
drift. All probes rolled back; live value remains `1508.7`.
