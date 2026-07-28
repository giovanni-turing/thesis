---
from: reviewer
ts: 2026-07-28T15:27:00-03:00
re: 188_d116_escalation
type: verification
thread: D116-stale-tracking-provenance
---

# D116 — Terminal verification

The recognized delegated ruling in `190_adjudication_d116_d117.md` is
**CLOSED-FIXED**.

`tex/tese.tex` and `progress/results-ledger.md` now state that the upstream
ignore pattern caused `colinha.pdf` to be skipped during the initial
vendoring add, after which it was force-added and is currently tracked. The
ledger also records the complete probe lineage
`33 -> 50 -> 52 -> 55`: 22 additions this round (`17 + 2 + 3`), with 55
current mutation probes plus three harness checks.

No D116 provenance residual remains.
