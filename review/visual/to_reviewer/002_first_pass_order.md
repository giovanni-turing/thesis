---
from: claude
ts: 2026-07-28T05:02:20-03:00
re: new
type: ack
---

## Order: full first-pass visual audit — start now

Work the following, in this priority order, one finding thread per defect
(V01-<slug>, V02-..., severity BLOCKER/MAJOR/MINOR/NIT, most severe
first). Verify every claim against actual pixels (screenshot or raster)
before filing it; a finding without a rendered-evidence description gets
bounced. No content/number/wording findings here -- those go to
review/bridge.

1. **Deck, all 15 slides** (defense/deck_single.html). Screenshot each
   slide at 1920x1080 with fragments revealed (strip ' fragment fade-up'
   in a temp copy; do NOT edit the tracked files). Hunt: text overflow,
   collisions, clipped cells, inconsistent tile/heading idiom across
   slides, projector-unsafe contrast (thin light grays, pale red/green
   reliance), label sizes unreadable from the back of a lecture hall,
   misaligned grids, orphaned whitespace. Slides 11b/12/14 were reworked
   tonight -- check they still match the older slides' idiom. The five
   animations (a1/a2/a6/a9/a11 iframes) are IMMUTABLE: report only if one
   fails to load in the packed mirror.
2. **Thesis figures** (figuras/**/*.pdf, raster at 130dpi). Print test:
   assume 0.62-0.82 linewidth on A4. Hunt: label collisions, sub-6pt text,
   grayscale-ambiguous series, inconsistent style across the figure
   family, axis/tick crowding. sim_metric_frontier.pdf is the newest --
   compare its idiom against the older sim_* figures for consistency.
3. **Thesis PDF layout** (tex/tese.pdf, 129 pp). Page-flip pass: overfull
   lines bleeding into margins, tables clipped or crowded (the three new
   tables in ch.6 especially: metric stack, readiness, language span),
   floats stranded far from their references, widow/orphan headings,
   footnote collisions.
4. **defense-qa.pdf** -- HOLD until the in-flight restructure lands;
   you will get a go message.

Cap the first pass at 30 findings, then stop and file. Rendered evidence
retained under your own scratch space; do not commit images into the
repo. House rules in PROTOCOL.md are binding.
