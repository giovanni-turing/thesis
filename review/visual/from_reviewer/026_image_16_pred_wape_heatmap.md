---
from: reviewer
ts: 2026-07-28T05:45:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V26-pred-wape-heatmap
---

## Deep Inspection Report — Image 16: `figuras/pred/pred_wape_heatmap.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/apendice.tex` line 456 (`\includegraphics[width=\linewidth]{figuras/pred/pred_wape_heatmap}`)
- **Target Print Width**: $1.00 \times 426.8\text{ pt} = \mathbf{426.8\text{ pt}}$ ($5.93\text{ inches}$)
- **PDF Canvas Size**: $1125.1 \times 390.0\text{ pt}$ ($15.63 \times 5.42\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{426.8}{1125.1} = \mathbf{0.379\times}$
- **Effective Font Sizes on Page**:
  - Heatmap cell numbers (nominal 7 pt): **2.65 pt** (severely sub-scale; unreadable without magnification)
  - Row / Column headers (nominal 8--9 pt): **3.03 pt** (below 6 pt legibility limit)
- **Effective Line Weight**: 1.0 pt cell borders $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Text Layer**: Vector text extraction produces 395 tokens (matrix WAPE values + model names).
- **PUA Glyphs**: 0 detected. Vector text layer is uncorrupted.

### 3. Data-Ink, Color & Legend Verification
- **Grid Layout**: 9 model rows $\times$ 12 column blocks (4 modalities $\times$ 3 time resolutions).
- **Coloring**: Single-hue sequential heatmap. Cell numbers are bolded for column-best values; contrast passes grayscale inspection.
- **Caption Alignment**: Caption in `apendice.tex` ("Foundation models are the column-best...") matches heatmap values.

### Verdict & Defect Summary (MAJOR)
Extreme canvas width ($1125\text{ pt}$) results in a **0.379x** reduction factor that shrinks all 200+ matrix cell numbers down to **2.65 pt**, rendering the heatmap table illegible on printed A4 paper.

**Required Action**:
1. Re-export on a compact canvas ($\approx 427 \times 148\text{ pt}$) matching `width=\linewidth` so cell numbers render at $\ge 7\text{ pt}$ on paper.
