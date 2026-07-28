---
from: reviewer
ts: 2026-07-28T05:37:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V18-sim-knees
---

## Deep Inspection Report — Image 8: `figuras/sim/sim_knees.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/metodologia.tex` line 496 (`\includegraphics[width=\linewidth]{figuras/sim/sim_knees}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $1020 \times 420.0\text{ pt}$ ($14.17 \times 5.83\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{1020} = \mathbf{0.418\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Axis labels (nominal 8 pt): **3.35 pt** (sub-6 pt legibility threshold)
  - Subpanel titles / Annotations (nominal 10 pt): **4.18 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.42 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Left panel: `)gol ,sm( 99p TFTT` ("TTFT p99 (ms, log)")
  - Right panel: `)gol ,sm( 99p yaled redocne` ("encoder delay p99 (ms, log)") (instance of V02)
- **Corrupted PUA Glyphs**: `U+E092` in `burst1 saturated at s=1` (intended `:`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: Log-log scales on both subpanels.
  - Left panel: `offered load (req/s, log)` vs `TTFT p99 (ms, log)` (100--10M ms).
  - Right panel: `offered load (img/s, log)` vs `encoder delay p99 (ms, log)` (100--10M ms).
- **Annotations & Knee Markers**: `knee s=3`, `head2k: knee s=32 (censored)`, `burst1: saturated at s=1`.
- **Caption Alignment**: Caption in `metodologia.tex` ("Saturation knees per pool...") accurately describes the per-pool capacity limits.

### Verdict & Defect Summary (MAJOR)
Suffers from canvas overscaling (**0.418x** factor rendering text at **3.35 pt**), reversed Y-axis text streams on both subpanels, and PUA colon glyph corruption in annotation text.

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 175\text{ pt}$) matching `width=\linewidth` to keep font sizes 8--10 pt.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer extraction and PUA colon glyphs.
