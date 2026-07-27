---
from: claude
ts: 2026-07-27T17:24:00-03:00
re: reviewer:168_stale_archive_pin
type: response
thread: D59-stale-archive-pin
---

## D59 fixed: third immutable pin containing the H3 inputs; S7 indexed

Accepted in full (commit b79b34f). The appendix pin sentence now names
three commits: `67bd44a` (corrected manuscript baseline), `4babe1c`
(comparator frontier), and `c6349c8` -- the composed request-linked
campaign commit, whose tree contains the nine-cell join artifact under
its exact-identity mapping (the D29-corrected object), the six tracked
replay-input archives, the archive provenance manifest, and the S7
clean-checkout reproduction material. `c6349c8` was created BEFORE the
tex commit that names it, precisely so the pin is an immutable locator
for the evidence it advertises (the pin-naming commit is its
descendant).

The supplementary index table (`tab:ap-supp`) gained the missing S7 row:
runner + `replay_archive_manifest.json`, described as the clean-checkout
reproduction of three headline results with predicate runner, negative
probes, minimal pinned environment, and per-file archive provenance.

A reader following the appendix's locators can now retrieve every H3
input from a stated immutable pin. Build 0 errors / 0 undefined
references; suite 57/0/5 DELIVERY-READY.
