---
from: reviewer
ts: 2026-07-28T05:36:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V17-aic-fn
---

## Deep Inspection Report — Image 7: `figuras/aic/aic_fn.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/metodologia.tex` line 243 (`\includegraphics[width=\linewidth]{figuras/aic/aic_fn}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $1080 \times 420.0\text{ pt}$ ($15.00 \times 5.83\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{1080} = \mathbf{0.395\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Ratio annotations $1.36\times$--$1.62\times$ (nominal 8 pt): **3.16 pt** (severely sub-scale; below 6 pt legibility limit)
  - Subpanel titles / Legends (nominal 10 pt): **3.95 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.40 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Left panel: `)gol ,sm( ycnetal drawrof` ("forward latency (ms, log)")
  - Right panel: `)sm( egami rep emit lenrek` ("kernel time per image (ms)") (instance of V02)
- **Corrupted PUA Glyphs**:
  - `U+E09F` in all multiplier annotations (`1.43`, `1.48`, `1.62`, etc., intended `×`)
  - `U+E081` / `U+E082` in legend `measured HF eager, 550` (intended `(` and `)`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - Left panel: Log-log scale for forward latency vs $N$ (1--128).
  - Right panel: Linear per-image kernel breakdown (ms/img) for $N=1$ and $N=64$.
- **Stack Breakdown**: 7 kernel categories (GEMM, attention, unfused elementwise, DeepStack gather, patch-embed conv, norm, other). Hatched patterns for non-AIC kernels maintain grayscale legibility.
- **Caption Alignment**: Caption in `metodologia.tex` ("AIC anchors the encoder cost...") aligns with kernel breakdown panel.

### Verdict & Defect Summary (MAJOR)
Severe canvas overscaling (**0.395x** reduction producing **3.16 pt** text on paper), reversed Y-axis text streams, and 12 corrupted PUA glyphs across numerical annotations.

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 166\text{ pt}$) matching `width=\linewidth` to keep fonts 8--10 pt.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer extraction and PUA multiplier glyphs.
