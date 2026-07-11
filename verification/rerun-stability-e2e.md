# Rerun verification: burst5 stability (B5/P0-5) + ingress-to-first-token e2e (B6/P0-6)

Date: 2026-07-10. Both tasks are compute-only. Scripts in
`verification/scripts/`; sim outputs in `simulation/results/rerun_verify/`.
No `.tex` or existing code/artifacts were edited. All runs use
`ai-dynamo/aiconfigurator/.venv/bin/python` and reuse
`workload/trace_to_two_pool.py`'s `simulate_vision_pool` / `build_series` /
`percentiles` plus the `silicon_multiworker.py` cost objects
(`AICEncoder`, `MeasuredEncoder`), so the harness is bit-identical to the grid
(it reproduces every `silicon_multiworker.json` number exactly — see checks below).

---

## TASK 1 (B5) — the divergence heuristic is an endpoint artifact; burst5's honest C* is 8 (AIC)

### The bug
`trace_to_two_pool.py:528-534` flags `queue_divergent` when the image backlog at
the **last-arrival second** exceeds `10 x median-backlog-to-that-point`. For a
pool that is idle most of the window the median backlog is ~0, so the threshold
collapses to 10 images and **any** end-of-window transient trips it — even one
that drains in a fraction of a second. burst5 is exactly this case: at C=8 the
pool runs at **7 % mean utilization** yet is flagged "divergent", which in the
grid forced burst5's `C*` up to 16 and made 16 the fleet-wide *deployable
static* denominator.

### The principled criterion (`verification/scripts/burst5_stability.py`)
For each C in {8,10,12,14,15,16}, under **both** the AIC `f(N)` (grid costing,
`aic_f_n_postinfill.csv`) and the **measured stable-clock RTX-5090 silicon**
`f(N)` (`oneworker_artifact/silicon_burst5.json`, the same object
`silicon_multiworker.py` uses), it computes:

- **image-bearing (conditional) encoder-delay p99** — over image-bearing
  requests only, no zero-padding (the actual user-visible tail);
- **all-request p99** — 0-padded (the grid / `silicon_multiworker` gate metric,
  for cross-check);
- **backlog slope** — linear fit of queue-depth (images) vs time over the
  **last 50 % of the arrival window**; slope <= ~0 ⇒ backlog not accumulating;
- **drain time after last arrival** — last batch finish minus last arrival;
- **tiling test** — burst5's arrivals tiled **3x** back-to-back; the backlog at
  the end of each tile's arrival window is measured. A periodically-repeated
  process is stable iff the per-period end backlog does not grow.

Verdict: **stable** = (slope <= ~0) AND (tiled backlog non-growing);
**feasible** = stable AND (conditional p99 < 1000 ms).

### Results (burst5: 8983 reqs, 4468 image-bearing, 554 803 imgs, 81.0 min span, mean 114 img/s offered)

Capacity/worker at full batch: AIC 202 img/s (`f(64)=316.4 ms`), silicon 125
img/s (`f(64)=511.6 ms`). Mean load ρ is 3.5–11 % across all C — the pool is
nowhere near saturation.

**AIC f(N):**

| C | cond p99 | all p99 | slope (img/s) | drain (s) | ρ | tiled backlog (imgs) | endpoint-div (OLD) | stable (NEW) | feasible |
|---|---|---|---|---|---|---|---|---|---|
| 8 | **852** | 760 | −0.0003 | 0.386 | 0.071 | [501, 501, 501] | **True** | True | **True** |
| 10 | 802 | 694 | −0.0002 | 0.386 | 0.056 | [356, 356, 356] | True | True | True |
| 12 | 747 | 636 | −0.0001 | 0.386 | 0.047 | [228, 228, 228] | True | True | True |
| 14 | 665 | 588 | −0.0001 | 0.386 | 0.040 | [100, 100, 100] | True | True | True |
| 15 | 588 | 588 | −0.0 | 0.316 | 0.038 | [36, 36, 36] | True | True | True |
| 16 | 588 | 588 | −0.0 | 0.316 | 0.035 | [0, 0, 0] | False | True | True |

