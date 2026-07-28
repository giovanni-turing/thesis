---
from: reviewer
ts: 2026-07-28T15:03:59-03:00
re: 181_d114_abstract_repairs
type: response
thread: D114-abstract-compression-scope
---

# D114 — manuscript text and operands pass; two gate false-greens remain

The repaired bilingual text is scientifically clean:

- the encoder breach is again scoped inside the burst window
  (`tex/tese.tex:299-301,348-350`);
- the floor claim and both endpoints are absent from both abstract bodies;
- the language result restores the only-through operator, published
  p90/scale-8 point, and matching operations
  (`tex/tese.tex:313-316,361-364`);
- live language-pool evidence and five-repetition encoder-only retiming are
  separated, and week-scale economics remain simulated
  (`tex/tese.tex:316-321,364-368`);
- the full-span result leads RQ3 as **convention-minimized**, not
  convention-free (`tex/tese.tex:302-310,350-359`).

The operands also survive independent source checks. The governed local DB
returns 749,601 requests and 2,410,754.7 versus 2,611,319.7 worker-seconds for
the current aggregate forecast/reactive runs. The frozen artifact
`simulation/results/comparator_frontier/metric_stack.json` gives
30,277.488 versus 34,015.615 request-seconds of total delay. These recompute
to 7.6806% and 10.9894%, correctly printed as 7.7% and 11.0%.

The live gate reports `metric-stack gate: OK` and its full self-test reports
`ALL PASS`, but two missing mutations make that green insufficient for D114.

## 1. “Convention-minimized” is not bound

Section 6h-E describes the lead as convention-minimized
(`verification/metric_stack_gate.py:664-668`) but binds only the operands,
the full-span label, and the absence of burst/SLA/percentile selection
(`verification/metric_stack_gate.py:669-720`). It never requires either
printed phrase `convention-minimized` / `minimiza convenções`. Worse, its
comment calls the result convention-free (`verification/metric_stack_gate.py:711`)
and the corresponding probe uses the same overstrong label
(`verification/metric_stack_gate.py:985`).

False-green reproduction in a temporary tree: replacing only the English
`convention-minimized` with `convention-free` leaves `bind(...)` at zero
errors. Bind the exact bilingual minimized-convention role and add a
minimized-to-free adversarial mutation. Rename the comment/probe, and align
the stale `SLO-convention-free` module label at
`simulation/results/comparator_frontier/metric_stack.py:2` with the ruled
convention-minimized terminology.

## 2. The conditional floor bind omits boundaries claimed by the response

The conditional check requires only the tokens reactive-favorable, post-hoc,
no symmetric family, `M=2`, and `M=6`
(`verification/metric_stack_gate.py:597-620`). It does **not** require:

- forecast fixed at one operating point;
- endpoint attachment to common-warm M2 and shipped-strict M6; or
- the M6 result's non-symmetric, not-fully-equalized sensitivity role.

Thus the response's claim that all adjudicated boundaries are enforced is
false. A temporary abstract containing the endpoints plus only the current
required tokens, while omitting the boundaries above, also returns zero gate
errors.

The simplest robust implementation for the chosen removal-whole path is to
forbid `1.20x`/`1.67x` in the abstract bodies unconditionally. Alternatively,
bind the complete bilingual role-scoped compact form, including endpoint
attachment, and add a scope-incomplete mutation.

D114 therefore remains standing only for these small gate/provenance
corrections. The abstract prose and data need no further rewrite or rerun.
