---
from: reviewer
ts: 2026-07-28T05:12:00-03:00
re: new
type: finding
thread: V03-figure-canvas-scale-discrepancy
---

## MAJOR: Canvas width and font scale inconsistency across thesis figure family

Rendered evidence:
- Page size inspection via `pdfinfo` across `figuras/`:
  - `figuras/sim/sim_metric_frontier.pdf` (newest, print-safe baseline): **734.4 x 309.6 pt** (10.2 x 4.3 inches).
  - `figuras/sim/sim_frontier.pdf`: **971.3 x 532.1 pt** (13.5 x 7.4 inches).
  - `figuras/sim/sim_knees.pdf`: **1020.0 x 420.0 pt** (14.2 x 5.8 inches).
  - `figuras/sim/sim_burst_queue.pdf`: **1020.0 x 510.0 pt** (14.2 x 7.1 inches).
  - `figuras/pred/pred_framework_diff.pdf`: **1125.1 x 420.0 pt** (15.6 x 5.8 inches).

Defect analysis:
The newer `sim_metric_frontier.pdf` uses a compact 734 pt canvas designed for standard thesis text width (~426--450 pt in LaTeX), requiring only a ~0.6x scale factor. In contrast, older figures (`sim_knees`, `sim_burst_queue`, `pred_framework_diff`) were exported on oversized 1020--1125 pt canvases (up to 15.6 inches wide). When LaTeX scales these older figures down with `\includegraphics[width=\textwidth]`, they undergo extreme reduction (0.41x--0.44x scale factor).
As a result:
- Nominal 8 pt fonts in `sim_knees` and `sim_burst_queue` shrink to **3.3--3.5 pt** on the printed A4 page (sub-6pt illegibility threshold).
- Nominal 1.0 pt lines shrink to **0.41 pt** (hairline thickness), creating visual inconsistency with `sim_metric_frontier.pdf`.

Proposed fix:
Standardize all figure export scripts (`make_figure.py`) to the target canvas size (e.g. 6.5 x 3.5 inches / ~468 x 252 pt) matching LaTeX `\textwidth` so font sizes (8--10 pt) and line weights (1.0--1.5 pt) remain uniform and readable at 1.0x scale.
