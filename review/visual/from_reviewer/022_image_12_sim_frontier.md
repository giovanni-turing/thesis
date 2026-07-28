---
from: reviewer
ts: 2026-07-28T05:41:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V22-sim-frontier
---

## Deep Inspection Report — Image 12: `figuras/sim/sim_frontier.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/closedloop.tex` line 589 (`\includegraphics[width=\linewidth]{figuras/sim/sim_frontier}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $971.3 \times 532.1\text{ pt}$ ($13.49 \times 7.39\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{971.3} = \mathbf{0.439\times}$
- **Effective Font Sizes on Page**:
  - Point callouts / Pass-fail labels (nominal 8 pt): **3.51 pt** (sub-6 pt legibility threshold)
  - Subpanel titles (nominal 10 pt): **4.39 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.44 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Un-reversed (`worst-window encoder-delay p99 (ms)` reads correctly).
- **PUA Glyphs**: None detected in this file.

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: Log-log scales on both subpanels.
  - X-axes: `provisioned worker-time, 5.60-day evaluation span (Mworker-s)` (1--16).
  - Y-axes: `worst-window encoder-delay p99 (ms)` (500--20000).
- **Subpanels**:
  - Panel A: Shipped mechanics (§8.2 frontier).
  - Panel B: Readiness repairs (warm-pool symmetric vs strict near-symmetric).
- **Markers & Legend**: Filled vs hollow markers denote 5-window pass vs failure. Dashed red gate line at 1000 ms.
- **Caption Alignment**: Caption in `closedloop.tex` ("§8.2 encoder-pool frontier...") matches 2-panel trade-off frontier curves.

### Verdict & Defect Summary (MAJOR)
Suffers from canvas overscaling (**0.439x** factor rendering point callouts and pass-fail text at **3.51 pt** on paper).

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 234\text{ pt}$) matching `width=\linewidth` to keep text 8--10 pt on paper.
