---
from: reviewer
ts: 2026-07-28T13:25:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 10: `figuras/pred/pred_forecast_band.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.88 \times 426.8\text{ pt} = 375.6\text{ pt}$
- **PDF Canvas Size**: $376.0 \times 148.0\text{ pt}$ ($5.22 \times 2.06\text{ inches}$)
- **Placement Scale Factor**: $\frac{375.6}{376.0} = \mathbf{0.999\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Timestamps & Axis ticks: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Annotations (`p90 band...`): **9.0 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Stream**: Reads forward `images/s`.
- **PUA Codepoints**: **0 detected**. Timestamps `17:30`, `18:00`, ..., `22:00` render standard ASCII colons.

### 3. Visual & Data-Ink Integrity
- **Prediction Band**: Shaded `p10-p90` interval and `point forecast` line distinct over burst peak.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
