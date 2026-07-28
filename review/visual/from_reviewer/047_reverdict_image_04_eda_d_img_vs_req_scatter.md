---
from: reviewer
ts: 2026-07-28T13:19:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 04: `figuras/eda/eda_d_img_vs_req_scatter.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.62 \times 426.8\text{ pt} = 264.6\text{ pt}$
- **PDF Canvas Size**: $265.0 \times 160.0\text{ pt}$ ($3.68 \times 2.22\text{ inches}$)
- **Placement Scale Factor**: $\frac{264.6}{265.0} = \mathbf{0.999\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Ticks & Colorbar labels: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Annotations ($R^2 = 0.12$): **9.0 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Stream**: Reads forward `images / s`.
- **PUA Codepoints**: **0 detected**. Colorbar label `30+` renders standard plus sign.

### 3. Visual & Data-Ink Integrity
- **Hexbin Density Grid**: Sequential colormap passes grayscale contrast check. $R^2 = 0.12$ regression line clearly superimposed.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
