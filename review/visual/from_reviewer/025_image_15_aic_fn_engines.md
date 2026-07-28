---
from: reviewer
ts: 2026-07-28T05:44:00-03:00
re: 007_per_image_deep_order
type: finding
thread: V25-aic-fn-engines
---

## Deep Inspection Report — Image 15: `figuras/aic/aic_fn_engines.pdf`

### 1. Canvas & Print-Scale Measurements
- **LaTeX Inclusion**: `tex/apendice.tex` line 406 (`\includegraphics[width=0.92\linewidth]{figuras/aic/aic_fn_engines}`)
- **Target Print Width**: $0.92 \times 426.8\text{ pt} = \mathbf{392.7\text{ pt}}$ ($5.45\text{ inches}$)
- **PDF Canvas Size**: $1080 \times 420.0\text{ pt}$ ($15.00 \times 5.83\text{ inches}$)
- **Effective Print Scale Factor**: $\frac{392.7}{1080} = \mathbf{0.364\times}$
- **Effective Font Sizes on Page**:
  - Tick numbers / Engine labels (nominal 8 pt): **2.91 pt** (severely sub-scale; below 6 pt limit)
  - Subpanel headings / Legend (nominal 10 pt): **3.64 pt**
- **Effective Line Weight**: 1.0 pt stroke $\to$ **0.36 pt** (hairline)

### 2. Text-Layer Extraction (`pdftotext`)
- **Y-axis & Vertical Text Streams**: All vertical text streams are reversed:
  - Left panel Y-axis: `)gol ,sm( drawrof TiV` ("ViT forward (ms, log)")
  - Right panel Y-axis: `CIA / enigne` ("engine / AIC")
  - Vertical annotation: `pac OFIF` ("FIFO cap") (instance of V02)
- **Corrupted PUA Glyphs**:
  - `U+E0A1` in `12.8%` (intended `+` or `±`)
  - `U+E088` in `HFSDPA` and `HFFA2` (intended `-`) (instance of V01)

### 3. Data-Ink, Color & Legend Verification
- **Axes & Units**: Log-log scale for ViT forward latency vs $N$ (1--512) on panel (a), ratio vs $N$ (0.9--1.7) on panel (b).
- **Engine Comparison**: 5 execution engines (`AIC composition`, `HF-SDPA`, `HF-FA2`, `vLLM-flash`, `torch.compile`). Colors and marker styles pass contrast check.
- **Caption Alignment**: Caption in `apendice.tex` ("Encoder cost across execution engines...") matches multi-engine scaling curves and $N \le 64$ vLLM tracking.

### Verdict & Defect Summary (MAJOR)
Extreme canvas overscaling (**0.364x** factor rendering text at **2.91 pt** on paper), reversed Y-axis and vertical annotation text streams, and corrupted PUA hyphens/symbols.

**Required Action**:
1. Re-export on a compact canvas ($\approx 393 \times 153\text{ pt}$) matching `width=0.92\linewidth` to preserve 8--10 pt fonts on paper.
2. Enable Type 42 fonts (`pdf.fonttype=42`) to fix text layer extraction and PUA hyphens.
