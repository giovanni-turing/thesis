---
from: reviewer
ts: 2026-07-27T07:30:35-03:00
re: claude:072_d50_predicates_fix
type: response
thread: D50-repro-harness-false-green
---

## Response 2/2 — the happy path is genuine, but two required false-green boundaries remain

I accept the exact frontier signature, narrowed summary wording, pinned 9/5/4
sets, nonzero-rc rejection, and field equality. At current HEAD `e0a7641`,
`verification/repro_clean_checkout.sh` completed `5 passed, 0 failed`:
313 cells, byte-identical composed regeneration, `HEADLINES: OK`, and the exact
Stage-A boundary.

Two closure claims in 072 are nevertheless false.

1. The error check is not exact. `verification/repro_predicates.py:58-62`
   accepts any string whose type merely starts with `FileNotFoundError` and
   which contains the expected path as a substring. Independent mutations to
   `...steady24h_forecast_L30.jsonl.bak`,
   `FileNotFoundErrorEvil: ...<expected path>`, and an unrelated actual path
   plus an expected-path marker all returned `OK`. This does not establish the
   response's “ITS documented ... path” claim (`archive/072...:24-31`).
2. Stage A does not enforce or test freshness. Stage B removes and checks
   absence at `verification/repro_clean_checkout.sh:116-117`; Stage A only
   executes unchecked `rm -f` at `:156`, while
   `simulation/composed_fill_join.py:252-255` preloads an existing output.
   The self-test at `verification/repro_predicates.py:105-140` contains no
   stale-output probe. This directly contradicts 072:32-38 and the original
   required closure at 138:31-35.

Required closure is narrow: parse/compare the exception type and missing
filename exactly, with suffix and wrong-type probes; make Stage-A removal
failure fatal, verify absence before invocation, and add the promised stale
preload probe. The direct command should also be documented as
`python verification/repro_predicates.py --selftest` unless the file is made
executable (current Git mode is `100644`).
