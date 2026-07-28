---
from: reviewer
ts: 2026-07-28T13:26:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 11: `figuras/pred/pred_horizon_wape.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.86 \times 426.8\text{ pt} = 367.0\text{ pt}$
- **PDF Canvas Size**: $367.0 \times 252.0\text{ pt}$ ($5.10 \times 3.50\text{ inches}$)
- **Placement Scale Factor**: $\frac{367.0}{367.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis ticks & Legend: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel titles: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Reads forward `WAPE (%)` across all 4 subpanels.
- **PUA Codepoints**: **0 detected**. Parentheticals in units clean.

### 3. Visual & Data-Ink Integrity
- **2x2 Grid**: 4 modalities (`requests`, `images`, `context tokens`, `generated tokens`). Foundation model min-max envelope distinct against baselines.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
