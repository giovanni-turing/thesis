---
from: reviewer
ts: 2026-07-28T05:23:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V14-eda-d-img-vs-req-scatter
---

## Deep Inspection Report — Image 4: `figuras/eda/eda_d_img_vs_req_scatter.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 230 (`\includegraphics[width=0.62\linewidth]{figuras/eda/eda_d_img_vs_req_scatter}`)
- **Target Print Width**: $0.62 \times 426.8\text{ pt} = \mathbf{264.6\text{ pt}}$ ($3.68\text{ inches}$)
- **PDF Canvas Size**: $705.1 \times 420.0\text{ pt}$ ($9.79 \times 5.83\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{264.6}{705.1} = \mathbf{0.375\times}$
- **Effective Font Sizes on Page**:
  - Axis tick labels / Colorbar ticks (nominal 8 pt): **3.00 pt** (severely sub-scale; illegible on A4)
  - Figure title / $R^2$ annotation (nominal 11 pt): **4.13 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Stream**: Reversed stream `s / segami` ("images / s") due to rotated matrix (instance of V02).
- **Corrupted PUA Glyphs**:
  - `U+E09D` in colorbar label `30` (intended `+`)
  - `U+E081` in `requests / s 1-min windows)` (intended `(`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: X-axis `requests / s (1-min windows)` (0--7), Y-axis `images / s` (0--350). Linear scatter/hexbin grid.
- **Colorbar**: Hexbin density count (0--30+). Sequential single-hue colormap maintains grayscale monotonicity.
- **Caption Alignment**: Caption in `trace-eda.tex` ("Vision work is poorly explained by request rate...") matches $R^2 = 0.123$ regression line in plot.

### Verdict & Defect Summary (MAJOR)
Extreme canvas scale reduction (**0.375x** rendering text at **3.00 pt**), reversed Y-axis text stream, and corrupted PUA glyphs in colorbar and axis titles.

**Required Action**:
1. Re-export on a compact canvas ($\approx 265 \times 160\text{ pt}$) matching `width=0.62\linewidth` so fonts remain 8--10 pt.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer streams and PUA encodings.
