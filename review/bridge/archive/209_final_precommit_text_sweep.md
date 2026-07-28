---
from: reviewer
ts: 2026-07-27T20:53:36-03:00
re: new
type: ack
---

## Final precommit sweep: manuscript clear; defense and pin remain

The latest manuscript/gate state is favorable:

- total delay is consistently a leading post-hoc synthesis, not the frozen
  endpoint;
- every-window p99 is consistently retained as the validity gate;
- the common-warm reactive-favorable/post-hoc and unexpanded-forecast
  design-space limitation is explicit;
- the readiness table now fits (the previous 74.39-pt overflow is gone);
- the fresh 129-page build has no undefined references;
- the corrected semantic gate and all nine negative probes pass; and
- the ledger's canonical correction block now supersedes the old strict-
  dominance wording.

Three precommit items remain.

### 1. Defense slide contradicts the frozen gate

`defense/reveal/index.html:455-458` and
`defense/deck_single.html:856-859` say “Same verdict with no burst windows”
and that bursts “are not how it is graded.” The same slide later correctly
calls windows the validity gate.

Use: **“Same resource-time conclusion in the span-level synthesis”** and say
that the span-level totals establish magnitude while the frozen per-window
grid remains the anti-masking success gate.

### 2. Defense provenance/readiness disclosure is false

`defense/reveal/index.html:623-626` and
`defense/deck_single.html:1023-1027` say:

- cost uses “symmetric warm-up accounting”; and
- every number re-derives from the provenance DB.

The displayed matrix is the shipped mixed-readiness pair, not symmetric
accounting. The live DB has zero `metric_stack` rows and zero new
`simulation/results/silicon_anchor/` ingests. Say instead:

> costs are separated by declared readiness mechanics; DB-backed where
> ingested, otherwise re-derived from tracked raw artifacts and gated
> generators.

Update the matching defense ledger entry at
`progress/results-ledger.md:3101-3107`: the slide shows total delay, not excess
mass, and windows remain the gate rather than only a masking check.

### 3. Exact wording and immutable pin

- Change `tex/closedloop.tex:29-31` from generic “tail latencies tie exactly”
  to “window p99 values tie exactly”; the distributions separate above p99.
- The final metric-stack/gate content is still uncommitted and
  `tex/apendice.tex:23-31` cannot yet name it. Use a two-step freeze:
  commit the corrective content, then add that exact content commit to the
  appendix pin list in a small follow-up commit. Send the follow-up HEAD for
  re-review.

Readability note, not a scientific blocker for this close: the readiness
result remains detailed at `tex/closedloop.tex:595-692`, then tabulated at
`:763-790`. That is acceptable for this low-risk pass; the threshold/survival
detail at `:694-724` is the clean Phase-2 appendix relocation candidate. Do
not start that larger move before freezing the present correction.
