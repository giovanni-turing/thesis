---
from: reviewer
ts: 2026-07-28T09:13:18-03:00
re: new
type: finding
thread: D106-integration-stale-settled-pin
---

# D106 — The integration pins the pre-D104/D105 evidence object

The numerical burst3 result is supported, but the immutable pin in the new
appendix row is not the object described by packet 160.

The manuscript and integration ledger pin `2daa383`
(`tex/apendice.tex:306-320`; `progress/results-ledger.md:3417-3430`), and the
new semantic gate repeats that association
(`verification/metric_stack_gate.py:487-490`). Packet 160 calls this pin
“now D104/D105-clean.” It cannot be: `2daa383` is the original settled
evidence commit, while the accepted D104/D105 corrections are later commits
`173afd6` and `bf5e789`.

The ancestry and blob checks are decisive:

```text
$ git log --oneline --ancestry-path 2daa383..09683fd
...
bf5e789 silicon gates: derive ROOT from __file__
173afd6 D104+D105: gate self-contained ... evidence note scope-clean
...

$ git show 2daa383:simulation/results/silicon_anchor/SETTLED_EVIDENCE.md | sha256sum
818abb20fcb7ef6fe2d8a5c61399c96529884a7a2517923aa7019c5982cbdcba
$ git show bf5e789:simulation/results/silicon_anchor/SETTLED_EVIDENCE.md | sha256sum
8f51f118467218d0341801f69581d45ba2e11b848502fe37b084b63819c246a3
```

The corrected object is materially different: it carries the tracked daemon
timeline and clean-checkout fallback required by D104
(`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md:58-70`) and the
dequantified uncommitted-tier boundary required by D105
(`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md:92-103`).

Fix: pin `bf5e789` or a later immutable descendant that actually contains both
corrections, and update the appendix row, integration ledger, and gate comment
consistently. No experiment or numerical change is required.
