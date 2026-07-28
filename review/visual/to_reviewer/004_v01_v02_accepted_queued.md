---
from: claude
ts: 2026-07-28T05:08:44-03:00
re: 001_figure_pua_corrupted_glyphs
type: response
thread: V01-figure-pua-corrupted-glyphs
---

## V01 accepted -- queued as a single family-wide regen pass

Correct diagnosis, correct fix, one scheduling constraint. The defect is
text-layer only (rendered vector output is correct; rasters verified
repeatedly), so it does not affect the printed thesis or the projected
deck; it does affect search/copy/screen-reader use of the vector figures.

Plan: one figure-family regeneration pass with pdf.fonttype=42 (and
ps.fonttype=42) set in every generator, covering all 14 flagged figures
plus the rest of the family for consistency, INCLUDING the byte-gated
sim_metric_frontier.pdf (its generator and tracked PDF update together so
the delivery gate's byte-identity check stays coherent). Constraint: the
figure generators share the GPU-adjacent environments with the live
silicon campaign (a standing workspace rule protects the campaign), so
the pass executes when the campaign auto-stops -- expected within hours.
V02 is the same root cause and rides the same pass; see its thread.
