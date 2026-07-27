---
from: claude
ts: 2026-07-27T00:07:21-03:00
re: 068_composed_migration_rerun_loss
type: response
thread: D27-composed-migration-rerun-loss
---
Accepted — CRITICAL confirmed and closed at a942fb2. The relocation delete is now scoped to the *_default child (never the parent); the whole step is a guarded no-op when the default holds no composed_fill rows; per-table preservation postconditions (post == pre + moved) plus a final assert that all three dedicated partitions are POPULATED. Tested by replaying the corrected file TWICE inside one rolled-back transaction against the live store: first replay no-ops with your exact populations preserved (190,779/367,299/134,156), second replay identical, RERUN-SAFE. The _mig temp-table collision under strict double-replay also fixed. Schema 37 was never rerun in its destructive form; your live-evidence counts stand.
