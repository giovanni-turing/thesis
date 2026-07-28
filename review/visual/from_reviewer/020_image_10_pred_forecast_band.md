---
from: reviewer
ts: 2026-07-28T05:39:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V20-pred-forecast-band
---

## Deep Inspection Report — Image 10: `figuras/pred/pred_forecast_band.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/predictors.tex` line 195 (`\includegraphics[width=0.88\linewidth]{figuras/pred/pred_forecast_band}`)
- **Target Print Width**: $0.88 \times 426.8\text{ pt} = \mathbf{375.6\text{ pt}}$ ($5.22\text{ inches}$)
- **PDF Canvas Size**: $990 \times 390.0\text{ pt}$ ($13.75 \times 5.42\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{375.6}{990} = \mathbf{0.379\times}$
- **Effective Font Sizes on Page**:
  - Tick timestamps / Axis labels (nominal 8 pt): **3.03 pt** (severely sub-scale; unreadable on paper)
  - Legend & Annotations (nominal 10 pt): **3.79 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Stream**: Reversed stream `s/segami` ("images/s") (instance of V02).
- **Corrupted PUA Glyphs** (11 occurrences):
  - `U+E0A3` in `honest 90% coverage` (intended `≈`)
  - `U+E092` in all 10 X-axis timestamps (`1730`, `1800`, ..., `2200`, intended `:`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: X-axis UTC timestamps (Oct 21, 2024, 17:30--22:00), Y-axis `images / s` (0--350). Linear grid.
- **Series & Legend**: `p10–p90 band` (shaded interval), `point forecast`, `naive`, `observed` (solid black line). Shaded prediction band distinguishable in grayscale.
- **Caption Alignment**: Caption in `predictors.tex` ("Chronos-2 (cov): a calibrated 12-step forecast...") aligns with plotted forecast trajectory.

### Verdict & Defect Summary (MAJOR)
Severe canvas overscaling (**0.379x** factor rendering text at **3.03 pt**), reversed Y-axis text stream, and 11 corrupted PUA glyphs across timestamp colons and math symbols.

**Required Action**:
1. Re-export on a compact canvas ($\approx 376 \times 148\text{ pt}$) matching `width=0.88\linewidth` to preserve 8--10 pt fonts on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix reversed text streams and PUA timestamp colons.
