# Closed-loop predictor benchmark v2 (redesigned)

**Branch:** `exp/dynamo-predictor-closedloop-v2`
**Date:** 2026-07-09
**Question:** Does the choice of Dynamo's shipped load predictor (arima / kalman / prophet)
change the SLA planner's closed-loop scaling schedule and the served-latency distribution?

## Why v2 (what the prior version got wrong)

A prior run on the **burst3** LLM window put all three predictors through the offline planner
and got **byte-identical p99 TTFT (3494.725887 ms)** for all three, then wrongly claimed
"forecaster-invariant, hypothesis CONFIRMED." That was **invalid**:

- **(a) Metric saturation** — on burst3 p99 TTFT is pinned by the single worst long-prefill,
  which a 2↔1 replica wobble cannot move; even real schedule differences can't show in the
  headline metric.
- **(b) Predictor collapse** — on the short in-window history ARIMA degenerated to order
  (0,0,0) = "predict the mean"; all three behaved near-identically for lack of history.
- **(c) Over-claim** — identical p99 proves the *metric* is insensitive, not that the
  *predictors* are equivalent.

## Redesign (this run)

- **Windows.**
  - `steady24h` — decode-bound, 24 h, 88 260 requests, mean 1.02 req/s. Decode-bound ⇒ **ITL**
    (not the prefill-floor TTFT) is the binding metric, and replica count moves ITL; 24 h of
    in-window history lets predictors differentiate. Trace: `grid_steady24h_C2.jsonl`, TP1, N=2
    (`tp_star=1, n_star=2` from `grid_summary.json`).
  - `burst4` — 3.15 h, slower 60-min onset, 25 639 requests. The gentle onset gives predictors
    room to diverge without burst3's prefill-floor saturation. Trace: `grid_burst4_C7.jsonl`,
    TP2, N=2 (`tp_star=2, n_star=2`).
- **Metrics.** Full distribution p50/p75/p90/p95/p99 for **both** TTFT and ITL, plus mean TTFT/ITL
  (sensitive where percentiles tie), `decode_worker_seconds`, `gpu_hours`, the **scale-action count**
  and the **worker-count timeline** parsed from the run log's `_compute_scale_decision` lines.
- **Predictor history.** The 24 h window itself supplies the history (~5760 load-scaling ticks at
  15 s cadence) — see the finding on the warmup knob below.
- **Configs.** Three variants of `riders44/planner_ladder_t200_20.json` differing **only** in
  `load_predictor` ∈ {arima, kalman, prophet}. SLA thresholds: TTFT ≤ 200 ms, ITL ≤ 20 ms;
  `max_gpu_budget=8`, `min_endpoint=1`; agg mode.

### Two harness facts verified before trusting the runs

1. **`advisory` does NOT suppress actuation in offline replay.** The config's `advisory:true` (and
   the hard-coded `planner_config.advisory = True` at `dynamo/replay/main.py:433`) only gates the
   *live* planner's `_apply_scaling_targets` → `connector.set_component_replicas`
   (`planner/core/base.py:922`). The **offline** path is different: `ReplayPlannerAdapter.on_tick`
   returns `(target_prefill, target_decode)` and the **Rust bridge applies the scaling itself**
   (`planner/offline/replay_adapter.py`, `_compute_scale_decision` runs unconditionally). Verified
   empirically: the runs actuate (43 scale actions on steady24h, 87–89 on burst4). So advisory was
   **not** the cause of the prior identical results. We set `advisory:false` in the variants for
   documentation intent; it is overridden to True in replay but the schedule still actuates.
2. **`load_predictor_warmup_trace` is a no-op in the replay entrypoint.** The config field exists
   (`planner_config.py:448`) and the live planner wires it (`base.py:248,267`), but
   `replay/main.py` constructs `ReplayPlannerAdapter` **without** `warmup_observations`
   (`main.py:540`). Predictors therefore start cold and accumulate history *in-window* during the
   replay. On a 24 h window that is ample; on a short window (burst3) it is not — which is exactly
   why the prior short-window run collapsed. **Finding:** to warm Dynamo's replay predictors from
   external history you must extend the entrypoint; the knob alone does nothing here.

