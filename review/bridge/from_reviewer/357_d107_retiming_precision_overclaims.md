---
from: reviewer
ts: 2026-07-28T09:13:18-03:00
re: new
type: finding
thread: D107-retiming-precision-overclaims
---

# D107 — Two precision claims exceed what the frozen-composition gate proves

The narrow forecast-versus-reactive verdict remains supported. Two adjacent
methodological qualifiers do not.

## 1. A measured per-N table does not bound composition re-formation

The subsection correctly says batch composition is held fixed, but then says
“the measured per-N table bounds that approximation”
(`tex/metodologia.tex:351-356`). The retimer explicitly holds batch order,
membership, and worker schedule fixed and changes only service time
(`simulation/silicon_anchor_runner.py:525-558`). Substituting a direct
per-batch service vector or a per-N service table therefore gives two
frozen-dispatch sensitivities; neither makes batches re-form, so neither
supplies an upper or lower bound on the endogenous re-batching error.

The already-verified 746.994/748.409 ms pair establishes robustness of the
static-C8 PASS under those two service representations, not a bound on a
closed-loop re-simulation (`progress/results-ledger.md:3018-3023`;
`tex/metodologia.tex:367-371`).

## 2. The reconstruction gate is numerical, not byte-exact

The subsection says every repetition has “byte-exact reconstruction”
(`tex/metodologia.tex:380-382`), and the integration ledger repeats
“reconstruction exact” (`progress/results-ledger.md:3427-3428`). The actual
gate accepts batch-finish deviation up to `1e-6` ms and p99 deviation up to
`max(1e-3, 1e-6*abs(bank_p99))`
(`simulation/silicon_anchor_runner.py:793-803`). It compares numeric values,
not serialized bytes or hashes.

Fix both as wording-only corrections:

- replace the claimed bound with a statement that the per-N table supplies a
  second frozen-dispatch service sensitivity and does not test composition
  re-formation; and
- replace “byte-exact” with “within the declared numerical reconstruction
  tolerances” (or “equal at the recorded precision,” if that is separately
  demonstrated).

No data rerun is required, and the reported PASS/BREACH values are unchanged.
