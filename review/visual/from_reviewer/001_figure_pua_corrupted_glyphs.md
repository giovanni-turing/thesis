---
from: reviewer
ts: 2026-07-28T05:10:00-03:00
re: new
type: finding
thread: V01-figure-pua-corrupted-glyphs
---

## MAJOR: Unmapped Private Use Area (PUA) font glyphs across 14 PDF figures

Rendered evidence:
- Rasterization: `pdftoppm -png -r 130` on `figuras/**/*.pdf`
- Text layer inspection: `pdftotext` extracted PUA Unicode codepoints (U+E000--U+F8FF) across 14 figures in `figuras/`:
  - `figuras/aic/aic_fn.pdf`: 12 PUA characters (`\ue09f`)
  - `figuras/aic/aic_fn_engines.pdf`: 3 PUA characters (`\ue0a1`, `\ue088`)
  - `figuras/eda/eda_a_context_vs_numimages.pdf`: 2 PUA characters
  - `figuras/eda/eda_c_seven_day_signals.pdf`: 1 PUA character (`\ue081`)
  - `figuras/eda/eda_d_acf.pdf`: 1 PUA character (`\ue09f`)
  - `figuras/eda/eda_d_img_vs_req_scatter.pdf`: 2 PUA characters
  - `figuras/eda/eda_e_arrival_process.pdf`: 5 PUA characters
  - `figuras/eda/eda_eval_windows.pdf`: 1 PUA character
  - `figuras/eda/eda_i_burst_onsets.pdf`: 1 PUA character
  - `figuras/eda/eda_l_request_clusters.pdf`: 9 PUA characters
  - `figuras/pred/pred_forecast_band.pdf`: 11 PUA characters
  - `figuras/pred/pred_horizon_wape.pdf`: 4 PUA characters
  - `figuras/pred/pred_models_burst.pdf`: 13 PUA characters
  - `figuras/sim/sim_burst_queue.pdf`: 1 PUA character

Defect analysis:
Matplotlib font subsetting during PDF export assigned Private Use Area codepoints to custom math/parenthetical symbols (e.g., `(1-min windows)` rendered with `\ue081`). This corrupts the text layer of vector PDF figures, causing search, selection, copy-paste, screen readers, and certain PDF renderers to display missing/blank glyph boxes or garbled Unicode characters.

Proposed fix:
Re-export figures with `plt.rcParams['pdf.fonttype'] = 42` (Type 42 TrueType embedding) and standard font encodings in Matplotlib scripts.
