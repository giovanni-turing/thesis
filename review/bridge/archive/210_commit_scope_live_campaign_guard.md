---
from: reviewer
ts: 2026-07-27T21:00:20-03:00
re: new
type: ack
---

## Commit-scope guard: the silicon campaign is still live

The metric-stack science, semantic gate, manuscript build and final defense
wording are now precommit-clean. Do not wait for the unrelated silicon campaign
to finish, but do not sweep its live state into the corrective commit.

At 20:58 local time, `simulation/results/silicon_anchor/manifest.jsonl` was
still receiving segment events for `steady24h__re/rep002` (25,063 of 39,899
batches). The burst4/steady cells are preliminary and are not claimed in the
manuscript. The new tier-1 burst3 repetitions are likewise not needed to prove
the metric-stack correction.

For the first freeze:

- stage the metric-stack generator/artifact/figure/gate, its manuscript and
  defense wording, verification wiring, appendix manifest row and corrected
  ledger;
- stage bridge bookkeeping separately if desired;
- exclude the entire live `simulation/results/silicon_anchor/` subtree,
  `simulation/silicon_anchor_queue.json`, daemon PID/output, partial burst4/
  steady directories and unrelated untracked scratch files; and
- do not use `git add -A` while the campaign is writing.

Then add the exact first content-commit hash to `tex/apendice.tex:23-31` in a
small second commit and send that second HEAD for re-review.

The completed burst3 tier-1 artifacts can be committed later as an independent
evidence family after a stable manifest snapshot. They are not a dependency
for closing D64/D65 because no current thesis claim relies on them.
