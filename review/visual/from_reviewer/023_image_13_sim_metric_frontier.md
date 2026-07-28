---
from: reviewer
ts: 2026-07-28T05:42:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V23-sim-metric-frontier
---

## Deep Inspection Report — Image 13: `figuras/sim/sim_metric_frontier.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/closedloop.tex` line 842 (`\includegraphics[width=0.82\linewidth]{figuras/sim/sim_metric_frontier}`)
- **Target Print Width**: $0.82 \times 426.8\text{ pt} = \mathbf{350.0\text{ pt}}$ ($4.86\text{ inches}$)
- **PDF Canvas Size**: $734.4 \times 309.6\text{ pt}$ ($10.20 \times 4.30\text{ inches}$) (Newest figure idiom)
- **Effective Print Scale Factor**: $\frac{350.0}{734.4} = \mathbf{0.477\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Tick numbers (nominal 9 pt): **4.29 pt** (near legibility floor)
  - Panel titles (nominal 10 pt): **4.77 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.48 pt**

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Clean & un-reversed (`total encoder delay` and `excess mass over 1 s`).
- **PUA Glyphs**: 0 detected. Clean Type 1 / TrueType vector text layer.

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - Shared X-axis: `provisioned worker-hours, aggregate span (log)` (300--4,000 h).
  - Left Y-axis (linear): `total encoder delay (10^3 request s)` (24--34).
  - Right Y-axis (log): `excess mass over 1 s (request s, log)` (10^2--10^4).
- **Markers & Styling**: High-contrast, print-safe markers (`forecast p90`, `reactive`, `oracle`, `static C=8`, warm floor family `M2`..`M32`). Grayscale distinguishable.
- **Caption Alignment**: Caption in `closedloop.tex` ("Cost versus delay burden, aggregate span...") matches panel (a) total delay mass and panel (b) log excess mass curves.

### Verdict & Defect Summary (MINOR / CANVAS COMPACTION)
Demonstrates clean text encodings (V01/V02-free) and print-safe markers. Canvas width ($734\text{ pt}$) is significantly tighter than older 1020 pt figures, but still undergoes 0.477x reduction when placed at `0.82\linewidth`.

**Required Action**:
Compact canvas from $734\text{ pt}$ to $\approx 350\text{ pt}$ matching target placement width so 8--10 pt labels render as 8--10 pt on paper without scale reduction.
