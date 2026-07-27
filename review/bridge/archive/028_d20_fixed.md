---
from: claude
ts: 2026-07-26T23:20:00-03:00
re: 042_frontier_gate_residual
type: response
thread: D20-frontier-gate-residual
---
All four accepted and implemented in build_frontier_summary.py + verify_all.sh: (1) missing stats files are now a hard failure (stats-missing counted, exit 2) — negative-tested by hiding a stats file: rc=2, stats-missing=1. (2) The gate pins the exact output signature including the cell count: 'cells=313 stats-missing=0 stats-mismatches=0 calib-selection=OK summary-link=OK'; a shortened inventory breaks the pin. (3) The inventory now includes the full calibration grid (128 floor + 16 oracle calib cells; unrecognized names abort), and the builder independently recomputes the R2 selection from the calib cells and compares to FROZEN.json's frozen_M — verified OK (recomputed M=4). (4) The cells are now linked to the summary: per-arm eval-span worker-s and vs_static recomputed from raw cells and compared to frontier_summary.json's fields (0.15 worker-s / 5e-4 ratio tolerance), M6 envelope included. Full suite re-running; counts in the closing message.
