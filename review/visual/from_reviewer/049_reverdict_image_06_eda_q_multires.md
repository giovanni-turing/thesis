---
from: reviewer
ts: 2026-07-28T13:21:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 06: `figuras/eda/eda_q_multires.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.88 \times 426.8\text{ pt} = 375.6\text{ pt}$
- **PDF Canvas Size**: $376.0 \times 165.0\text{ pt}$ ($5.22 \times 2.29\text{ inches}$)
- **Placement Scale Factor**: $\frac{375.6}{376.0} = \mathbf{0.999\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis labels & ticks: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel headings: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Both vertical axes read forward (`CV² of rate` and `observed peak / 1s peak`).
- **PUA Codepoints**: **0 detected**.

### 3. Visual & Data-Ink Integrity
- **Series & Legend**: 4 modalities (`requests`, `images`, `ctx`, `gen`). Marker shapes and colors pass contrast check.
- **Sub-floor minor ticks**: Minor-tick labels below floor suppressed set-wide.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
