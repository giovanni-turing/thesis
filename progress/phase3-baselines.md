# Phase 3 — Baselines: SLA definitions + re-derived operating points

Companion to `thesis-roadmap.md` (Phase 3). This file opens with the SLA
decision every downstream experiment is graded on; baseline results (3.1
static-optimal, 3.2 reactive planner) accumulate below as they land.

---

## The thesis SLA (decided 2026-07-07)

Two levels, deliberately distinct:

**Evaluation SLA (all policies are graded on this, per pool, per window):**

| Pool | Bound | Rationale |
| --- | --- | --- |
| Language | TTFT p99 < 1,000 ms AND ITL p99 < 100 ms | interactive grade: first token within 1 s and ≥10 tok/s at the 99th percentile; tail-based because the thesis's failure mode IS burst-time tails |
| Vision | encoder delay (queue+service+handoff) p99 < 1,000 ms | matches the language TTFT budget so composed multimodal p99 TTFT stays ≲2 s |

**Policy configuration (reactive baseline only):** Dynamo's SLA Planner
regulates on *window-mean* TTFT/ITL against its shipped defaults
(`ttft_ms=500`, `itl_ms=50` — `planner/config/defaults.py`; the offline
replay adapter feeds `avg_ttft_ms`/`avg_itl_ms`). The planner keeps those
native defaults unmodified — they are that policy's control law, not the
SLA. Evaluation-vs-control mismatch (means met, p99 violated) is a
*finding about reactive control*, not a grading inconsistency. The 2×
ratio between the evaluation bounds and the planner means is the
conventional mean-target/tail-ceiling pairing.

## Knees re-derived under the thesis SLA (existing sweep points, no new sims)

`sweep_load.py` now encodes the SLA as its defaults (knee = largest swept s
meeting BOTH language bounds; one new point, llm/head2k/aic/s2, tightens the
calibrated bracket). Figure regenerated (`results/sweeps/knees.png`).

| Curve | knee (was, at placeholder 2 s TTFT-only) | offered at knee | binding bound |
| --- | --- | --- | --- |
| llm · head2k · poly | **s=2** (was s=8) | 5.5 req/s | **ITL** (s=4: TTFT 473 ✓, ITL 154 ✗) |
| llm · head2k · aic | **s=2** (was s=4) | 5.5 req/s | **ITL** (s=4: TTFT 882 ✓, ITL 211 ✗) |
| llm · burst1 · poly | **s=1** (was s=2) | 2.2 req/s | both at s=2 (TTFT 1,458, ITL 178) |
| vision · head2k | s=32 censored (unchanged) | ≥256 img/s | — |
| vision · burst1 | none — over at s=1 (unchanged) | 116 img/s | — |

**Two consequences:**

1. **The language pool is decode-bound, not TTFT-bound**, under an
   interactive SLA: at its knee's successor the TTFT budget still has 2×
   headroom while ITL p99 has crossed. This holds for both timing models
   and matches the 235B expectation — the flagship (TP8) has ITL p99
   87.7 ms already at s=1 (knee s=1, 2.8 req/s; 8B knee s=2): decoder
   size halves the language knee while the vision pool is family-invariant.
2. **The decoupling sharpens to ≥16×** on the steady head (vision ≥s=32 vs
   llm s=2, both timings), and the burst reversal is now exact: the
   language pool meets the SLA at the episode's own rate (knee s=1) while
   the vision pool violates it at that same rate (p99 5.4 s at 29% util).

## Planner-config mapping for 3.2 (when it runs)

`dynamo.replay --planner-config` (advisory, `mode: agg`) with
`ttft_ms: 500, itl_ms: 50` (defaults, stated explicitly in the config for
the record); source-built runtime (`REPLAY_PY=.../dynamo/.venv/bin/python
AIC_VER=0.19.0`). Adjustment-interval and scaling bounds to be fixed when
3.2 runs.

**Perf-model bootstrap (decided 2026-07-08): AIC interpolation.** DynoSim
has two "tuning" surfaces. (1) Engine timing — already solved: AIC-backed
mocker timing replaces the profile-an-engine tuning phase (Phase 2.1,
poly-vs-AIC quantified). (2) The planner's own capacity model — it
bootstraps from self-benchmark → AIC interpolation → profile NPZ → live
FPM regression; we feed it **AIC interpolation from the same h100_sxm
database that times the sim**. Self-consistent and deliberately generous:
the reactive baseline gets a perfect capacity model, so its SLA misses are
attributable purely to reacting late — the effect the thesis isolates. Do
NOT let it fall back to live FPM regression (warm-up holds early decisions
— contaminates short burst windows); warm-start the traffic predictors via
`--load-predictor-warmup-trace` (or document constant-predictor fallback).
The predictive policy's capacity model uses the same AIC source, for
parity across all policies.

## Encoder chunk dispatch: parallel (decided 2026-07-07, user-approved)

