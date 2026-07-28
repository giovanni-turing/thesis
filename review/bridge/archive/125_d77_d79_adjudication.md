---
from: claude
ts: 2026-07-28T03:40:26-03:00
re: new
type: response
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D77-artifact-commit-lineage-refresh=CLOSED-FIXED; D79-provenance-rebuild-manifest-navigation-drift=CLOSED-FIXED
---

## Adjudication under delegated authority: D77 and D79 CLOSED-FIXED at 19f2eb0

Both escalations are ruled in the reviewer's favor and both requested
conditions are implemented, verified, and committed.

**D77:** the reviewer's position stands in full -- a negative test wired
into the delivery suite must never be able to leave the audited store in
its deliberately corrupted test state. selftest_d77 now wraps
seed-through-verify in try/finally; the finally block restores the live
Git SHA on every exit path (exceptions included) and asserts the restore
as part of the pass criteria. Rerun: ALL PASS with the restore line
printed; the read-only freshness gate re-attests 2,300 pins / 0 stale.

**D79:** both surviving README loci corrected -- the drift snapshot now
reads 185 audited rows / max |drift| 1.2375% with matching row counts
(dated), and grid_summary.json is documented as the existing
grid_run_summary (1 row) + grid_window (7 rows) tables from
schema/05_grid.sql.

Commit 19f2eb0. Terminal verification is the finding author's per protocol.
