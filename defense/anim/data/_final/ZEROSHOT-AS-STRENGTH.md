# Zero-shot forecasting is a STRENGTH, not a concession

(Fine-tuning is OUT OF SCOPE for this thesis. Nothing below depends on it.)

The thesis currently frames zero-shot defensively ("the conservative reading of the foundation
models' capability", "the operationally simpler posture"). Four measured lines support a positive
claim instead.

## 1. It provisions correctly from COLD START — the argument no trained model can answer
A15 + expanding-context archives: forecasts issue from **3 minutes** into the trace (first origin
2024-10-15 12:03:00) and reach **99.96 % coverage — 999,599 of 1,000,000 requests** — end to end
through BOTH pools, for all three model families (TTFT p99 651.1 ms, encoder p99 588.4 ms each).
A trained forecaster is definitionally unavailable at deployment time: it requires history that
does not yet exist. A zero-shot controller provisions a workload it has never seen, from the first
minutes of service. This is the strongest form of the claim and it is now MEASURED, not asserted.

## 2. Model selection is not on the critical path
A14 (per-model max-span E2E, 749,601 / 872,980 / 931,628 req) and A15 (999,599 req each):
Chronos-2, Toto-2.0 and TimesFM-2.0 all deliver **TTFT p99 = 651.1 ms** and encoder delay p99 =
**588.4 ms**. Identical, end to end, across three independent model families.
A practitioner does not have to pick well. For a zero-shot deployment — where you cannot validate
a model against your own workload before serving it — that insensitivity IS the safety property.

## 3. What carries the result is the MECHANISM, not forecast accuracy
A2/A2x across all 18 episodes: the one episode the forecast policy misses, **e13**, fails
**identically under all three models and under both rho=10 and rho=15**. A model-independent
failure is a property of the p90-headroom + tail-aware-conversion mechanism, not of any model's
accuracy. Symmetrically, the 17 episodes that pass, pass under every model.
So the lever is the provisioning mechanism. A different forecaster would not buy a better outcome,
and that is precisely why a zero-shot one suffices.

## 4. Zero-shot removes an entire operational surface, and its cost is measured
No training pipeline, no retraining cadence, no drift detection, no train/test leakage management,
no checkpoint governance — none of which this thesis would otherwise have to charge or audit.
What the controller DOES cost is now measured (A16 controller cost): **12.9 ms/tick (Chronos),
30.1 (TimesFM), 94.4 (Toto)** per signal on GPU. Charged against the fleet, the 0.62x ratio moves
only to **0.6240x**. On CPU-class hardware the 4-signal fleet controller is materially expensive
(0.74-0.75x, erasing the forecast-vs-reactive margin though not the saving vs static), and Toto
cannot hold a 15 s tick on CPU at all (duty 1.95-2.14x) — a deployment constraint worth stating,
and an argument for the 180 s tiled tick or a shared GPU.

## The sentence to write
"The zero-shot posture is not a limitation of this work but a property of the deployment it
targets. A foundation forecaster provisions correctly from three minutes into an unseen workload,
covering 99.96 % of the trace end to end, and does so identically across three model families
(TTFT p99 651.1 ms, encoder delay p99 588.4 ms for all three) — so neither training data nor
model selection sits on the critical path. What carries the result is the p90 headroom and the
tail-aware conversion rather than forecast accuracy: the single episode the policy misses fails
identically under every model and both capacity ratings, marking a mechanism boundary rather than
an accuracy deficit. Charged for its own inference, the controller moves the cost ratio from
0.623x to 0.624x on GPU."

## Honest limits to keep
- Model-independence is measured on ONE trace: it is a property of this workload's
  forecastability, not a general claim about foundation models.
- e13 is a genuine boundary of the mechanism; zero-shot does not remove it.
- On CPU-class hardware the controller's own cost is NOT negligible (see line 4).

## Future-work note (one sentence for the conclusion, keep it small)
"Fine-tuning a forecaster on the operator's own trace remains open as a forecasting-side upper
bound; the zero-shot posture evaluated here is the cold-start-deployable lower bound, and the
gap between them is unmeasured."

Rationale for keeping it brief: an exploratory fine-tuning pass in this session did not improve
point accuracy, but a single failed recipe does not establish a ceiling, so nothing stronger than
"open" is defensible — and the thesis's claims do not rest on it either way.