## Results

SLA for PASS/FAIL: p99 TTFT ≤ 200 ms **and** p99 ITL ≤ 20 ms (the config's own scaling SLA).

### steady24h (decode-bound, 24 h, TP1 N=2)

TTFT (ms):

| pred    | p50 | p75 | p90 | p95 | p99 |
|---------|-----|-----|-----|-----|-----|
| arima   | 39.3685 | 91.6070 | 264.3457 | 387.0730 | 1111.7423 |
| kalman  | 39.3685 | 91.6023 | 264.3457 | 387.0730 | 1111.7423 |
| prophet | 39.3685 | 91.6081 | 264.3475 | 387.0730 | 1111.7423 |

ITL (ms):

| pred    | p50 | p75 | p90 | p95 | p99 |
|---------|-----|-----|-----|-----|-----|
| arima   | 6.9025 | 7.4548 | 8.2974 | 9.3869 | 32.9876 |
| kalman  | 6.9025 | 7.4548 | 8.2974 | 9.3869 | 32.9876 |
| prophet | 6.9025 | 7.4548 | 8.2974 | 9.3869 | 32.9876 |

Resources & schedule:

| pred    | decode_worker_seconds | gpu_hours | scale_actions | mean_ttft_ms | mean_itl_ms | PASS/FAIL |
|---------|-----------------------|-----------|---------------|--------------|-------------|-----------|
| arima   | 88012.04 | 24.4478 | 43 | 133.192472 | 8.524610 | **FAIL** |
| kalman  | 88015.59 | 24.4488 | 43 | 133.192168 | 8.524609 | **FAIL** |
| prophet | 88012.34 | 24.4479 | 43 | 133.192634 | 8.524620 | **FAIL** |

**Schedules are byte-identical across all three (similarity 1.0, 43 actions each).**
Divergence: decode_worker_seconds spread **3.5 s / 88 000 s = 0.004 %**; mean-TTFT spread
**0.00047 ms**; mean-ITL spread **0.000011 ms**; every reported percentile ties exactly.

### burst4 (slow onset, 3.15 h, TP2 N=2)

TTFT (ms):

| pred    | p50 | p75 | p90 | p95 | p99 |
|---------|-----|-----|-----|-----|-----|
| arima   | 60.1807 | 452.1027 | 810.9707 | 1230.4101 | 2783.9918 |
| kalman  | 60.1001 | 451.0558 | 811.2684 | 1231.8111 | 2775.7637 |
| prophet | 60.4125 | 456.0858 | 813.6902 | 1234.9363 | 2783.9918 |

ITL (ms):

| pred    | p50 | p75 | p90 | p95 | p99 |
|---------|-----|-----|-----|-----|-----|
| arima   | 4.5308 | 5.2517 | 6.7359 | 9.2037 | 151.3748 |
| kalman  | 4.5326 | 5.2625 | 6.7382 | 9.2311 | 151.3450 |
| prophet | 4.5338 | 5.2682 | 6.7685 | 9.2813 | 151.6377 |

Resources & schedule:

| pred    | decode_worker_seconds | gpu_hours | scale_actions | mean_ttft_ms | mean_itl_ms | PASS/FAIL |
|---------|-----------------------|-----------|---------------|--------------|-------------|-----------|
| arima   | 14835.13 | 8.2417 | 89 | 311.805905 | 8.620271 | **FAIL** |
| kalman  | 14770.01 | 8.2056 | 89 | 311.814219 | 8.624803 | **FAIL** |
| prophet | 14704.95 | 8.1694 | 87 | 312.873684 | 8.650275 | **FAIL** |

**Schedules genuinely diverge — three distinct schedules** (similarity arima↔kalman 0.854,
arima↔prophet 0.909, kalman↔prophet 0.909). Divergence: decode_worker_seconds spread **130.2 s**
(monotone arima > kalman > prophet); mean-TTFT spread **1.07 ms**; mean-ITL spread **0.030 ms**;
p99-ITL spread **0.29 ms**. The p99/max **TTFT** tail is pinned by the same scheduling-invariant
worst prefill (`max_ttft_ms = 6193.6327` byte-identical for all three; p99 arima ≡ prophet).

## Are the runs actually distinct? (yes — proof)

The near-identical headlines are a *finding*, not a mistake. Independent evidence the three runs
used three different predictors and produced three different decision streams:

- Only the arima runs emit `ARIMA selected order=...` lines; kalman and prophet emit **zero**.
- The predictors' raw forecasts differ at the same trace instant, e.g. steady24h first non-idle
  prediction: arima `num_req=121.60`, kalman `num_req=85.77`; burst4: arima `165.00`, kalman
  `233.96`. These come straight from `predict_next()`.
- On burst4 the resulting **scale schedules differ** (89 / 89 / 87 actions, similarity 0.85–0.91)
  and worker-seconds differ by 130 s.

**ARIMA did not collapse here.** On steady24h it selected varied orders — (0,0,1), (1,0,0) — and
where raw hit (0,0,0) the built-in **log1p fallback** engaged (AIC 42.7 → −11.9). So prior
invalidity cause (b) is fixed on this window.

## Honest conclusion

- **Predictor CHOICE is second-order on these two traces.** The three classical predictors compute
  genuinely different forecasts, but the SLA→replica mapping quantizes those differences onto a
  coarse replica boundary (demand only ever crosses the 1↔2 line). On **steady24h** the different
  forecasts collapse to a **byte-identical** 43-action schedule and byte-identical served
  percentiles (worker-seconds differ 0.004 %). On **burst4** the slower onset lets the schedules
  actually split (3 distinct schedules, worker-seconds spread 130 s / 0.9 %), but all three still
  land within ~1 ms of mean TTFT and **FAIL the SLA together**.
- **This does NOT prove the predictors are equivalent in general** — it shows that on these
  demand shapes, at this replica granularity and SLA margin, their differences do not change the
  binding outcome. The forecasts *do* diverge upstream; the divergence is washed out downstream.
- **This does NOT by itself prove the conversion (encoder-shift / two-pool trace construction) is
  the defect.** Predictor-invariance of the *schedule outcome* is consistent with several causes
  (coarse replica granularity, wide SLA margin, demand that rarely crosses a boundary); it does not
  single out the conversion. What v2 *does* establish, that v1 could not: the metrics now **can**
  see predictor differences (worker-seconds, means, and the burst4 schedule all move), and even so
  the outcome is invariant — a far stronger statement than v1's saturated byte-identical p99.
- **Both windows FAIL the tight 200 ms / 20 ms SLA identically**, regardless of predictor.

## Files

- `configs/planner_{arima,kalman,prophet}.json` — the three variants (differ only in `load_predictor`).
- `run_one.sh` — driver for one (predictor, window) cell.
- `analyze.py` — extracts the tables, schedules, and divergence stats; writes `analysis_summary.json`.
- `ANALYSIS.txt` — captured analyzer output.
- `analysis_summary.json` — machine-readable divergence summary.
- `{steady24h,burst4}/{arima,kalman,prophet}.report.json` — full aiperf reports (74 keys each).
- `{steady24h,burst4}/{arima,kalman,prophet}.planner.log` — compact planner-decision log (schedule,
  predicted-load, ARIMA orders, scaling decisions, final metrics table).
- `{steady24h,burst4}/{arima,kalman,prophet}.log.gz` — full raw run log (archival).

## Reproduce

```
REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python AIC_VER=0.19.0 STARTUP_TIME=60 \
  simulation/results/predictor_closedloop_v2/run_one.sh <arima|kalman|prophet> <steady24h|burst4>
python3 simulation/results/predictor_closedloop_v2/analyze.py
```

Note: `run_replay.sh` `exec`s the replay process, which exits non-zero during interpreter teardown
**after** writing the full report.json + metrics table (a benign atexit/loop-close artifact, no
traceback). `run_one.sh` treats a valid report.json as success regardless of that exit code.
