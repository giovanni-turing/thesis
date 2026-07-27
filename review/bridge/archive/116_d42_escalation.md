---
from: reviewer
ts: 2026-07-27T02:37:51-03:00
re: 115_d42_type_and_byte_exactness
type: escalation
thread: D42-composed-raw-artifact-tolerance
---

## Escalation — byte identity is correct but runs after K16 writes

The new `cmp` invariant is verified: clean regeneration is byte-identical and
all prior boolean/number, int/float, signed-zero, lexical, duplicate-key,
gross-drift, missing/extra, generator-failure, and `PYTHONOPTIMIZE` attacks
reject.

Its ordering remains unsafe:

- A6 runs full `main.py`, including K16, at
  `provenance/verify_all.sh:125` and again at `:128`;
- fresh regeneration and `cmp` occur only later at `:367-373`; and
- `--data` sets `WANT_THESIS=0`, so that later check never runs.

A valid nine-cell artifact carrying `burst1 e2e_p99=999999` was accepted by
K16, which emitted an atomic committed replacement and corrupt ingest SHA.
Executing the exact transaction with only final `COMMIT` changed to audit
plus `ROLLBACK` showed `999999` and the corrupt SHA in-transaction. The later
byte check rejects, but default verification detects only after the write;
`--data` can settle fully green without detecting it.

At the two-response ceiling, D42 is escalated. Required closure: make
regeneration plus byte identity a fatal pre-ingest prerequisite before either
loader call, run it in `--data` too, and prove corrupt artifact or generator
failure causes zero K16 calls/writes.
