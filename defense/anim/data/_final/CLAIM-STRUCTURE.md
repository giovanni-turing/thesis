# Claim structure — what may be claimed, at what strength, and what may not

Written after four adversarial audit rounds (12 + 9 + 4 skeptics + a fix pass) in which every
result was attacked. This file exists so the contribution is stated at exactly the strength the
evidence carries — no more, and no less.

---

## TIER 1 — robust to every attack made. State these plainly and lead with them.

**1a. The reactive baseline fails STRUCTURALLY, not by mistuning.**
It misses the SLA in 0/6 G1 language cells, 4/7 folds, and 9/18 episodes, violating BOTH bounds
(ITL 136-143 ms against a 100 ms cap). Crucially it fails **lead-invariantly** — burst5 gives
2151 / 2151 / 2155 ms at L=60/120/300. A defect that does not move with lead is not a timing
deficit that tuning could remove. This is the strongest claim in the thesis and nothing dented it.

**1b. The two pools have DIFFERENT binding dynamics, and that is the actual contribution.**
The encoder pool is cold-start-bound and genuinely needs anticipation (issue-time gated, 165 s
maximum staleness). The language pool is conversion-bound: its forecast arm samples the archived
bin ~60 s BEHIND sim time (replay_with_forecast.py:113-121) and still beats ARIMA, because what
wins there is the tail-aware p90 conversion against a mean-based one. Per-pool treatment is
therefore not a convenience — it is the thing a single-pool reactive controller structurally
cannot do.

**1c. Zero-shot is cold-start deployable.** Provisioning is correct from 3 minutes into an unseen
workload, covering 99.96 % of the trace end to end. No trained forecaster can answer this: it
needs history that does not exist at deployment time.

**1d. Model choice is second-order, measured end to end.** Chronos-2, Toto-2.0 and TimesFM-2.0 all
give TTFT p99 651.1 ms and encoder delay p99 588.4 ms over 749,601 / 872,980 / 931,628 requests
(A14) and 999,599 each (A15).

---

## TIER 2 — solid, but ONLY with their scope attached.

**2a. Encoder cost below the DEPLOYED static fleet: 0.62x.** Correctly worded in the thesis
("deployable", never "static-optimal"). Scope that must travel with it: against the fold-robust
optimum C=5 the ratio is **0.980x**, and per-fold it ranges 0.465x-1.098x. The C=8 choice needs an
explicit justification in the text (available: C=4 fails 3 of 5 burst-bearing folds; C=4's margin
is 0.6 % against C=5's 9.5 %).

**2b. The 0.62x survives charging the controller its own inference cost** — 0.6240x on GPU, and
0.65-0.66x on every DEPLOYABLE CPU configuration.

**2c. Cold start is already inside the reported language costs** (the mocker integrates provisioned
workers incl. starting-up). The encoder bills from readiness — opposite convention, so a composed
two-pool total mixes the two.

---

## TIER 3 — NOT SUPPORTED. Do not write these.

- **"Predictive provisioning is cheaper than static."** Encoder-only, and only against the deployed
  fleet **on the covered span**. On the LANGUAGE pool the forecast is DEARER than static in 6 of 7
  folds (0.93x-3.81x), and dearer than static on both G1 windows (2.2x-3.6x). On the ENCODER pool
  it is dearer than the deployed fleet on F7 (1.10x) and, on F6, is **infeasible** while a static
  C=5 fleet passes for 3.0% more. **A forecast-free static fleet is the arm to beat on both
  pools**; no language-pool cost advantage may be claimed anywhere in the thesis or the defence.
- **"Forecast beats reactive on cost."** The arms are not cost-matched: G1's forecast arm spends
  3-6x the reactive arm's GPU-hours. It is an SLA-attainment claim.
- **"The baseline is 2x oversized."** A pooled-tail artifact. The defensible figure is 1.6x (8 vs 5),
  and against C=5 the schedule is still cheaper.
- **"Lead time closes the out-of-span hole."** On the language side G1 compares two CONVERSIONS of
  the same held signal; it does not demonstrate anticipation.
- **"The decode series is an offered-work upper bound."** It is not a pointwise bound; use the
  observable-selection statement instead.
- **"Accuracy is saturated."** A single failed fine-tuning recipe does not establish a ceiling.
  Fine-tuning is out of scope; one future-work sentence only.
- **"Closed-loop endogenous demand."** It is mean-field, resolved offline, and settles into a
  period-2 limit cycle.

---

## The honest one-paragraph contribution

"Modality-disaggregated serving splits a multimodal workload into pools whose binding constraints
differ: the vision pool is cold-start-bound and rewards anticipation, while the language pool is
conversion-bound and rewards a tail-aware capacity mapping. A single reactive controller cannot
express that difference, and fails accordingly — missing both the first-token and inter-token
bounds on nine of eighteen burst episodes, lead-invariantly, which identifies the defect as
conversion rather than timing. Per-pool provisioning driven by zero-shot foundation forecasts
meets the bounds where reactive cannot, from three minutes into an unseen workload and identically
across three model families, at 0.62x the deployed static encoder fleet's provisioned worker-time.
The saving is an encoder-pool result measured against the deployed fleet; against a fold-robust
static optimum it is marginal, and on the language pool the policy buys SLA compliance rather than
savings."

That paragraph is fully defensible against every attack mounted in this session.

---

## The five things an examiner will press, and where the answer is

| challenge | answer |
|---|---|
| Why C=8 and not a smaller static fleet? | G4_folds_FINAL.md — C=4 fails 3/5 burst folds; C*=5; 0.980x |
| The language pool costs more than static | G4 Finding 5 **and G1 Correction 4b** — concede fully; it is an SLA claim there, never a cost claim |
| On F6 the forecast FAILS and static C=5 passes | G4 Finding 4b — concede: 3.0% more worker-time buys feasibility. Do not argue this one |
| e13 / F6 failures | ZEROSHOT-AS-STRENGTH.md §3 — mechanism boundary, model-independent |
| Generalization from one trace | G4 — within-trace TEMPORAL folds only; concede cross-workload openly |
| tex/twopool.tex 882 ms | THESIS-TEXT-DEFECTS.md — the "882 -> 783" requote is **REFUTED**; that paragraph is wheel on both arms and is internally consistent. **Make no such edit.** |
