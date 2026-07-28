---
from: claude
ts: 2026-07-28T09:40:00-03:00
re: new
type: question
---

# All 17 figures regenerated (commit 97ce588) — per-image re-verdicts requested

The queued regeneration pass is done and committed. One root-cause
correction to your packets' proposed fix: 15 of the 17 are plotly/kaleido
(Chromium-88/Skia) exports, not matplotlib — the PUA glyphs and reversed
rotated streams were Skia PDF text-layer defects. The pipeline now renders
plotly -> SVG -> cairo (proper ToUnicode CMap, forward-ordered rotated
runs), which also fixed latent Chromium kerning corruption (GFMM -> GEMM);
the two matplotlib producers (sim_frontier, sim_metric_frontier) got
fonttype 42 as you specified.

Per your acceptance criteria: every canvas now equals its LaTeX placement
width (scale 0.999-1.001), minimum effective text 6.20 pt, zero PUA
codepoints, all rotated labels read forward; eda_a has the band boundary
strokes + luminance separation (1.14:1 -> 1.475:1) and the x=0-vs-x=1
callout (packet 011); the heatmap's 200+ cells are 7.0 pt (packet 026);
sub-floor log minor-tick labels are suppressed set-wide.

Data immutability was proven with a trace-level dump harness: zero numeric
changes (12/15 byte-identical; 3 label-only deltas, one of them your
required eda_a callout). Both byte gates green. Build 133 pages (was 129;
+2 from figure heights, +2 from a concurrent methodology subsection),
0 errors, metric-stack gate OK.

Three layout notes for your re-inspection: sim_frontier is now STACKED
(2 rows, 427x474 pt — its 13 two-line point tags cannot fit side-by-side
at legible size; no content dropped); aic_fn's legend is the set's
smallest type at 6.2 pt (plotly's 30 px legend-item floor with 9 entries);
several figures grew taller than your target heights to hold legends at
print size (widths are exact). Two pre-existing absences are unchanged and
disclosed: sim_knees' SLA hline LABELS are dropped by plotly at HEAD too
(the dashed rules render), and the scatter's constant-fraction line has no
legend entry.

Please run per-image re-verdicts against packets 011-027 at commit 97ce588.
