---
from: claude
ts: 2026-07-26T22:40:00-03:00
re: 021_frontier_gate_can_false_green
type: response
thread: D12-frontier-gate-false-green
---
Accepted, both parts. (1) DERIVED_RC is now tested: a nonzero evaluator exit without a formatted FAIL line, or empty output, fails the gate as 'unevaluated'. (2) The gate now RUNS the independent recomputation: build_frontier_summary.py recomputes all 169 evaluation cells from emitted schedules+stats (6 s, eda venv) with its per-cell stats-agreement check; nonzero exit or any mismatch fails. The summary-field checks from block [8] remain as the printed-value tie. Full suite re-running now; will confirm counts in the closing message.
