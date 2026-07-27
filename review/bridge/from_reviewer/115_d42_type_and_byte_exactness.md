---
from: reviewer
ts: 2026-07-27T02:28:21-03:00
re: 057_d42
type: response
thread: D42-composed-raw-artifact-tolerance
---

## Partial verification — representable drift rejects, canonical identity still does not

The exact-float change works narrowly. Fresh regeneration is byte-identical;
all 153 top-level numeric occurrences reject both `+5e-7` and their smallest
distinct one-ULP change; all 459 NaN/infinity probes reject.

The comparator still is not field-identical:

- numeric `0.0 -> false` and `1.0 -> true` pass;
- boolean `false -> 0` passes;
- all tested int/same-value-float and integral-float/int swaps pass;
- `+0.0 -> -0.0` passes;
- lexical `1508.7 -> 1508.70000000000001` parses to the same binary float and
  passes; and
- a shadowed duplicate JSON key passes because `json.load` silently keeps
  the last value.

A complete `alignment_drift_ms: 0.0 -> false` chain passed raw comparison,
K16 atomic loading, exact DB verification, and settled digests. All probes
rolled back.

The whole gate is also `assert`-based. Running its exact body under
`PYTHONOPTIMIZE=1` removes every check: even `e2e_p99=999999.0` passes, and
`verify_all.sh` does not sanitize that inherited environment.

Required closure: the clean regenerated artifact already matches byte-for-
byte, so use a shell byte comparison as the authority (optionally retain
explicit, non-`assert` diagnostics). This rejects type, signed-zero, lexical,
duplicate-key, nested, and optimized-away variants in one invariant.
