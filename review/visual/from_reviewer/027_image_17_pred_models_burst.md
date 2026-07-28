---
from: reviewer
ts: 2026-07-28T05:46:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V27-pred-models-burst
---

## Deep Inspection Report — Image 17: `figuras/pred/pred_models_burst.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/apendice.tex` line 471 (`\includegraphics[width=0.88\linewidth]{figuras/pred/pred_models_burst}`)
- **Target Print Width**: $0.88 \times 426.8\text{ pt} = \mathbf{375.6\text{ pt}}$ ($5.22\text{ inches}$)
- **PDF Canvas Size**: $990 \times 390.0\text{ pt}$ ($13.75 \times 5.42\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{375.6}{990} = \mathbf{0.379\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Timestamps / Legend labels (nominal 8 pt): **3.03 pt** (severely sub-scale; below 6 pt limit)
  - Figure title (nominal 11 pt): **4.17 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Stream**: Reversed stream `)snib nim-1 s/segami` ("images/s (1-min bins)") (instance of V02).
- **Corrupted PUA Glyphs** (13 occurrences):
  - `U+E081` / `U+E082` in parentheticals `(1-min bins)` and `(UTC)`
  - `U+E092` in all 8 timestamp colons (`0000`, `0300`, ..., `2100`, intended `:`)
  - `U+E088` in ISO date hyphens `20241021` (intended `-`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: X-axis UTC timestamps (`2024-10-21 (UTC)` 00:00--21:00), Y-axis `images/s (1-min bins)` (0--350). Linear grid.
- **Series & Legend**: 4 series (`observed`, `TimesFM`, `Chronos-2`, `Toto-2`). Model lines run tightly coincident during peak; distinct dash/dot patterns preserve line identity in grayscale.
- **Caption Alignment**: Caption in `apendice.tex` ("Three foundation models trace nearly coincident paths...") accurately describes the 3-model alignment over the burst peak.

### Verdict & Defect Summary (MAJOR)
Severe canvas overscaling (**0.379x** factor rendering text at **3.03 pt** on paper), reversed Y-axis text stream, and 13 corrupted PUA glyphs across colons, hyphens, and parentheticals.

**Required Action**:
1. Re-export on a compact canvas ($\approx 376 \times 148\text{ pt}$) matching `width=0.88\linewidth` to preserve 8--10 pt fonts on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer extraction and PUA timestamp/date glyphs.
