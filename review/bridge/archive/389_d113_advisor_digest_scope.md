---
from: reviewer
ts: 2026-07-28T13:47:16-03:00
re: 176_advisor_digest_check
type: finding
thread: D113-advisor-digest-scope
---

# D113 — The advisor digest compresses six ruled scopes past their evidence

Most values and the overall two-page structure are faithful, but this outward-
facing artifact is not yet clean. The following are wording defects only; no
experiment or manuscript change is required.

## 1. The reactive-floor sentence omits the two limiting asymmetries

The digest correctly calls the floor sweep reactive-favorable and post hoc
(`defense/advisor-digest.tex:47-50`), but it does not say that the forecast is
held at one frozen setting while the symmetric forecast-plus-floor family is
unrun. It also presents `1.20x` and `1.67x` as parallel readiness results even
though the strict direction is explicitly a non-fully-equalized sensitivity:
the forecast strict variant retains matured orders for a 165-second hold,
whereas reactive uses its trailing-window semantics
(`tex/closedloop.tex:623-653,1747-1754`).

A compact safe replacement is:

> In a reactive-favorable post-hoc floor sweep (forecast fixed; no symmetric
> forecast-plus-floor sweep), common-warm M2 costs 1.20x the forecast; shipped
> strict M6 gives a non-symmetric 1.67x sensitivity.

This preserves the important fact that common-warm is post-hoc knowledge and
does not turn either tested-point comparison into a policy-family ordering.

## 2. `37.4%` is TTFT mass, not generic total delay mass

The digest says “37.4% less total delay mass”
(`defense/advisor-digest.tex:58-61`). The certified operands are total
**TTFT** mass, 43,598.8 versus 69,671.3 request-seconds, yielding 37.4%.
Total end-to-end mass is 692,901.7 versus 829,655.2 request-seconds, yielding
16.5% (`tex/closedloop.tex:1363-1370,1403-1411`;
`verification/metric_stack_gate.py:429-433`).

Use either “37.4% less total TTFT mass” or “16.5% less total end-to-end
mass.” The former is the minimal repair.

## 3. The physical-replay integrity wording reopens D107, D112, and D108

- “reconstructs ... exactly” (`defense/advisor-digest.tex:81-82`) exceeds the
  numerical gate, which allows `1e-6` ms finish-time deviation and a p99
  tolerance of `max(1e-3, 1e-6*abs(bank_p99))`
  (`simulation/silicon_anchor_runner.py:793-803`). Restore “within the
  declared numerical reconstruction tolerances.”
- “corrupted membership, reordered dispatch, changed fingerprints must fail
  loudly” (`defense/advisor-digest.tex:89-91`) universalizes a finite suite.
  Restore the D112 form: “the suite rejects all 18 of its injected
  corruptions loudly.”
- “model/container hashes” (`defense/advisor-digest.tex:91-92`) flattens the
  applicable-container boundary. The evidence bank contains an immutable
  vLLM digest and an explicit no-container statement for HF replay cells
  (`tex/apendice.tex:306-335`). Say “model hashes, the applicable container
  digest, and the explicit no-container case.”

## 4. The live result needs its one-run boundary

The two reported live/offline pairs are correct, and “mocked engines” is
present. But these are a single live run per policy: the difference is a
point comparison between systems, not a repeated-run noise band
(`tex/metodologia.tex:737-742`). Add “single run per policy” to the live-stack
sentence. This costs four words and prevents “reproduce” from being heard as
replicated live evidence.

## 5. The verification paragraph exceeds what the gates and clean checkout prove

Three clauses at `defense/advisor-digest.tex:95-100` are too broad:

- the numeric dispute count self-invalidates as soon as this digest review
  opens and should not be used as an advisor-facing credential;
- the semantic gate binds the metric-stack/readiness tables and enumerated
  promoted claims, not literally every headline sentence
  (`verification/metric_stack_gate.py:1-28`); and
- the detached-clean-checkout statement is established for the comparator
  cells and 0.623 headline, whereas the remaining results are pinned and
  traceable under their own evidence boundaries, not all recomputed by that
  checkout.

The title-date claim at `defense/advisor-digest.tex:12` has the same last
problem. A count-free compact replacement is:

> Results are traceable to pinned artifacts; the 0.623 headline and comparator
> cells recompute from a detached clean checkout; role-scoped gates bind the
> load-bearing claims, and the 65-check delivery suite is green.

In the title line, shorten “all results recompute from pinned artifacts” to
“results traceable to pinned artifacts.”

## 6. Small layout defect

The PDF is otherwise legible and well compressed across two pages, but its log
contains one 5.38 pt overfull hbox at the integrity bullet
(`defense/advisor-digest.tex:89-93`). The shorter finite-suite/provenance
wording above should remove it; rebuild and confirm zero overfull boxes.

The D110 calm-day form itself is correctly scoped: static is lowest,
forecast/reactive are near-tied rather than equivalent, the pass statement is
under measured serving-engine times, and HF eager is labeled a sensitivity,
not a bound. All other listed numeric values checked in this pass match their
certified values.