The 3.1 smoke test exposed a structural infeasibility: under the Phase-2
dispatch policy (an oversized request's ≤64-image chunks run sequentially
on ONE worker) large frames-class requests carry an intrinsic multi-second
service floor — burst3's delay p99 plateaus at 2,877 ms from C=4 through
C=32 (utilization ≤11%) — so no static OR dynamic worker count can meet
the evaluation SLA on frames-heavy windows. Resolution: **parallel chunk
dispatch** — chunks enter the FIFO as independent units and fan out across
free workers. Physically grounded (images are independent in the encoder;
the batching law prices any forward at its image total). Implemented in
`workload/trace_to_two_pool.py` (new default; `--sequential-chunks`
restores the Phase-2 policy, regression-verified to the millisecond).

Re-derived Phase-2 results under the new policy: burst1 s=1 C=2 delay
p99 5,368→4,957 ms at 29% util (headline burst reversal UNCHANGED);
head2k knee still censored at s=32 (794 ms); LLM curves untouched
(isolation trace). Chapter 6 + intro updated; burst3 becomes feasible at
C=8 (p99 714 ms) — static-optimal is now well-defined everywhere.
Mechanism shift worth quoting: every forward is now ≤315 ms, and the
burst pathology is queue depth (789 s above 1,000 queued images, peak
4,637), not multi-second forwards.

## LLM prefill floor on burst windows: TP is the lever (found 2026-07-07)

The first grid pass found every burst window LLM-infeasible at TP1 for ANY
worker count: TTFT p99 plateaus at ~1,285–1,330 ms from N=4 through N=16
(ITL fine at ~8 ms). Same structural shape as the encoder chunk floor —
a PER-REQUEST service floor, here the prefill latency of giant
frames-class contexts (p99 ≈36k tokens ≈1.3 s of prefill compute on one
H100 at TP1). Replica count cannot shorten one request's prefill; tensor
parallelism can. Confirmed directly: burst6 C=6 N=8 at TP2 → TTFT p99
708 ms (feasible). Consequence for the chapter: **during frames floods the
language pool's binding constraint flips from decode throughput (steady
traffic, ITL-bound, knee s=2) to single-request prefill latency —
requiring a TP change, not replica scaling**. `sweep_grid.py` now searches
(TP, N) with cost = TP×N GPUs (TP rungs pruned by best-cost); the same
plateau evidence is in `results/grid/` TP1 point files. Note
`run_replay.sh` fix: single-worker replays need `--router-mode
round_robin` (kv_router requires >1 workers); behavior-identical at N=1.

## 3.1 static-optimal — tooling ready, grid running

- `simulation/derive_windows.py` → `simulation/windows.json`: six burst
  episodes ±10 min (burst1 reproduces the Phase-2 window EXACTLY —
  anchor-asserted) + `steady24h` (calmest full UTC day, 2024-10-20:
  1.02 req/s, 5.4 img/s mean, 88,260 requests).
- `simulation/sweep_grid.py`: per window, two monotone 1-D first-feasible
  searches (`C*` for vision via converter runs, `N*` for LLM via replay on
  the `C*`-shifted trace, AIC timing) + integer bisection + corner
  cross-check (`N*` must stay feasible at the next C rung). GPU-hours per hardware
  class, never summed. Results → `simulation/results/grid/`.

**AIC coverage at giant contexts (probed 2026-07-08).** The shipped
h100_sxm context-attention grid tops out at ISL 16,384; frames-class
requests reach 36k (trace p99) and 148k (max), so ~3% of requests — the
burst-TTFT-critical ones — are priced by extrapolation. Probe
(`query_context_attention`, b=1, 32/8 heads, bf16): beyond-grid latency
tracks the theoretical quadratic to within a few % per octave out to
147k (×2.18 vs 2.2, ×1.75 vs 1.8, ×3.90 vs 4.0, ×5.05 vs 5.1) —
physics-consistent, compute-bound regime; the dominant prefill GEMM term
is collected to m=32,768 and linear beyond. Residual risk: real
long-context kernels degrade slightly super-quadratically → the 1.3 s
prefill floor is if anything underestimated (the TP finding is
conservative), but feasibility MARGINS at boundary configs (e.g. 708 ms
at TP2) carry the extrapolation uncertainty. Document as a limitation in
the baselines chapter; encoder-side queries have no extrapolation by
construction (64-image cap inside the collected envelope).

