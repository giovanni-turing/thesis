---
from: reviewer
ts: 2026-07-28T13:28:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 13: `figuras/sim/sim_metric_frontier.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.82 \times 426.8\text{ pt} = 350.0\text{ pt}$
- **PDF Canvas Size**: $350.0 \times 172.0\text{ pt}$ ($4.86 \times 2.39\text{ inches}$) (Compacted canvas)
- **Placement Scale Factor**: $\frac{350.0}{350.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis labels & ticks: **8.5 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel titles: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Un-reversed (`total encoder delay` and `excess mass over 1 s`).
- **PUA Codepoints**: **0 detected** (`pdf.fonttype=42` enabled).

### 3. Visual & Data-Ink Integrity
- **Compact Canvas**: Canvas width compacted from $734\text{ pt} \to 350\text{ pt}$, achieving exact 1.0x scale match at `0.82\linewidth`.
- **Series Markers**: Print-safe markers (`forecast p90`, `reactive`, `oracle`, `static C=8`, warm floor series) pass grayscale contrast check.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
