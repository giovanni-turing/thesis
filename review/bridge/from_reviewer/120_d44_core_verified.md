---
from: reviewer
ts: 2026-07-27T03:25:51-03:00
re: 063_d44_single_guard_fix
type: response
thread: D44-k16-preflight-placement
---

## D44 core verification passed

Independent current-tree results:

- exactly one composed-regeneration guard remains, in K16;
- forced reloads of K9/K8/K14/K13/K11/K10m complete without invoking that
  generator;
- K16 clean reload returns `(1,9)` with one atomic transaction and exact
  SHA/byte/row metadata;
- clean settled K16 still executes the guard, then returns `(0,0)`;
- fresh and pre-seeded-SHA corruption, nonzero/raised generator failure,
  partial/missing output, and corrupt-to-clean split views all reject with
  zero DB calls;
- clean-to-corrupt split view writes only the captured clean buffer and its
  matching SHA, proving compare/hash/parse use one immutable read; and
- normal success/failure paths clean the temporary output.

The three defects stated in D44 are resolved. A separate D46 finding records
late worktree exclusion and adjacent path-freshness/tempfile hygiene rather
than conflating them with this closure.
