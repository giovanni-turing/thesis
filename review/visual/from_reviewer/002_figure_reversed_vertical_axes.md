---
from: reviewer
ts: 2026-07-28T05:11:00-03:00
re: new
type: finding
thread: V02-figure-reversed-vertical-axes
---

## MAJOR: Reversed vertical axis text streams in Matplotlib PDF figure exports

Rendered evidence:
- Inspection of PDF stream text extractions across `figuras/**/*.pdf`:
  - `figuras/sim/sim_burst_queue.pdf`: Y-axis label text stream reads `s/segami dereffo` ("offered images/s") and `segami deueuq` ("queued images").
  - `figuras/aic/aic_fn.pdf`: Y-axis label text stream reads `)sm( egami rep emit lenrek` ("kernel time per image (ms)").
  - `figuras/eda/eda_c_seven_day_signals.pdf`: Y-axis labels read `s/stseuqer` ("requests/s") and `s/segami` ("images/s").
  - `figuras/eda/eda_i_burst_onsets.pdf`: Y-axis label reads `s/segami kaep` ("peak images/s").
  - `figuras/pred/pred_framework_diff.pdf`: Y-axis label reads `)nim-1 ,langis egami( EPAW` ("WAPE (image signal, 1-min)").
  - `figuras/pred/pred_models_burst.pdf`: Y-axis label reads `)snib nim-1\ue081 s/segami`.

Defect analysis:
When Matplotlib exports rotated y-axis titles (90-degree rotation) to PDF without explicit text-direction controls, it outputs reversed string streams governed by negative transformation matrices. While visual vector rendering handles the matrix flip, the underlying PDF text layer becomes back-to-front, breaking accessibility, PDF text search, and PDF-to-image/vector converters.

Proposed fix:
Configure Matplotlib PDF backend with standard orientation transformations or use `ps.fonttype = 42` / `pdf.fonttype = 42` with explicit text alignment settings.
