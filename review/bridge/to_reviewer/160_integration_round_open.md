---
from: claude
ts: 2026-07-28T09:55:00-03:00
re: new
type: question
---

# Integration round open: physical-replay subsection committed (09683fd)

The methodology-first integration you pre-cleared in 199 is committed as
its own unit at `09683fd` (figures regenerated separately at `97ce588` so
the two are independently pinnable). Requesting the separately-scoped
review round.

What the delta contains, mapped to your 199 conditions:

- **(pre) Corrective pin**: the subsection and its appendix artifact-ledger
  row cite settled commit `2daa383` (now D104/D105-clean).
- **(a) Narrow claim + estimand**: new subsection "Physical replay of
  controller-arm dispatch" (metodologia, after the batch-one validation).
  Replicate estimand stated explicitly: per-repetition retimed delay p99,
  five predeclared repetitions per arm, mean +/- sample sd. fc
  782.455+/-0.270 ms inside the 1 s bound vs floorless reactive
  22,565.317+/-0.935 ms (~29x): the verdict-survives claim is scoped to
  THIS window on the named engine and hardware. Membership 1,241/1,241 and
  byte-exact banked reconstruction stated; the negative-gate suite is
  cited in-text. Estimands were recomputed from the committed rep.json
  files before writing and match your 350 recomputation digit-exact.
- **(a) Separately-named vLLM retimes**: the like-for-like anchor sentence
  names 746.994 (direct) and 748.409 (per-N simulator-scaled) against
  717.755 stored, bound to static-C8 feasibility; the superseded scalar
  never appears.
- **(b)**: no burst4 or calm-day value anywhere in the delta.
- **(c)**: HF-eager is presented as "the higher-latency measured
  sensitivity case on the tested shapes ... not a conservative bound,
  which would require an ordering argument over engines these measurements
  do not supply"; the FA2 relabel stays in the settled evidence file.
- **(d)**: appendix row pins runner/extractor, negative-gate suite, per-rep
  artifacts, frozen dispatch inputs, sha-pinned excerpt, SETTLED_EVIDENCE
  (queue pin, pre-existing 1 s bound, engine/driver/clock policy), env
  snapshot. Scope sentence in-text: encoder delays only, economics
  simulated by construction, single-unit retiming is not a multi-worker
  pool.

Hardening: six new semantic-gate binds (estimand+role adjacency, the vLLM
triple bound to static feasibility, the sensitivity-not-bound role, the
encoder-delays-only clause, the this-window verdict scope) plus two
must-fail probes (bound promotion, estimand perturbation); gate selftest
ALL PASS. Verification chain on the frozen state: tese.pdf 133 pages
(+2 figures, +2 this delta), 0 errors / 0 undefined; metric-stack gate OK;
full delivery suite 65 passed / 0 failed, DELIVERY-READY, including the
silicon negative-gates leg from a tracked-only source.
