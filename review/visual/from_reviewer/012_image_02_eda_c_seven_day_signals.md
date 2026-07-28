---
from: reviewer
ts: 2026-07-28T05:21:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V12-eda-c-seven-day-signals
---

## Deep Inspection Report — Image 2: `figuras/eda/eda_c_seven_day_signals.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 167 (`\includegraphics[width=0.86\linewidth]{figuras/eda/eda_c_seven_day_signals}`)
- **Target Print Width**: $0.86 \times 426.8\text{ pt} = \mathbf{367.0\text{ pt}}$ ($5.10\text{ inches}$)
- **PDF Canvas Size**: $780 \times 464.9\text{ pt}$ ($10.83 \times 6.46\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{367.0}{780} = \mathbf{0.471\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Tick numbers (nominal 8 pt): **3.76 pt** (sub-6 pt legibility threshold)
  - Subpanel titles (nominal 10 pt): **4.71 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.47 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Top panel: `s/stseuqer` ("requests/s")
  - Bottom panel: `s/segami` ("images/s") (instance of V02)
- **Corrupted PUA Glyphs**: `U+E081` in `requests / s 1-min windows)` (intended `(`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - Top panel: Language-pool requests/s (0--8), 1-min windows.
  - Bottom panel: Vision-pool images/s (0--300), showing `p99 = 224 img/s` callout.
  - X-axis: UTC timestamps across 7-day span (Oct 16--22, 2024).
- **Caption Alignment**: Caption in `trace-eda.tex` ("One shared clock: vision demand is far spikier...") accurately reflects the 2-panel comparison.

### Verdict & Defect Summary (MAJOR)
Suffers from sub-scale font shrinking (**3.76 pt** at 0.471x scale), reversed vertical text streams on both y-axes, and PUA glyph corruption in panel sub-headings.

**Required Action**:
1. Re-export on a $\approx 367 \times 220\text{ pt}$ canvas to preserve 8--10 pt font legibility.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer streams and PUA encodings.
