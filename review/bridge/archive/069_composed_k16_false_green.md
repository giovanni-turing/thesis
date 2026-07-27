---
from: reviewer
ts: 2026-07-26T23:35:57-03:00
re: new
type: finding
thread: D28-composed-k16-false-green
---

## HIGH — K16 and the delivery gate retain stale 29-arm data when the source breaks

The nine current cells recompute cleanly, but that truth is not enforced by
the ingest/delivery chain.

`provenance/loader/loaders.py:589-621` has four fail-open paths:

1. a missing joined artifact returns success-like `(0, 0)` at `:589-592`;
2. an artifact cell carrying `error` or lacking `e2e_p99` is silently skipped
   at `:598-600`;
3. no assertion pins the exact nine cell identities or even `len(rows) == 9`;
4. `:619-621` only upserts. Removing a cell from the artifact does not remove
   its old database row.

Even an exception is non-terminal: `provenance/loader/main.py:94-104` prints
the error, continues, and exits zero. The delivery gate then settles once and
compares a second run (`provenance/verify_all.sh:120-134`); its digest at
`:114-119` covers raw-table counts and selected run/ingest fields, but not
`composed_e2e` row content. A missing or truncated K16 artifact can therefore
leave all 29 old rows in place and pass the settled rerun.

Registry search:

```text
rg -n 'composed_e2e|K16|29.*arm' provenance/schema/*checks*.sql
```

finds no check that pins the 20+9 source split, exact nine-cell set, or numeric
identity with `composed_fill_joined.json`. The standalone join validators are
also not invoked by `verify_all.sh`.

Concrete false-green:

- replace the K16 input logically with a one-cell object;
- K16 accepts one row and emits only an upsert plus `ingest_log n_rows=1`;
- the eight removed source rows remain in `composed_e2e`;
- after the gate's first settle pass, its second digest is stable and green.

The fix needs all four properties together: exact expected cell set/count,
source-scoped stale-row rejection or replacement, loader errors propagated to
a nonzero process status, and a delivery check that independently regenerates
the nine-cell join and compares both artifact and database projection.
