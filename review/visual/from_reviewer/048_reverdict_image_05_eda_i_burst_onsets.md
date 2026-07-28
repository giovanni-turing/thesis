---
from: reviewer
ts: 2026-07-28T13:20:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 05: `figuras/eda/eda_i_burst_onsets.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.82 \times 426.8\text{ pt} = 350.0\text{ pt}$
- **PDF Canvas Size**: $350.0 \times 165.0\text{ pt}$ ($4.86 \times 2.29\text{ inches}$)
- **Placement Scale Factor**: $\frac{350.0}{350.0} = \mathbf{1.000\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Axis labels & ticks: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Annotations (`p10 2 min, p50 6.5 min`): **9.0 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis Text Streams**: Both vertical axes read forward (`fraction of episodes` and `peak images/s`).
- **PUA Codepoints**: **0 detected**. Parentheticals `(18 episodes)` clean.

### 3. Visual & Data-Ink Integrity
- **Log X-axes**: Onset time 1--100 min log scales on both panels.
- **Data Series**: ECDF line and scatter plot points uncollided and distinct in grayscale.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
