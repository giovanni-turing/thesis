---
from: claude
ts: 2026-07-28T05:16:54-03:00
re: 002_first_pass_order
type: ack
---

## Standing order upgrade: one image per iteration, exhaustively

Author directive. Change your working mode from family-level sweeps to
per-image deep dives: each iteration takes exactly ONE artifact (one
figure PDF or one deck slide) and exhausts it before moving on.

Per-image protocol:
1. Full raster at working resolution AND at print/projection scale (for
   figures: the actual \includegraphics scale factor from the tex --
   grep the width argument and compute effective pt sizes; for slides:
   1920x1080 plus a 50% downscale to simulate a weak projector).
2. Zoomed crops of every text element, legend, tick region, and marker
   cluster -- verify each is legible at effective size, uncollided,
   correctly colored against the design system, and (for figures)
   grayscale-distinguishable.
3. Text-layer extraction (pdftotext) -- PUA/reversed-stream defects per
   your V01/V02 method, per image.
4. Data-ink sanity: axes labeled with units, scales marked (log/linear),
   every series identifiable without color, caption cross-checked
   against what the image actually shows (caption CONTENT mismatches
   route to the scientific bridge, but flag them).
5. Consistency check against the family idiom (fonts, palette, line
   weights, canvas class) with pt-level measurements.
6. File ONE message per image: either its finding set (V-threads as
   usual, severity-ranked) or an explicit CLEAN verdict with the
   evidence listed -- clean verdicts matter as much as findings; the
   author wants per-image proof of inspection, not silence.

Order of work: the 14 thesis-figure PDFs the manuscript includes (grep
tex/ for includegraphics to enumerate exactly; do them in chapter
order), then the 15 deck slides, then defense-qa.pdf pages with visual
content. Keep the 30-finding cap per batch but CLEAN verdicts do not
count against it. Continue until every included image has its verdict
on record.
