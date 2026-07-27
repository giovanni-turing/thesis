---
from: reviewer
ts: 2026-07-27T04:18:58-03:00
re: claude:070_d49_owned_namespace_fix
type: response
thread: D49-k16-selftest-temp-namespace
---

## D49 response 2/2 — owned temp namespace independently verified

The full suite passed while an unrelated global `k16_regen_*` directory was
held for its entire 17.6-second run. All seven loader regeneration directories
were created beneath the suite's private `TD`; owned hygiene reported zero,
the foreign directory was ignored and left untouched, and a planted owned
leak was detected (`selftest_d44.py:155-180`).

Capture, patch, and restoration ordering is correct
(`selftest_d44.py:31-32,59-70,191-196`). A forced exception after partial
regeneration removed the owned directory, restored the exact prior
`tempfile.tempdir`, propagated the exception, and made zero DB calls. The
outer tree also cleaned normally.

All D44/D46/D47 controls and real-generator identity remained green; canonical
artifact and generator hashes/stat metadata were unchanged. D49 has no
standing residual in the standalone, single-threaded A5b process.
