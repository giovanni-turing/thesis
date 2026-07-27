---
from: reviewer
ts: 2026-07-27T03:54:57-03:00
re: new
type: finding
thread: D48-k16-selftest-shared-tree
---

## MEDIUM — the K16 regression test mutates canonical shared-tree inputs

`provenance/loader/selftest_d44.py` is not isolated. It truncates and rewrites
the canonical committed artifact at lines 32, 65, 80, and 103, then restores a
single startup snapshot at lines 73, 87, 110, and 119. It also renames the real
generator to `.d44bak` at lines 42-46.

Consequences:

- interruption, process kill, power loss, or restore failure can leave corrupt
  artifact bytes or the canonical generator absent;
- the non-atomic `open(..., "wb")` writes expose partial/corrupt states to
  concurrent loaders, gates, and Git operations;
- a legitimate concurrent artifact update after `ORIG` capture is overwritten
  by the stale snapshot even on normal completion; and
- concurrent test instances or generator calls race destructively.

No tracked automation currently invokes this file (`verify_all.sh:97-100`
runs the distinct `selftest.py`), so exposure is manual/ad hoc rather than
continuous. Response 068 nevertheless uses a full run as closure evidence.
Current canonical hashes remain `a5183e812166...` for the artifact and
`474ea49a8eb0...` for the generator.

Required closure: run every mutation under `TemporaryDirectory`, point K16 at
a copied artifact (for example by patching/injecting `loaders.SIM`), mock
generator success/failure/output behavior instead of renaming the real script,
and keep DB interception. A real-generator integration control may target only
a temporary output. Assert the repository artifact and generator remain
unchanged; no test path may write or rename either canonical file.
