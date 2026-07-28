---
from: reviewer
ts: 2026-07-28T13:23:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 08: `figuras/sim/sim_knees.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $1.00 \times 426.8\text{ pt} = 426.8\text{ pt}$
- **PDF Canvas Size**: $427.0 \times 175.0\text{ pt}$ ($5.93 \times 2.43\text{ inches}$)
- **Placement Scale Factor**: $\frac{426.8}{427.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis labels & ticks: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Annotations (`knee s=3`): **9.0 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Both vertical axes read forward (`TTFT p99 (ms, log)` and `encoder delay p99 (ms, log)`).
- **PUA Codepoints**: **0 detected**. Colon in `burst1: saturated at s=1` clean.

### 3. Visual & Data-Ink Integrity
- **Log-Log Scales**: Both pools (`language` vs `vision`) clearly contrast saturation knee limits.
- **Disclosed Feature**: Dashed SLA reference lines render clearly.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
