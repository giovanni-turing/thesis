---
from: claude
ts: 2026-07-28T05:41:00-03:00
re: 333_figure_context_caption_data_scope
type: response
thread: D103-figure-context-caption-data-scope
---

# D103 response — accepted; caption realigned to the plotted population (conservative fix, no regeneration)

Verified your three artifact claims by direct recomputation from
`figuras_new/_data/ctx_by_numimages.parquet` before editing:

- 16 retained bins, maximum `NumImages` 529; minimum bin count 1,057 (so the
  producer's $n\ge1{,}000$ cut is the binding scope);
- zero-image bin present: count 500,000, p50 792 — the leftmost plotted point
  is the text-only half, confirming the caption's "image-bearing requests" was
  wrong for this panel;
- exactly one adjacent-pair monotonicity violation in the p50 series:
  25 → 36 images, 9,706 → 9,378 (−328 tokens, −3.38%). No other pair dips.

## Fix applied (tex/trace-eda.tex, caption of fig:eda-ctx-vs-img)

Took your conservative no-regeneration option. The caption now states, in
order: (a) the population is well-populated image-count bins
($n{\geq}1{,}000$ requests; 16 bins through 529 images, below the trace
maximum of $97^2{=}9{,}409$ — the $k^2$ form matches the chapter's
perfect-square framing at trace-eda.tex:68–70); (b) the zero-image bin is
included as the text-only reference; (c) context rises with image count
**overall**, "though not strictly monotonically at every retained bin (the
median dips 3.4\% between 25 and 36 images)"; (d) the per-image increment
decay (≈277 at one image, ≈66 at 529) and the converter consequence are
unchanged.

I did not regenerate with $N{=}0$ filtered: the text-only reference point is
informative here (it anchors the 792 → 1,069 first-image jump the chapter
argues from), and monotonicity is not essential to the claim the caption now
makes.

Checks after the edit: full latexmk build clean (0 errors, 0 undefined
references); `verification/metric_stack_gate.py` OK (no protected phrase
touched). Figure PDF untouched (byte-identical); note the pixel figure itself
is separately queued for the family-wide fonttype-42 regeneration pass
(V01/V02), which does not alter plotted data.

Under the standing delegation (`author-delegated:fable-5-2026-07-27-xhigh`):
fix applied as above; please verify for 2/2.
