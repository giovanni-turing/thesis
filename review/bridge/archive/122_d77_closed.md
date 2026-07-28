---
from: claude
ts: 2026-07-28T03:37:10-03:00
re: 257_artifact_commit_lineage_stale
type: response
thread: D77-artifact-commit-lineage-refresh
---

## D77 closed at 775fd5a

All four narrow-closure items: (1) K34 special-cases artifact_commit_sha
with staged-first COALESCE (recomputed lineage refreshes; measured/config
fields keep fill-only semantics; the pass stays idempotent); (2) K34
rerun -- both rows (eda:i_burst_anatomy, eda:j_classes) advanced to
67bd44a8; (3) new verification/artifact_lineage_gate.py checks every
repo-local non-null pin against live git log -1 (2,300 pins over 1,040
tracked paths, 0 stale) via the loaders' psql transport, wired into
verify_all Gate A; (4) selftest_d77 seeds the historical 4e855370 stale
SHA, requires K34 to advance it to live, then requires the second pass
idempotent -- ALL PASS, also wired into verify_all.
