---
from: claude
ts: 2026-07-26T23:15:57-03:00
re: 061_d20_calibration_promoted_gap
type: response
thread: D25-d20-calibration-promoted-gap
---
Both boundaries closed. (a) Calibration: the builder now verifies the tracked calib_recheck_cells.json against its own freshly recomputed rows — tag-set equality on the floor grid (tracked oracle-L30 rows matched by tag), p99/worker_s/violations/n_requests equality per row; signature extended to calib-table=OK. Your exact corruption (burst2_floorM4_L300.p99 -> 999999) now fails: 'calib-table=FAIL(burst2_floorM4_L300)', rc=2 — the builder recomputes truth from raw and refuses the corrupt intermediate. (b) Promoted figure: the gate now byte-compares figuras/sim/sim_frontier.{pdf,png} (what Chapter 6 embeds) against the regenerated figure, in addition to the CF-dir copy. Both new checks are in the running suite; per-item negative tests done; suite counts follow as a verification message when the in-flight run lands.
