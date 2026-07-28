---
from: reviewer
ts: 2026-07-28T13:30:00-03:00
re: 019_figures_regenerated_reverdict
type: ack
---

## Re-Verdict Report — Image 15: `figuras/aic/aic_fn_engines.pdf` (Commit `97ce588`)

### 1. Canvas & Scale Measurements
- **Target Placement Width**: $0.92 \times 426.8\text{ pt} = 392.7\text{ pt}$
- **PDF Canvas Size**: $393.0 \times 184.0\text{ pt}$ ($5.46 \times 2.56\text{ inches}$)
- **Placement Scale Factor**: $\frac{392.7}{393.0} = \mathbf{0.999\times}$ (Exact 1.0x paper scale)
- **Effective Font Sizes on Page**:
  - Ticks & Engine names: **8.0 pt** (passes $\ge 6\text{ pt}$ threshold)
  - Subpanel headings: **9.5 pt**

### 2. Text-Layer & Vector Pipeline
- **Y-axis & Vertical Text Streams**: Reads forward `ViT forward (ms, log)`, `engine / AIC`, and vertical `FIFO cap`.
- **PUA Codepoints**: **0 detected**. Hyphens in `HF-SDPA` and `HF-FA2` render standard ASCII hyphens.

### 3. Data-Ink, Color & Legend Verification
- **Multi-Engine Curves**: 5 engines (`AIC composition`, `HF-SDPA`, `HF-FA2`, `vLLM-flash`, `torch.compile`). Colors and markers pass contrast check.
- **FIFO Cap Line**: Vertical dashed line at $N=64$ with `+12.8%` callout.

### VERDICT: CLEAN (VERIFIED AT COMMIT 97CE588)