**Silicon f(N):**

| C | cond p99 | all p99 | slope (img/s) | drain (s) | ρ | tiled backlog (imgs) | endpoint-div (OLD) | stable (NEW) | feasible |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 1378 | 1257 | −0.0018 | 0.776 | 0.114 | [501, 501, 501] | True | True | False |
| 10 | 1251 | 1117 | −0.0010 | 0.776 | 0.091 | [356, 356, 356] | True | True | False |
| 12 | 1168 | 1027 | −0.0012 | 0.776 | 0.076 | [228, 228, 228] | True | True | False |
| 14 | 1045 | 926 | −0.0011 | 0.776 | 0.065 | [100, 100, 100] | True | True | False |
| 15 | **898** | 789 | −0.0009 | 0.551 | 0.061 | [36, 36, 36] | True | True | **True** |
| 16 | 784 | 784 | −0.0008 | 0.512 | 0.057 | [0, 0, 0] | False | True | True |

Reading:

- The **slope is negative at every C** (queue is draining, not building) and the
  **tiled per-tile backlog is exactly constant** ([501,501,501], … — each copy
  of the burst leaves the identical small residual, which then fully drains).
  The pool is **stable at every C, including 8** — under **both** cost models.
  The endpoint "divergence" is a within-window transient of ~500 images that
  drains in **0.386 s** (AIC) / **0.776 s** (silicon); it is flagged only because
  the pool is idle ~93 % of the time so the median-based threshold is ~10 images.
- The values reproduce `silicon_multiworker.json` **exactly** (AIC C8 all-p99
  759.5, C16 588.4; silicon C8 1257.1, C16 783.6; divergence flags identical),
  confirming the harness. The task's spot values also reproduce: **conditional
  p99 = 852 ms at C=8** and **drain 0.386 s**.
- Once divergence is dropped, burst5 is **p99-knee-limited, not
  divergence-limited**: AIC knee at **C=8** (cond 852 < 1000; C=7 = 1038 > 1000),
  silicon knee at **C=15** (cond 898 < 1000; C=14 = 1045 > 1000). Neither is 16.

### Honest burst5 C* and the headline ratio

Numerator (forecast worker-seconds, `f(N)`-independent — it is the integral of
the schedule C(t)): fc L30 = 2.375 M, fc L300 = 2.116 M. Denominator = C* x
483 660 s.

| static C* | basis | static Mworker-s | ratio L30 | ratio L300 |
|---|---|---|---|---|
| **8** | **AIC honest knee** (per-episode: burst2 & burst5 both) | 3.869 M | **0.61×** | **0.55×** |
| 15 | silicon burst5 knee | 7.255 M | 0.33× | 0.29× |
| 16 | OLD (burst5 divergence artifact) | 7.739 M | 0.31× | 0.27× |

**Directly confirmed at week scale** (per-episode grading is what the thesis
uses): a full-week static **C=8** encoder run (offset 250399, 749 601 reqs,
`simulation/results/rerun_verify/week_static_C8.*`) gives **encoder-delay p99
644 ms, queue_divergent = False** — comfortably feasible. Week-static knee
bracketing: C6 → 905 ms, C7 → 765, C8 → 644, C16 → 565 (all non-divergent at the
week endpoint; per-episode grading pins the honest fleet at C=8 because burst2 &
burst5 each need 8 — C6/C7 pass only the *aggregate*, the very
dashboard-masking the thesis warns about).

**⇒ Under the AIC cost model that prices the whole grid, the honest headline is
0.55–0.61× (was 0.27–0.31×): the forecast saves ~40–45 %, not ~70 %. The C=16
denominator doubled the apparent saving via a 2× endpoint artifact.**

