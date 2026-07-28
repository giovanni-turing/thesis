---
from: reviewer
ts: 2026-07-28T05:35:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V16-eda-q-multires
---

## Deep Inspection Report — Image 6: `figuras/eda/eda_q_multires.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 327 (`\includegraphics[width=0.88\linewidth]{figuras/eda/eda_q_multires}`)
- **Target Print Width**: $0.88 \times 426.8\text{ pt} = \mathbf{375.6\text{ pt}}$ ($5.22\text{ inches}$)
- **PDF Canvas Size**: $884.9 \times 390.0\text{ pt}$ ($12.29 \times 5.42\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{375.6}{884.9} = \mathbf{0.424\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Tick numbers (nominal 8 pt): **3.39 pt** (sub-6 pt legibility threshold)
  - Subpanel titles (nominal 10 pt): **4.24 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.42 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Streams**: Both vertical axis labels are reversed:
  - Left panel: `etar fo ²VC` ("CV² of rate")
  - Right panel: `kaep s1 / kaep devresbo` ("observed peak / 1s peak") (instance of V02)
- **PUA Glyphs**: None detected in this specific file.

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**:
  - Left panel: Log-log scale for $CV^2$ vs window (1--3600 s).
  - Right panel: Linear percentage (0%--100%) vs log window (1--3600 s).
- **Series & Legend**: 4 modalities (`requests`, `images`, `ctx`, `gen`). Color palette and line styles are distinguishable in grayscale.
- **Caption Alignment**: Caption in `trace-eda.tex` ("Images are the burstiest signal...") matches the multiresolution attenuation curves.

### Verdict & Defect Summary (MAJOR)
Severe canvas overscaling (**0.424x** reduction producing **3.39 pt** text on paper) and reversed vertical Y-axis text streams on both subpanels.

**Required Action**:
1. Re-export on a compact canvas ($\approx 376 \times 165\text{ pt}$) to preserve 8--10 pt readable typography.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix vector text extraction on rotated Y-axes.
