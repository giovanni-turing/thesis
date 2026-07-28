---
from: reviewer
ts: 2026-07-28T05:40:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V21-pred-horizon-wape
---

## Deep Inspection Report — Image 11: `figuras/pred/pred_horizon_wape.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/predictors.tex` line 243 (`\includegraphics[width=0.86\linewidth]{figuras/pred/pred_horizon_wape}`)
- **Target Print Width**: $0.86 \times 426.8\text{ pt} = \mathbf{367.0\text{ pt}}$ ($5.10\text{ inches}$)
- **PDF Canvas Size**: $810 \times 540.0\text{ pt}$ ($11.25 \times 7.50\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{367.0}{810} = \mathbf{0.453\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Tick numbers (nominal 8 pt): **3.62 pt** (sub-6 pt legibility threshold)
  - Subpanel titles / Legend (nominal 10 pt): **4.53 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.45 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Reversed streams `% EPAW` ("WAPE (%)") across subpanel vertical axes (instance of V02).
- **Corrupted PUA Glyphs**: `U+E081` and `U+E082` in parenthetical units `%` (intended `(` and `)`) (instance of V01).

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: 2x2 matrix (`requests`, `images`, `context tokens`, `generated tokens`).
  - X-axes: `horizon step h` (1, 3, 6, 9, 12).
  - Y-axes: `WAPE (%)` (0--80%).
- **Series & Legend**: `foundation models (min–max)` (shaded envelope), `naive`, `EWMA`, `Holt–Winters`. Shaded envelope and dashed baseline markers maintain contrast in grayscale.
- **Caption Alignment**: Caption in `predictors.tex` ("Point-forecast error across the horizon...") matches the 2x2 horizon accuracy curves.

### Verdict & Defect Summary (MAJOR)
Canvas overscaling (**0.453x** factor rendering text at **3.62 pt**), reversed Y-axis text streams across all 4 subpanels, and PUA parenthetical glyph corruption.

**Required Action**:
1. Re-export on a compact canvas ($\approx 367 \times 245\text{ pt}$) matching `width=0.86\linewidth` to preserve 8--10 pt fonts on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix reversed streams and PUA parenthetical glyphs.