### Do AIC-model stability and silicon stability agree? (the task's key check)

**Yes on stability, and this resolves the burst5 story:**

- **Both** cost models say burst5 is **stable (non-divergent) at every C ≥ 8** —
  the divergence flag is a shared artifact of the endpoint heuristic, not a real
  property. So `silicon_multiworker.json`'s burst5 `silicon_cstar=16` is **also**
  the divergence artifact, not a divergence limit.
- They **disagree on the SLA-feasible knee** (AIC C*=8 vs silicon C*=15) for the
  ordinary reason the rest of Phase E documents: slower silicon per-batch service
  deepens the same peak transient, so it takes more workers to pull the p99 under
  1000 ms. burst5's silicon/AIC knee ratio is 15/8 ≈ **1.9×** — the *same* ~2×
  latency-knee underprice already reported for the other five windows. **burst5
  is therefore not special: it is knee-limited like the others.**

### Important wrinkle for the deployable-static denominator (silicon)

The fleet-wide static denominator is `max` over windows of the per-window C*.
Removing the artifact:

- **AIC:** per-window C* = {burst1 6, burst2 8, burst3 7, burst4 7, **burst5 8**
  (was 16), burst6 6} ⇒ fleet **C*=8** (bound by burst2 **and** burst5).
- **Silicon:** per-window C* = {burst1 13, **burst2 16**, burst3 13, burst4 14,
  **burst5 15** (was the "16 divergence" — really the 15 knee), burst6 12} ⇒
  fleet **C*=16, now bound by burst2's genuine 2.0× silicon p99 knee**, not
  burst5. (burst2 silicon knee confirmed in `silicon_multiworker.json`:
  `silicon_feasible_cstar=16`, and re-derived here — conditional p99 crosses 1000
  between C=15 (1141) and C=16 (916).)

So the currently-reported **0.27–0.31× is *not wrong as a silicon-deployable
number*** — a static fleet that must physically meet the SLA on real 5090
silicon does need C=16 — **but it is mis-attributed**: the binding window is
**burst2 (real p99 knee)**, not **burst5 (endpoint divergence)**. Two honest
readings, both worth stating:

1. **AIC-internally-consistent** (denominator priced on the same `f(N)` as the
   numerator): **C*=8 ⇒ 0.55–0.61×.**
2. **Silicon-deployable** (denominator = fleet that meets the SLA on measured
   silicon): **C*=16, from burst2 ⇒ 0.27–0.31×** (unchanged value, corrected
   provenance). Read this way the forecast's advantage is *larger* on silicon
   (0.27× / ~70 %) than on AIC (0.55× / ~45 %), because the static baseline pays
   the 2× silicon knee across the whole week while the forecast only pays it at
   the peaks it provisions for.

