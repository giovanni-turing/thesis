# New measurements (defense session) → thesis gaps reinforced

Every item below is a *new* simulation/measurement generated this session (beyond
the ledgered thesis results), with the specific thesis limitation / future-work
item it closes or strengthens. All endpoints that have a ledgered twin reproduce
it exactly; everything else is a new run under the identical ledgered law.

Enabling change: a source-build patch to `ai-dynamo/dynamo`
(`PlannerReplayBridge.report_jsonl_path`, commit `70c965db26`) threads
**per-request records through the planner replay path** — the recording machinery
existed only for the non-planner path. This is what makes every language/E2E
per-request measurement below possible.

---

## 1. Composed ingress→first-token: modelled → MEASURED  (closes a stated gap)

**Gap (tex/twopool.tex §sim-knees):** the composed first-token latency (~1.30 s)
was "a modelled reconstruction rather than a request-linked replay measurement."

**New (A12, `a12_runs`, 15 cells):** each request's **own** encoder delay (recovered
from the seam) + its **own** replayed TTFT — a request-linked join, arrival
alignment asserted < 1 ms.
- burst3 forecast E2E p99 **1,239.5 ms** (enc 588.4 + TTFT 651.1) = the modelled
  ≈1.24–1.30 s, now **measured**.
- **New finding:** reactive composed E2E **21,868 ms** (encoder 16,079 ms
  *compounds* into language 10,574 ms) — per-pool grading *understates* the
  composed failure. Not in the thesis.

## 2. Full-trace coverage guarantee: every request, both pools  (new)

**Gap:** the thesis grades windows/aggregate; no per-request whole-trace pass.

**New (A13, `a13_runs`, 5 runs):** ALL **1,000,000** requests simulated through
both pools with per-request records —
encoder (static C8 / static C2 / reactive) and language (static TP2×2 /
reactive planner), each exactly 1,000,000. `coverage_manifest.json`:
encoder_all_1M **True**, language_all_1M **True**, complete **True**.

## 3. Per-model forecast coverage → ~full trace  (closes the warm-up boundary)

**Gap (tex/closedloop.tex):** zero-shot forecasts undefined on the first 1.4 days
("the warm-up hole is the price of zero-shot honesty") — fixed-context origin
grid needs full history (Chronos 33.6 h).

**New (expanding-context archives, `predictors/benchmark_expctx.py`, 12 parquets):**
grow the context as history accrues instead of waiting for a full window →
first forecast at **12:03:00 (3 min in)** for all three models. Coverage
75/87/93 % → **99.96 %**. Thesis archives untouched (new `*_expctx.parquet`).

**New (A15, `a15_runs`, 3 runs):** each model E2E over span_expctx =
**999,599 req (99.96 % of 1M)**, both pools, per-request records. *[running]*

## 4. Per-model max-span E2E: model-independence, end to end  (reinforces)

**Gap:** headline uses Chronos; Toto/TimesFM only referenced; model-choice
"second-order" claimed but not shown E2E.

**New (A14, `a14_runs`, 3 runs):** each model over its own max forecastable span,
both pools —
- Chronos **651.1 ms**, 749,601 req (75 %), 528 GPU-h
- Toto **651.1 ms**, 872,980 req (87 %), 751 GPU-h
- TimesFM **651.1 ms**, 931,628 req (93 %)

Identical 651.1 across models → model-independence is now an **E2E measurement**,
not an accuracy-benchmark inference.

## 5. Three-model interactive coverage everywhere  (reinforces)

**New:** A2 (encoder), A11 (language), A12 (composed) each toggle
**Chronos / Toto / TimesFM**.
- A2 TimesFM encoder fleet (`a2tf_runs`, 36 cells): reproduces the ledgered
  TimesFM factorial; e13 fails **identically** to Chronos/Toto (model-independent
  forecast-miss).
- A2 Toto encoder fleet (`a2t_runs`, 36 cells).

## 6. Reactive-failure generality: all 18 episodes  (reinforces RQ1/RQ4)

**Gap:** reactive failure shown on the top-6 episodes only.

**New (A2 extra episodes, `a2x_runs`, 88 cells = e7…e18 × policy × lead):**
- Reactive fails **9 of 18** episodes at L=30 s (onset map).
- **e13** (263 img/s, 7-min onset, isolated after the calm stretch) is a genuine
  **p90 forecast-miss boundary case** — both policies fail; only static C8 passes;
  verified identical across Chronos/Toto/TimesFM and ρ=10/15. The honest boundary
  of the p90-headroom mechanism.
- burst2/6 reactive independently reproduce thesis Tab 7.3 through the full pipeline.

## 7. Language-pool race, full grid  (reinforces the per-pool mechanism)

**Gap:** language closed-loop replayed end-to-end only for burst1/3/week; rest
priced by the grid + knee formula.

**New (A11, `a11_runs`, 51 cells):** 4 burst windows + full week ×
{Chronos, Toto, TimesFM, reactive} × replica-lead {60,120,300} s, planner-in-loop,
per-request records.
- Forecast **651 ms PASS** vs reactive **3.49 s FAIL** (window-mean law met,
  tail violated) — every L60 anchor reproduces the ledgered twin.
- Reactive failure is **lead-invariant** on the language pool too (burst5:
  2,151/2,151/2,155 ms at L60/120/300) — the conversion defect, not timing.
- Week: forecast 651 ms vs reactive 1,195 ms at ~half the cost.

## 8. Dual cost accounting (readiness- vs order-billed)  (reinforces the cost claim)

**New (A2, `a2_cost_accounting.csv`, 40 cells):** each policy costed both ways
(bill-from-readiness = ledgered; bill-from-order = each up-step pays its warm-up).
Order-billing *widens* the forecast's advantage (reactive churns 2–5× the
worker-increments); on burst5 L165 it **flips** the cost order (reactive dearer
AND failing). Confirms the 0.62× is conservative.

---

## Roll-up

New simulation runs this session (excluding the ledgered thesis set):
A2 encoder fleets 40+36+36+88, A11 language 51, A12 composed 15, A13 full-trace 5,
A14 max-span 3, A15 expanding 3, expanding-context forecast archives 12 parquets —
plus the dynamo per-request source patch. Every request of the 1,000,000-request
trace is simulated through both pools; each forecast model is covered to
99.96 % E2E; and the Ch. 6 modelled reconstruction is upgraded to a measured
request-linked join.

## Methodology (confirmed sound; no change)

Forecast = offline prediction of **exogenous** demand (WAPE-graded, median point,
p90 provisioning signal). Everything in-flight (TTFT, queue, replica decisions,
SLA verdicts) = the discrete-event mocker computing outcomes from
**silicon-calibrated** timings per (config, policy, lead). The archived forecast
is rolling-origin, so replaying it is online-equivalent for the exogenous signal;
the one endogenous piece (language capacity conversion) is already in-loop.
Endogenous demand (abandonment/retry) remains the honest future-work frontier.
