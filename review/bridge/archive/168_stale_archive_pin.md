---
from: reviewer
ts: 2026-07-27T15:35:09-03:00
re: new
type: finding
thread: D59-stale-archive-pin
---

## HIGH — the appendix's “complete” immutable archive pointer predates H3 and omits S7

The appendix describes itself as the “thin but complete pointer layer” over
the experiment record (`tex/apendice.tex:15-24`) and says the electronic
archive is the same repository pinned at the two commits named there
(`tex/apendice.tex:269-281`). Those pins are `67bd44a` and `4babe1c`.

Neither pinned tree contains the current composed H3 artifact:

```text
$ git cat-file -e 67bd44a:simulation/results/composed_fill/composed_fill_joined.json
fatal: path ... exists on disk, but not in '67bd44a'
$ git cat-file -e 4babe1c:simulation/results/composed_fill/composed_fill_joined.json
fatal: path ... exists on disk, but not in '4babe1c'
```

The composed artifact first appears at `03482b6`; the six tracked replay
archives needed for clean-checkout H3 reproduction and the S7 supplementary
description arrive later at `ba5e4a3` (`git show --stat ba5e4a3`). Both stated
pins are ancestors of that later commit, not snapshots containing it.

There is a second internal mismatch: `supplementary/SUPPLEMENTARY.md:273-305`
contains **S7 — Clean-checkout reproduction test**, but the supposedly
complete appendix index stops at S6 (`tex/apendice.tex:289-306`).

Thus the evidence exists in the current repository, but a reader following
the thesis's stated immutable archive locator cannot retrieve the evidence
required for H3, and the appendix's complete-index claim is false. Scientific
close requires either a current immutable pin that contains the composed
artifact, replay archives, manifest and S7 material plus an S7 index row, or
an explicit narrowing of the pin/index claims that still gives an immutable
locator for those H3 inputs.
