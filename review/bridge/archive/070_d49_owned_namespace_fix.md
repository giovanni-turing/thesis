---
from: claude
ts: 2026-07-27T06:55:00-03:00
re: reviewer:134_k16_selftest_temp_namespace
type: response
thread: D49-k16-selftest-temp-namespace
---

## D49 fixed: hygiene asserts only the suite-owned regen namespace

Implemented exactly as required in `provenance/loader/selftest_d44.py`:

1. **Owned namespace.** `tempfile.tempdir` is set to the suite's outer `TD`
   for the duration of the probes (restored in `finally`), so every
   `k16_regen_*` directory the loader creates in THIS process lands under
   `TD`. The hygiene assertion (`owned_leftovers()`) lists `TD` only —
   nothing global is scanned.
2. **Concurrency control, foreign direction.** Probe 8b creates an unrelated
   `k16_regen_*` directory in the REAL global temp root (captured before the
   patch) and asserts the result is unaffected; the suite removes only the
   directory it created.
3. **Concurrency control, owned direction.** Probe 8c plants a leaked
   `k16_regen_leak` under `TD` and asserts detection still fails it —
   cleanup detection is not weakened; all owned leftovers still count.

Evidence: full run ALL PASS with `tempdir-hygiene(owned): leftovers=0`,
`foreign-regen-dir-ignored: True`, `owned-leak-detected: True`, and the
run was executed with a hostile pre-existing `/tmp/k16_regen_FOREIGN_PROBE`
directory held in the global temp root for the entire suite duration (your
reproduction scenario) — no false-red. All D44/D46/D47 controls, the
read-only real-generator integration control, and both canonical-unchanged
assertions are unchanged and green.
