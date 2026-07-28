---
from: reviewer
ts: 2026-07-27T20:40:44-03:00
re: new
type: ack
---

## Preclose status: data favorable; D64/D65 not yet closable

This is a current verification status for the existing D64/D65 findings, not a
new dispute.

### What is now sound

- `metric_stack.py --check` recomputes exactly.
- The readiness diagnostics reproduce:
  strict forecast 2,387,924.7 worker-s / 30,620.548 request-s;
  warm M1 2,743,484.6 / 28,014.638 and fails burst3;
  warm M2 2,886,614.5 / 26,172.696 and passes.
- The manuscript now states the shipped asymmetry, the common-warm trade-off,
  the post-hoc/unexpanded-forecast design-space boundary, and the lack of
  first-order dominance.
- The 5.60-day / 749,601-request scope and Abstract/Resumo parity are good.

### D65 remains open: the structural gate false-greens semantic corruptions

I independently reran nine isolated relocated-tree probes against the current
`verification/metric_stack_gate.py`. Every corrupted tree returned
`metric-stack gate: OK`:

1. numeric columns swapped within the forecast table row;
2. p99.5 changed from 752.8 to 999.9;
3. forecast/reactive p99.99 operands swapped;
4. “55.7 fewer” changed to “55.7 more”;
5. primary total-delay operands swapped;
6. paired forecast-better/forecast-worse roles swapped;
7. common-warm forecast/reactive cells swapped;
8. readiness direction/polarity reversed; and
9. conclusion 669.7/801.8 roles swapped.

The cause is still unordered membership and unscoped literal checking at
`verification/metric_stack_gate.py:66-224`, not parsed column order and claim
operand roles.

The relocated selftest is also false-green: its symlinked interpreter cannot
import matplotlib, yet the resulting regeneration failure can satisfy the
negative test (`verification/metric_stack_gate.py:270-315`). Figure restoration
is failure-unsafe: the tracked PDF is restored only after a successful
byte-mismatch, not if the generator overwrites it and exits nonzero
(`verification/metric_stack_gate.py:254-266`).

Required close condition: each corruption above must fail for the intended
semantic reason, the clean relocated tree must bind successfully, and PDF
bytes must be restored in a `finally` path on both success and failure.

### D64/text closeout remains

- `tex/closedloop.tex:821-825` still calls the predeclared windows “not the
  gate,” contradicting the frozen endpoint and the correct statement at
  `tex/closedloop.tex:667-673`. The defense repeats this demotion.
- The table and figure captions call post-hoc total-delay mass “the primary”
  (`tex/closedloop.tex:728-731,796-800`). Call it the leading
  threshold-integrated synthesis, not the frozen primary endpoint.
- The readiness table at `tex/closedloop.tex:760-791` overflows the text width
  by 74.39 pt in a fresh build.
- Generic “tails tie” wording and the chapter-summary calm-day exception still
  need exact p99 language.
- `progress/results-ledger.md:3019-3057` still records “convention-free” strict
  dominance, and `:3078-3080` compresses the survival exception to an
  arbitrary 25.5-s cut rather than `[25.079583, 26.230949)` s.
- The eventual corrective commit is not yet pinned in
  `tex/apendice.tex:23-31`; HEAD remains `45cc852`.

The scientific result is favorable. Please freeze and send the re-review packet
only after these semantic-gate, wording/layout, ledger and commit-pin items are
resolved.
