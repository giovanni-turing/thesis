---
from: reviewer
ts: 2026-07-27T04:06:46-03:00
re: new
type: finding
thread: D49-k16-selftest-temp-namespace
---

## MEDIUM — A5b scans every process's global K16 temporary directory

The isolation suite checks temp hygiene by listing the entire process-global
`tempfile.gettempdir()` and failing on any `k16_regen_*`
(`provenance/loader/selftest_d44.py:149-152`). A legitimate concurrent K16
invocation owns such a directory for roughly one regeneration interval, so
the new continuously runnable A5b gate can false-fail even when this suite
cleaned every directory it created.

This is reproducible by holding an unrelated matching directory in the global
temp root while the suite reaches probe 8: all functional controls pass, but
`tempdir-hygiene` reports a leftover and the suite exits nonzero. The namespace
overlap is real; concurrent `d48_iso_*` directories were observed during
independent runs.

Required closure: force or record this process's loader regeneration
directories under its outer `TD`, and assert only those owned paths. Add a
concurrency control proving that an unrelated global `k16_regen_*` directory
does not affect the result, while an owned leaked directory still fails. Do
not weaken cleanup detection by accepting all global leftovers.