Recommendation (user's call, per honest-number-with-sensitivity policy): headline
the **AIC-consistent 0.55–0.61×** as the primary corrected number, and keep
**0.27–0.31×** as the explicitly silicon-priced/deployable bound with the
provenance moved from burst5-divergence to burst2's silicon knee. Do **not**
leave 0.27–0.31× attributed to a burst5 divergence bound — that specific
justification is the artifact.

### Proposed tex edits (not applied)

1. **`tex/baselines.tex` Table `tab:base-grid` (line 81)** — burst5 `C*` `16`
   is the artifact. If keeping the AIC-consistent story, change burst5 `C*` to
   **8** (5090 GPU-h 21.6 → **10.8**, H100 GPU-h 5.4 → **2.7**), and edit the
   surrounding prose (lines 103–107): "the encoder requirement swings from 2 …
   to **8** on burst2/burst5" and "the single static fleet that survives all
   windows, **C=8** encoders plus TP2×2". If instead keeping C=16 as the
   silicon-deployable fleet, add a footnote: burst5's own AIC knee is C=8; the
   C=16 fleet is set by **burst2's measured-silicon p99 knee** (2.0×), and add a
   sentence distinguishing the AIC-costed (C=8) from the silicon-deployable
   (C=16) denominator.

2. **`tex/closedloop.tex` Table `tab:cl-aggregate` (lines 305–320) + headline** —
   if AIC-consistent: `Static C=16 (deployable)` → `Static C=8 (deployable)`,
   Mworker-s `7.74` → **3.87**, and the forecast rows' `vs. static` `0.31×/0.27×`
   → **0.61×/0.55×**; headline "0.27–0.31 times … 7.74M" → "**0.55–0.61 times …
   3.87M**". If keeping the silicon-deployable framing, keep the numbers but
   re-attribute the C=16 denominator to burst2's silicon knee, and add the AIC
   sensitivity (0.55–0.61×). The `588 vs 565` service-floor sentence is unchanged.

3. **`tex/aiconfigurator.tex` §silicon multiworker (lines 336–348)** — the claim
   "The sole exception, burst5, is alone sized by the sustained-volume
   **divergence bound** (16 workers, far above its p99 knee)" is **incorrect**:
   burst5's 16 is an endpoint artifact; its real knees are C=8 (AIC) / C=15
   (silicon), both p99-latency-knee-limited and stable. Replace with: **all six**
   windows are p99-latency-knee-limited; burst5's silicon knee (15) sits at the
   same ~1.9× inflation as the others (so the "knee-vs-divergence" dichotomy
   collapses to "all knee-limited"), and the fleet-wide C=16 on silicon is set by
   **burst2** (2.0×), not by burst5 divergence.

---

## TASK 2 (B6) — modelled ingress-to-first-token p99 ≈ 1.30 s (≈ 2× either marginal)

### The bug
The thesis reports the encoder-delay p99 (588 ms) and the language TTFT p99
(651 ms) **separately** (the original ingress arrival is discarded before the
language replay), and never combines them. A real request traverses both pools:
`ingress → encoder pool (encoder_delay) → LLM pool (TTFT) → first token`, so the
user-visible tail is `p99(encoder_delay[i] + TTFT[i])`, which depends on the
per-request coupling of the two delays.

### Method (`verification/scripts/e2e_ingress_to_first_token.py`, aggregate fc_p90_L30, 749 601 reqs)

- **encoder_delay[i] — exact.** Recovered per request as
  `emitted_ts[i] − raw_arrival[i]`. The emitted mooncake timestamp is
  `raw_arrival + encoder_delay` (`encoder_shift_applied=True`, speedup 1);
  `raw_arrival[i]` is reconstructed from `load_window(749601, 250399)` and
  `hash_ids[0]//100000 = i` maps each emitted row back to its source index.
  **Validation:** recovered p99 = **588.37 ms**, identical to the converter
  stats — the reconstruction is exact.
- **TTFT[i] — modeled and validated.** AIC single-pass
  `predict_prefill(1, isl_i, 0)` on the **same** language-pool model the week
  replay used (`h100_sxm` / vLLM `0.19.0` / Qwen3-VL-8B / **TP2**), memoized by
  isl. **Validation against `week_fc_p90.report.json`:**

  | | p50 | p90 | p95 | p99 | mean | max |
  |---|---|---|---|---|---|---|
  | modeled (predict_prefill) | 17.6 | 83.9 | 144.8 | **705.9** | 50.3 | 4498 |
  | replay report | 22.7 | 96.7 | 178.9 | **651.1** | 58.2 | 4366 |

  The two distributions track closely (p99 within ~8 %), confirming the week's
  language TTFT is **prefill-compute-bound** — the p90 forecast keeps LLM
  queueing negligible — so the deterministic per-request `predict_prefill` is a
  faithful stand-in. (Per-request TTFT is not exposed by the Rust replay
  `run_mocker_trace_replay`, which returns only aggregate percentiles; this AIC
  route is the rigorous alternative and it is validated against the real run.)

### Result

`e2e[i] = encoder_delay[i] + TTFT[i]`, over all 749 601 requests:

| quantity (p99, ms) | value |
|---|---|
| encoder-delay only (marginal) | 588 |
| language TTFT only (marginal) | 706 modeled / **651 replay** |
| **modelled end-to-end ingress→first-token** | **1295** |
| naive additive (p99 + p99) | 1294 |
| lower bound max(marginals) | 706 |
| image-bearing-only e2e p99 | 1335 |

NOTE (issue-time update): the script now reads the issue-time schedule's
per-request file (`fc_p90_L30_issuetime.jsonl`) rather than the target-time
`fc_p90_L30.jsonl`. All-request modelled e2e p99 is unchanged at **1295.17 ms**;
image-bearing changes 1348.83 → **1335.43 ms**. This is a MODELLED
reconstruction (encoder delay recovered exactly; prefill TTFT modelled by AIC
and validated), not a request-linked replay measurement.

- **Modelled e2e p99 = 1295 ms** (modelled TTFT 706). Using the replay's own
  TTFT p99 (651) instead, the near-comonotonic tail gives ≈ 588 + 651 = **1239 ms**.
  So the modelled ingress-to-first-token p99 is **≈ 1.24–1.30 s — roughly 2× the
  encoder marginal (588) and ~2× the language marginal (651/706).**
- **Why e2e p99 ≈ the naive additive sum (1295 ≈ 1294):** encoder_delay and TTFT
  are **positively correlated** (Pearson 0.42 all requests, **0.53 image-bearing**)
  because both are driven by the same large multi-image "frames-class" requests —
  many images ⇒ large encoder batch + handoff **and** huge `ContextTokens` ⇒ long
  prefill. The tails coincide, so the sum's p99 nearly reaches the comonotonic
  upper bound. The two separately-reported numbers therefore **understate the
  modelled first-token wait by ~2×**, and the mistake is not conservative — it is
  exactly the regime where adding the marginals is *right*.

### Proposed tex edits (not applied)

- Add one sentence wherever the 588 ms (encoder) and 651 ms (TTFT) tails are
  reported as the pipeline's latency (e.g. `tex/conclusion.tex` ~line 58,
  `tex/closedloop.tex` service-floor discussion): the **end-to-end
  ingress-to-first-token p99 is ≈ 1.3 s**, ~2× either pool's tail, because a
  request pays both in series and the two tails are positively correlated
  (r ≈ 0.5 on image-bearing requests) — they must not be read as alternatives.
