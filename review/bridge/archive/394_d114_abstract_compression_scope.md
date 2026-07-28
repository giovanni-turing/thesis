---
from: reviewer
ts: 2026-07-28T14:13:17-03:00
re: 180_ime_conversion_round_open
type: finding
thread: D114-abstract-compression-scope
---

# D114 — The compressed abstracts reopen ruled scopes and omit the principal full-span result

The retained numbers are mostly correct, but the compression is not
scientifically clean in four places. It also drops the one result that is now
supposed to lead RQ3. These are bilingual wording repairs; no experiment rerun
is required.

## 1. The encoder breach lost its burst-window population

The English abstract says that “the encoder pool misses its tail bound at the
trace's own recorded rate” (`tex/tese.tex:305-307`); the Portuguese mirror has
the same unqualified statement (`tex/tese.tex:249-251`). The evidence is
specifically **inside the burst window**, not a full-trace or steady-head claim
(`tex/metodologia.tex:604-621,643-648`). The parent abstract carried that
qualifier.

Add “inside the burst window” / “dentro da janela de rajada.”

## 2. The D113 compact floor form was not retained

The current `1.20x to 1.67x ... depending on readiness model` form
(`tex/tese.tex:263-268,318-321`) names neither endpoint and omits three ruled
boundaries:

- the forecast remains one frozen operating point;
- no symmetric forecast-plus-floor family was run; and
- common-warm `M=2` is the reactive-favorable post-hoc point, whereas shipped
  strict `M=6` is a non-fully-equalized sensitivity.

Those are not optional mechanics; they prevent a tested-point comparison from
becoming a policy-class or equalized-interval claim
(`tex/closedloop.tex:623-653,717-725,1747-1754`). Restore the already
adjudicated compact form in both languages:

> In a reactive-favorable post-hoc floor sweep (forecast fixed; no symmetric
> forecast-plus-floor sweep), common-warm M2 costs 1.20x the forecast; shipped
> strict M6 gives a non-symmetric 1.67x sensitivity.

If that sentence is too expensive under the one-page limit, remove the floor
claim and its numbers together rather than retain a scope-free range.

## 3. The language result lost its operating point and changed what “only” governs

The English abstract now says a generic secondary policy “reaches only near
break-even ... through” tail-aware conversion (`tex/tese.tex:322-325`).
The `0.965x` time-matched and `1.03x` request-matched operands belong
specifically to the published p90/conversion-scale-8 point. Other language
points have different ratios and statuses
(`tex/closedloop.tex:1006-1018,1480-1511`). The causal result is instead that
the same forecast holds its SLA **only through tail-aware conversion**; native
mean conversion fails (`tex/closedloop.tex:1416-1428,1513-1524`).

Use:

> The secondary language policy holds its SLA only through tail-aware
> conversion and, at its published p90/scale-8 point, is near break-even ...

The Portuguese mirror must also restore “pareado por tempo” and “pareado por
contagem de requisições”; `por tempo` / `por requisições`
(`tex/tese.tex:269-271`) no longer names the matching operation.

## 4. The closing sentence fuses two different physical populations

The current closing sentence makes one “verdict” reproduce through the live
language stack and then survive physical RTX 5090 replay
(`tex/tese.tex:272-275,325-328`). These are different pools and estimands:

- live evidence is the fastest-onset **language-pool** p90/reactive result,
  one live run per policy through the real control plane with mocked engines
  (`tex/metodologia.tex:737-742,780-788`);
- physical evidence is five-repetition **encoder-only** frozen-dispatch
  retiming on one RTX 5090, not a controller-in-loop run
  (`tex/metodologia.tex:338-367,406-410`).

Separate the clauses and name both pools. A compact safe form is:

> The fastest-onset language-pool p90/reactive verdict agrees in one live
> Dynamo run per policy (real control plane, mocked engines); separately,
> five-repetition encoder-only frozen-dispatch retiming on one RTX 5090
> preserves that window's simulated forecast/reactive verdict.

Retain “week-scale economics remain simulated.”

## 5. The abstract omits the convention-minimized result that now leads RQ3

The current principal result is not a burst-window or percentile claim. Over
all 749,601 evaluation requests under shipped mechanics, forecast provisions
2,410,754.7 versus 2,611,319.7 worker-seconds — 55.7 worker-hours or 7.7%
less — and accumulates 30,277.5 versus 34,015.6 request-seconds of total
encoder delay, 11.0% less, than the identically informed direct-reactive arm.
Neither operand uses a burst definition, SLA cutoff, or percentile selection
(`tex/closedloop.tex:674-704`; `tex/conclusion.tex:51-65`).

That is abstract-mandatory under the declared result hierarchy. Lead the RQ3
portion with a compact, explicitly full-span version. It may displace
lower-priority detail; the strict-rewarm narrative, `1.042x`, language
two-status bracket, upstream-PR mention, and calm-day replay can remain
chapter-grade.

## Gate implication

The metric-stack gate and its self-test pass, but the abstract portion only
binds the seven-day/one-million and 5.60-day/749,601 population phrases
(`verification/metric_stack_gate.py:462-473`). It therefore cannot detect any
of the four regressions above. Bind the repaired burst-window, floor-endpoint,
language-operating-point, and live-versus-physical roles in both languages,
with at least one adversarial mutation for each role family.

The seven-day and evaluation-span populations themselves remain correctly
assigned; the 12.8% silicon/H100-not-revalidated boundary is intact; and no
D107 exact-reconstruction or D110 equivalence claim was reintroduced.
