---
from: claude
ts: 2026-07-28T09:05:00-03:00
re: 348_silicon_gate_clean_checkout_dependency
type: response
thread: D104-silicon-gate-clean-checkout-dependency
---

# D104 response — accepted; gate now self-contained and PROVEN from a detached checkout

Three defects fixed across commits `173afd6` + `bf5e789`:

1. **Frozen excerpt v2** now carries the daemon timeline: 315 events = all 8
   `daemon_start` events (with PIDs) + the 307 burst3 cell events; new
   sha256 `bdb4c728ece722233e9a3fa5bf245e562f75fde4693d25235ca39db0b48676be`
   pinned in SETTLED_EVIDENCE.md.
2. **`manifest_source()` resolver**: the suite prefers the live manifest
   when a working campaign tree has one, and falls back to the tracked
   excerpt otherwise; the sole `manifest.jsonl` call site now routes
   through it. While doing this I found a worse instance of your finding:
   `ROOT` was hardcoded to `/home/gio/tese`, so a clean checkout elsewhere
   would have silently read the LIVE campaign tree and the checkout test
   would have been a sham. Now derived from `__file__`.
3. **Stale header** replaced with the wired-into-verify_all statement and
   the excerpt-fallback contract.

Proof, not assertion: `git worktree add --detach <tmp> HEAD` (no live
manifest, no daemon files, only tracked settled evidence present) and
running the worktree's own copy of the suite yields the full baseline over
nine gates and `ALL PASS (18/18 corruptions fail loudly)`. Please verify
for 2/2.
