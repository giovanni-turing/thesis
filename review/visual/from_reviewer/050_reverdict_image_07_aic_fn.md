---
from: reviewer
ts: 2026-07-28T13:22:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 07: `figuras/aic/aic_fn.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $1.00 \times 426.8\text{ pt} = 426.8\text{ pt}$
- **PDF Canvas Size**: $427.0 \times 214.0\text{ pt}$ ($5.93 \times 2.97\text{ inches}$)
- **Placement Scale Factor**: $\frac{426.8}{427.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Legend items (9 entries): **6.2 pt** (smallest type in set, passes $\ge 6.2\text{ pt}$ floor)
  - Ticks & Ratio annotations: **7.5--8.0 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Both vertical axes read forward (`forward latency (ms, log)` and `kernel time per image (ms)`).
- **PUA Codepoints**: **0 detected**. Multipliers `1.43×`, `1.48×`, `1.62×` render standard `×` characters.
- **Kerning**: `GEMM` kerning clean (no Skia `GFMM` corruption).

### 3. Visual & Data-Ink Integrity
- **Kernel Breakdown Bar Stack**: 7 categories with distinct hatch patterns for non-AIC kernels.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
