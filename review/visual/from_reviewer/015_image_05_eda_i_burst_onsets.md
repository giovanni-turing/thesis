---
from: reviewer
ts: 2026-07-28T05:34:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V15-eda-i-burst-onsets
---

## Deep Inspection Report — Image 5: `figuras/eda/eda_i_burst_onsets.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 267 (`\includegraphics[width=0.82\linewidth]{figuras/eda/eda_i_burst_onsets}`)
- **Target Print Width**: $0.82 \times 426.8\text{ pt} = \mathbf{350.0\text{ pt}}$ ($4.86\text{ inches}$)
- **PDF Canvas Size**: $810 \times 360\text{ pt}$ ($11.25 \times 5.00\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{350.0}{810} = \mathbf{0.432\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Axis labels (nominal 8 pt): **3.46 pt** (sub-6 pt legibility threshold)
  - Subpanel headings (nominal 10 pt): **4.32 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.43 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Left panel: `sedosipe fo noitcarf` ("fraction of episodes")
  - Right panel: `s/segami kaep` ("peak images/s") (instance of V02)
- **Corrupted PUA Glyphs**: `U+E081` in `(18 episodes)` (intended `(`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: Logarithmic X-axes (`onset time, baseline→peak (min)` across 1--100 min).
  - Left Y-axis: Linear `fraction of episodes` (0.0--1.0).
  - Right Y-axis: Linear `peak images/s` (220--380).
- **Annotations**: `Onset time ECDF — p10 2 min, p50 6.5 min (18 episodes)` callout and `Fast-onset bursts are not small` header.
- **Caption Alignment**: Caption in `trace-eda.tex` ("Burst onsets are short...") aligns with ECDF percentiles and peak scatter trend.

### Verdict & Defect Summary (MAJOR)
Suffers from canvas overscaling (**0.432x** factor rendering text at **3.46 pt**), reversed Y-axis text streams on both panels, and corrupted PUA parenthetical glyphs.

**Required Action**:
1. Re-export on a compact canvas ($\approx 350 \times 155\text{ pt}$) so fonts remain 8--10 pt on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix reversed streams and PUA encodings.
