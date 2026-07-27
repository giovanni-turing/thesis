---
from: reviewer
ts: 2026-07-27T16:42:07-03:00
re: new
type: finding
thread: D62-supplementary-stale-closure
---

## HIGH — final closure sweep finds stale result and false pin scope in the electronic appendix

The built `.tex` manuscript, D60/D61 evidence, archive bytes, and delivery gate
are green, but the electronic appendix still contradicts the final result and
its own Git history in four current statements.

### 1. The retired four-of-five result survives in the supplement

`supplementary/SUPPLEMENTARY.md:158-163` says the preserved result includes
“the 4-of-5 tie.” The current, denominator-disciplined result is an exact tie
on three of five evaluation windows (burst1/4/5) plus the non-independent
aggregate view, with calm within 5 ms (`tex/closedloop.tex:29-31,879-883,
1398-1400`). The supplementary phrase must carry that same population.

### 2. The manuscript-baseline claim excludes current evidence

`supplementary/SUPPLEMENTARY.md:18` says every claim in the shortened thesis
must trace to evidence present at or before `67bd44a`. The live manuscript now
cites the forecast-free G1 halves (`tex/closedloop.tex:803-805`), but:

```text
$ git cat-file -e 67bd44a:defense/anim/data/g1_runs/burst2_enc_static_C8.jsonl.zst
fatal: path ... does not exist in '67bd44a'
$ git log --diff-filter=A --format='%h %s' -- <the four G1 .zst paths>
947005c D30/D31 round 2: view derivation, archived g1 halves, precise tie population
```

`67bd44a` is accurately the rollback baseline for the shortening campaign, not
an upper bound on later evidence. The universal sentence must distinguish
those roles and defer later evidence to its later immutable pins.

### 3. The claimed S1–S6 checkout cannot contain the index it promises

`supplementary/SUPPLEMENTARY.md:21-22` says everything in S1–S6 is reachable at
`4babe1c`, yet both of these fail:

```text
$ git cat-file -e 4babe1c:supplementary/SUPPLEMENTARY.md
fatal: path ... does not exist in '4babe1c'
$ git cat-file -e 4babe1c:supplementary/manifest_full.md
fatal: path ... does not exist in '4babe1c'
```

Those supplementary files first appear at `3c56418`. Add an accurate
structural-supplement pin (or narrow the claim to the older evidence paths)
rather than representing `4babe1c` as a checkout of the later S-index.

### 4. The self-description stops at S6

`supplementary/SUPPLEMENTARY.md:142` calls this an “S1–S6” index, while S7 is
live at `:273-291`. It must say S1–S7.

These are text/provenance closure defects only; no scientific number or data
artifact needs to change. The fact that `verify_all.sh --thesis` currently
passes 49/0/4 shows this exact supplementary surface is not covered by the
automated manuscript gate.
