---
from: reviewer
ts: 2026-07-28T05:38:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V19-sim-burst-queue
---

## Deep Inspection Report — Image 9: `figuras/sim/sim_burst_queue.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/metodologia.tex` line 561 (`\includegraphics[width=\linewidth]{figuras/sim/sim_burst_queue}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $1020 \times 510.0\text{ pt}$ ($14.17 \times 7.08\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{1020} = \mathbf{0.418\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Axis labels (nominal 8 pt): **3.35 pt** (sub-6 pt legibility threshold)
  - Subpanel headings / Queue callouts (nominal 10 pt): **4.18 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.42 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Top panel: `s/segami dereffo` ("offered images/s")
  - Bottom panel: `segami deueuq` ("queued images") (instance of V02)
- **Corrupted PUA Glyphs**: `U+E081` in `(1-min mean)` (intended `(`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - X-axis: `hours into the episode window` (0--8 h).
  - Top Y-axis: Linear `offered images/s (1-min mean)` (0--300).
  - Bottom Y-axis: Linear `queued images` (0--5000).
- **Annotations**: Peak callout `peak 4,701 images queued` at $t \approx 3.2\text{ h}$. Red fill region emphasizes queue buildup; grayscale threshold passes.
- **Caption Alignment**: Caption in `metodologia.tex` ("A 29%-utilized vision pool...") matches peak backlog callout and mean utilization text.

### Verdict & Defect Summary (MAJOR)
Suffers from canvas overscaling (**0.418x** factor rendering text at **3.35 pt**), reversed Y-axis text streams on both subpanels, and PUA glyph corruption in axis parentheticals.

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 213\text{ pt}$) matching `width=\linewidth` to keep text 8--10 pt on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix reversed streams and PUA parenthetical glyphs.
