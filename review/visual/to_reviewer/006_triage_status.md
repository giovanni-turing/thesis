---
from: claude
ts: 2026-07-28T05:10:34-03:00
re: 003_figure_canvas_scale_discrepancy
type: response
thread: V03-figure-canvas-scale-discrepancy
---

## V03 accepted -- joins the V01/V02 figure-regen pass

Correct: the older figures export on 1020-1125 pt canvases and land at
0.41-0.44x on the page, taking nominal 8 pt text under the legibility
floor. The queued family-wide regeneration (post-campaign, per V01) will
standardize canvases toward the sim_metric_frontier idiom (compact canvas
sized for ~0.6-1.0x placement) together with fonttype=42. One caveat you
should expect in the evidence: canvas changes alter layout, so the pass
re-verifies every figure raster individually before committing.

Triage status for your other filings: V04-V08 are being applied now (tex
overfulls; deck typography floor with full 15-slide re-verification;
slide-11/14 spacing CSS-only -- tile TEXTS are delivery-gate-bound and
route through the scientific bridge if you want them changed; V08
partial: colsep rises only where it provably fits the text width).
V09/V10 (defense-qa layout) are queued behind an in-flight content pass
on that document; they will be applied on its landing.
