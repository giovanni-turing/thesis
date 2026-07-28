---
from: reviewer
ts: 2026-07-28T13:27:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 12: `figuras/sim/sim_frontier.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $1.00 \times 426.8\text{ pt} = 426.8\text{ pt}$
- **PDF Canvas Size**: $427.0 \times 474.0\text{ pt}$ ($5.93 \times 6.58\text{ inches}$) (Stacked 2-row layout)
- **Placement Scale Factor**: $\frac{426.8}{427.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Point callout tags (13 two-line labels): **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel headings: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Un-reversed (`worst-window encoder-delay p99 (ms)` reads forward).
- **PUA Codepoints**: **0 detected** (`pdf.fonttype=42` enabled).

### 3. Visual & Data-Ink Integrity
- **Stacked Layout Verification**: 2 vertically stacked panels (Panel A: shipped mechanics; Panel B: readiness repairs). Vertical stacking accommodates all 13 point tags without horizontal overlap.
- **Pass/Fail Markers**: Filled vs hollow markers and red dashed 1000 ms SLA line clearly distinguishable.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
