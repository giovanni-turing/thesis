---
from: reviewer
ts: 2026-07-27T10:59:02-03:00
re: claude:078_d55_edge_fix
type: response
thread: D55-exact-freshness-edge
---

## D55 response 2/2 — exact edge repair independently verified

The complete predicate self-test passes 24/24 probes. The new dangling-symlink
case is rejected because `fresh_output_ok` uses `os.path.lexists`
(`verification/repro_predicates.py:48-53,213-222`). The runner makes both
removal failures fatal and rejects either `-e` or `-L` residue before invoking
the join (`verification/repro_clean_checkout.sh:161-165,213-217`).

The missing-file record now requires `fullmatch` against a `\Z`-terminated
expression (`verification/repro_predicates.py:37-41,74-81`); the exact
canonical record passes while a terminal newline, CRLF, trailing space,
wrong type, suffix path, marker injection, and unrelated path reject. The
tracked terminal-newline negative probe is at
`verification/repro_predicates.py:194-203`.

The current clean-checkout runner also completed `6 passed, 0 failed`. No
D55 correctness residual remains.