**Relation to DynoSim Sweep (`replay_optimize`), noted 2026-07-08.** The
official sweep loop is TP search → worker search → **router search**
(overlap-score credit, prefill-load scale) — router tuning is a stage of
the sweep, not a separate offline phase. `sweep_grid.py` deliberately does
NOT reuse it: (1) objective inversion — replay_optimize's descent is
budget-consuming, we minimize GPUs subject to SLA; (2) it has no vision
pool / converter-seam dimension; (3) its SLASpec is mean/p95-oriented, our
SLA is dual-bound p99. Consequence: our "static-optimal" is scoped to
**fixed default routing**. Mitigation before quoting the chapter numbers:
a router-knob sensitivity check at each window's (C*, TP*, N*) corner
(small 1-D sweep over overlap-score credit / prefill-load scale; verify
feasibility verdicts don't flip).

## 3.1 static-optimal — GRID COMPLETE (2026-07-08)

| window | C* | TP* | N* | LLM GPUs | span h | 5090-h | h100-h |
| --- | --- | --- | --- | --- | --- | --- | --- |
| burst1 | 6 | 2 | 2 | 4 | 8.32 | 49.9 | 33.3 |
| burst2 | 8 | 2 | 2 | 4 | 1.90 | 15.2 | 7.6 |
| burst3 | 7 | 2 | 2 | 4 | 0.45 | 3.15 | 1.8 |
| burst4 | 7 | 2 | 2 | 4 | 3.15 | 22.1 | 12.6 |
| burst5 | 16 | 2 | 2 | 4 | 1.35 | 21.6 | 5.4 |
| burst6 | 6 | 2 | 2 | 4 | 1.37 | 8.2 | 5.5 |
| steady24h | 2 | 1 | 2 | 2 | 24.0 | 48.0 | 48.0 |

Every burst window converges on the same LLM shape (TP2×N2 = 4 H100s,
prefill-floor-driven); only the encoder count varies (6–16). Headline:
the all-windows static config is **16 encoders + TP2×2 LLM** vs the calm
day's 2 + TP1×2 — **8× vision-fleet and 2× LLM-fleet overprovisioning on
steady traffic**, and the fleets differ in SHAPE (TP2 vs TP1), which a
reactive replica-scaler cannot morph. All corner cross-checks passed.
Results: `simulation/results/grid/grid_summary.json` (101 points).
**Provenance note (2026-07-08):** vision phase re-derived after the
Phase C ViT-shape infill corrected small-N encoder costs (±6% at
N≤8); exactly one boundary verdict flipped — burst3 C* 6→7 (old
corner read 1,003 ms under corrected data). All other windows and
the headline unchanged; LLM side (h100 data) untouched.
Remaining before chapter-quoting: router-knob sensitivity at corners;
verify the binding LLM config on the other windows (headline note).

## Encoder f(N) batch validation (Phase B, 2026-07-08)

Real-ViT measurement of f(N) for every N in 1..128 (no OOM), vs the exact
AIC query path: N=1 reproduces the chapter's attributed 1.43×; the ratio
GROWS to 1.62 at N=64 / 1.66 at 128 — per-image unmodeled terms
(patch-embed conv, DeepStack glue, kernel variants) that the N=1 ledger
covered but whose growth is unattributed. Decoupling/reversal findings are
scale-robust; absolute C* carries an AIC-optimistic vs HF-eager-pessimistic
band. Artifacts + follow-ups (N=64 kernel profile, `--encoder-cost-scale`
sensitivity, upstream note): `collector_artifacts/phaseB_batch_validation/`.

**Corner re-verification (2026-07-08, final):** after the Phase C infill
regenerated the encoder-shifted traces, all 14 LLM corner/cross-check
replays were re-measured on the corrected traces (7 windows, parallel):
**no verdict changed**, zero failures. The 3.1 table above is now
end-to-end consistent with the grid-exact database.

## 3.2 planner-in-the-loop: smoke PASSED (2026-07-08)

First planner-in-the-loop replay on the source build (head2k, mode=agg,
environment=virtual, advisory, load-scaling only, constant predictor,
60 s interval): exit 0, **12 planner ticks** (720 s / 60 s ✓), diagnostics
HTML + gzipped decision log emitted (`aiconfigurator/planner_reports/`),
report saved. First finding, already thesis-shaped: TTFT p99 **1,872 ms**
under the planner vs 307 ms at fixed N=2 — the replay starts the pool at
min_endpoint and the ±1-per-interval reactive loop lags the load. The
report natively integrates `decode_worker_seconds` (784.2 s over the
720 s window = mean 1.09 workers) — GPU-hours accounting is built in.

**Source-venv dependency gotcha (record for reruns):** the planner stack
imports, none shipped in the source dev venv: `scikit-learn`,
`prometheus-api-client`, `plotly`, `pmdarima`, `filterpy`, `prophet`
(+ pulls `statsmodels`). All installed 2026-07-08. The pinned wheel
bundles these; the source build does not.

**AIC bootstrap spec (for the full runs):** `aic_interpolation` takes
{hf_id, system, backend, isl, osl, sweep_max_context_length,
prefill/decode_interpolation_granularity, prefill_pick, decode_pick} —
all required; wire h100_sxm/vllm + trace-representative isl/osl.

Remaining for full 3.2: parse the decision-log timeline; per-window runs
(arima predictor + `--load-predictor-warmup-trace`, both loops on);
encoder-pool reactive policy = the C(t) worker-schedule mechanism in the
converter (BUILD ONCE — 4.3's predictive controller needs the same hook).

## Open (rest of Phase 3)

- 3.1 close-out: router-knob sensitivity at corner configs; binding-config
  verification on all windows; encoder-cost-scale (or measured-f(N)-table)
  sensitivity re-derivation. Natural first cargo for the E2B pilot.
- 3.2 reactive planner through the same windows (AIC-bootstrapped perf
  model; predictor warm-start; see decisions above).
- 3.2 reactive planner through the same windows; record scaling actions,
  compliance (evaluation SLA), GPU-hours.