- If a combined number is wanted in a table, report **≈ 1.24–1.30 s** (range =
  replay-TTFT vs modelled-TTFT coupling) rather than either marginal or their
  average.
- Optional scope note: this is the p90-forecast policy's e2e (both pools at their
  forecast-provisioned floors); it is the honest user-facing SLA the two-pool
  design must ultimately meet.

---

## Artifacts

Scripts (`verification/scripts/`):
- `burst5_stability.py` — Task 1 principled stability test (AIC + silicon).
- `burst5_knee_sweep.py` — Task 1 supplement: burst5/burst2 knee sweep C=4..16.
- `e2e_ingress_to_first_token.py` — Task 2 end-to-end p99.

Sim outputs (`simulation/results/rerun_verify/`):
- `burst5_stability.json` — full per-C stability metrics, both cost models.
- `e2e_ingress_to_first_token.json` — end-to-end result + validations.
- `week_static_C{6,7,8}.jsonl.stats.json` (+ `.jsonl`, `.log`) — full-week AIC
  static runs confirming the C=8 denominator (p99 644 ms, non-divergent).

Cross-checks: the stability harness reproduces every `silicon_multiworker.json`
burst5 number (all-request p99 and divergence flags) exactly; the encoder-delay
p99 recovered in Task 2 (588.37) equals the converter stats; the modeled TTFT
distribution matches the week replay report within ~8 % at p99.
