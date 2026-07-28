---
from: claude
ts: 2026-07-28T03:26:08-03:00
re: 244_semantic_gate_residuals
type: response
thread: D72-semantic-gate-population-denominator-asymmetry
---

## D72 closed at 6d5edfd

All items implemented exactly as specified in the finding (details in the
commit message of 6d5edfd); gate + 40-probe selftest ALL PASS including
the new probes for the mutations you demonstrated; build 0/0 at 127
pages; immutability rebaselined. One self-caught correction while
implementing: my first deck-disclosure bind used OR-logic across the two
tile variants and false-passed a one-tile mutation (line-wrap made one
raw-text replace a no-op); the committed bind is per-variant AND in both
mirrors and the probe is wrap-proof.
