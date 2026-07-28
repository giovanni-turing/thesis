---
from: reviewer
ts: 2026-07-28T05:22:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V13-eda-eval-windows
---

## Deep Inspection Report — Image 3: `figuras/eda/eda_eval_windows.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 178 (`\includegraphics[width=0.95\linewidth]{figuras/eda/eda_eval_windows}`)
- **Target Print Width**: $0.95 \times 426.8\text{ pt} = \mathbf{405.5\text{ pt}}$ ($5.63\text{ inches}$)
- **PDF Canvas Size**: $884.9 \times 330.0\text{ pt}$ ($12.29 \times 4.58\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{405.5}{884.9} = \mathbf{0.458\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Burst callouts `b1`--`b6` (nominal 8 pt): **3.66 pt** (sub-6 pt legibility threshold)
  - Figure title (nominal 11 pt): **5.04 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.46 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Stream**: Reversed stream `)naem nim-1 s/segami` ("images/s (1-min mean)") due to rotated text matrix (instance of V02).
- **Corrupted PUA Glyphs**: `U+E081` in `)naem nim-1 s/segami` (intended `(`) (instance of V01).

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: X-axis UTC timestamps (Oct 16--22, 2024), Y-axis `images / s (1-min mean)` (0--400). Linear scales.
- **Annotations**: Stratified evaluation windows highlighted and labeled (`b1` through `b6`, `calm day`, `forecast context (never graded)`). Distinct shaded region boxes pass grayscale check.
- **Caption Alignment**: Caption in `trace-eda.tex` ("Stratified evaluation harness...") accurately describes the 6 burst episodes and context span.

### Verdict & Defect Summary (MAJOR)
Canvas overscaling (**0.458x** reduction producing **3.66 pt** episode annotations and tick labels on paper) combined with reversed y-axis text stream and PUA glyph corruption.

**Required Action**:
1. Re-export on a compact canvas ($\approx 405 \times 150\text{ pt}$) to maintain 8--10 pt font sizes on paper.
2. Enable `pdf.fonttype=42` to fix vector text extraction and PUA encoding.
