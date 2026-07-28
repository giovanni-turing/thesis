---
from: reviewer
ts: 2026-07-28T13:24:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 09: `figuras/sim/sim_burst_queue.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $1.00 \times 426.8\text{ pt} = 426.8\text{ pt}$
- **PDF Canvas Size**: $427.0 \times 213.0\text{ pt}$ ($5.93 \times 2.96\text{ inches}$)
- **Placement Scale Factor**: $\frac{426.8}{427.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis labels & ticks: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel headings: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Both vertical axes read forward (`offered images/s` and `queued images`).
- **PUA Codepoints**: **0 detected**. `(1-min mean)` renders standard ASCII parentheses.

### 3. Visual & Data-Ink Integrity
- **Dual Time Series**: Top panel (offered load) and bottom panel (queued backlog) share 0--8 h timeline.
- **Peak Callout**: `peak 4,701 images queued` callout box rendered with red fill contrast.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
