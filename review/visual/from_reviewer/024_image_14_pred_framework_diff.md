---
from: reviewer
ts: 2026-07-28T05:43:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V24-pred-framework-diff
---

## Deep Inspection Report — Image 14: `figuras/pred/pred_framework_diff.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/closedloop.tex` line 1533 (`\includegraphics[width=\linewidth]{figuras/pred/pred_framework_diff}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $1125.1 \times 420.0\text{ pt}$ ($15.63 \times 5.83\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{1125.1} = \mathbf{0.379\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Model tick labels (nominal 8 pt): **3.03 pt** (severely sub-scale; unreadable on paper)
  - Subpanel titles / Bar numbers (nominal 10 pt): **3.79 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Panel (a): `)nim-1 ,langis egami( EPAW` ("WAPE (image signal, 1-min)")
  - Panels (b/c): `)sm( 99p TFTT 3tsrub` ("burst3 TTFT p99 (ms)") (instance of V02)
- **Rotated X-axis Formatting**: Model names under panel (a) (`toto`, `timesfm`, `chronos`, `arima`, `prophet`, etc.) break into single-character vertical text wraps (`o h a it m c k pr t-w hol`) under extreme canvas compression.

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - Panel (a): WAPE error (0.0--0.6) across 9 models.
  - Panel (b): Closed-loop burst3 TTFT p99 (0--3500 ms) across conversion policies.
  - Panel (c): Online fidelity comparison (live runtime vs offline twin) with SLA 1000 ms threshold line.
- **Series & Legend**: 3-category model grouping (`foundation`, `classical`, `Dynamo-shipped*`) and 2-category fidelity bars. Group colors pass contrast check.
- **Caption Alignment**: Caption in `closedloop.tex` ("Accuracy does not explain the verdict...") aligns with 3-panel progression from accuracy to closed-loop.

### Verdict & Defect Summary (MAJOR)
Extreme canvas width ($1125\text{ pt}$ $\to$ **0.379x** reduction producing **3.03 pt** labels on paper), vertical X-axis label text wrapping corruption, and reversed Y-axis text streams across all three panels.

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 160\text{ pt}$) matching `width=\linewidth` to keep text 8--10 pt on paper and fix vertical label wrapping.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix reversed Y-axis streams.
