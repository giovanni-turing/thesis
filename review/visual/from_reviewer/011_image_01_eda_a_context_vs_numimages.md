---
from: reviewer
ts: 2026-07-28T05:20:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V11-eda-a-context-vs-numimages
---

## Deep Inspection Report — Image 1: `figuras/eda/eda_a_context_vs_numimages.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/trace-eda.tex` line 83 (`\includegraphics[width=0.62\linewidth]{figuras/eda/eda_a_context_vs_numimages}`)
- **Target Print Width**: $0.62 \times 426.8\text{ pt} = \mathbf{264.6\text{ pt}}$ ($3.68\text{ inches}$)
- **PDF Canvas Size**: $690 \times 390\text{ pt}$ ($9.58 \times 5.42\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{264.6}{690} = \mathbf{0.383\times}$
- **Effective Font Sizes on Page**:
  - Axis labels / Legend (nominal 8 pt): **3.06 pt** (severely sub-scale; below the 6 pt legibility threshold)
  - Title heading (nominal 11 pt): **4.21 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.38 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis Text Stream**: Reversed stream `snekot txetnoc` ("context tokens") due to unhandled 90-degree matrix rotation (instance of V02).
- **Corrupted PUA Glyphs**:
  - `U+E0A2` in `64 tokens / image` (intended `≈`)
  - `U+E081` in `images per request NumImages)` (intended `(`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: X-axis `images per request (NumImages)` (0--500), Y-axis `context tokens` (0--40k). Linear scales.
- **Series & Legend**: 3 bands/lines (`p10–p90`, `p25–p75`, `median`). Shaded bands maintain grayscale contrast.
- **Caption Alignment**: Caption in `trace-eda.tex` ("Context tokens scale with image count...") aligns with plotted trend (~64 tokens/image slope).

### Verdict & Defect Summary (MAJOR)
This figure suffers from severe print-scale reduction (**0.383x** factor rendering text at **3.06 pt**) combined with text-layer reversal and PUA glyph corruption.

**Required Action**:
1. Re-export on a compact canvas ($\approx 265 \times 150\text{ pt}$) so 8--10 pt fonts remain 8--10 pt when placed at `width=0.62\linewidth`.
2. Apply `pdf.fonttype=42` to fix PUA glyphs and un-reverse vertical text streams.
