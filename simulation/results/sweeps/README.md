# Phase 2.3 — saturation-knee load sweeps (2 encoder × 2 LLM workers)

Arrival-speedup sweeps on the Azure LMM trace, run pool-by-pool so each pool's
saturation knee is measured in isolation. Produced by `simulation/sweep_load.py`
(runs) + `simulation/sweep_fig.py` (figure). Machine-readable rollup:
`summary.json`; figure: `knees.png`.

**Headline (the decoupling argument, in simulation):** the two pools saturate at
different offered loads on the *same* trace — and in *opposite order* depending
on the window. On the steady head the language pool knees at s=8 (poly; s=4 at
AIC timing) while the vision pool is still under threshold at s=32. On the
burst episode the vision pool is already over threshold at s=1 (its offered
116 img/s hides 370 img/s peak minutes) while the language pool holds to s=2.
No scalar "load" predicts both pools; each knee lives on its own axis
(req/s + tokens vs img/s).

## Setup

- **Windows** (row offset / count into the ts-sorted trace CSV):
  - `head2k` — offset 0, n=2000. Steady head: 2.774 req/s, 7.99 img/s, horizon 721 s.
  - `burst1` — offset 843072, n=64804. Largest EDA burst episode
    (`analysis/trace_eda/i_burst_anatomy_stats.json` top6_by_peak[0], baseline
    span 2024-10-21 13:09→21:08, peak 370.18 img/s @ 19:53) padded ±10 min →
    [12:59:00, 21:18:00) UTC. 2.165 req/s, 116.17 img/s, horizon 29 939 s;
    input_length p50/p90/max = 1139 / 27 092 / 121 188 tokens (image-token heavy).
- **Speedup mechanics** (offered load = s × base, verified to scale within 2%):
  - LLM pool: **native** `dynamo.replay --arrival-speedup-ratio s` on the s=1
    isolation trace (`traces/llm_<window>.jsonl`, converter `--no-encoder-shift`);
    the Rust core divides every trace timestamp by s. One replay per point via
    `run_replay.sh`, 2 offline kv_router workers.
  - Vision pool: converter `--arrival-speedup s` per point (inter-arrival gaps
    ÷ s before the FIFO encoder sim; 2 workers, cross-request batching ≤64 img,
    448² AIC rtx_5090 costing). The `.stats.json` is the measurement — no replay.
- **Knee rule** (thresholds are **placeholders pending Phase 3 SLA definitions**):
  largest swept s with metric under threshold — vision: encoder delay p99
  < 1000 ms and not queue-divergent; llm: TTFT p99 < 2000 ms.

## Curves (knee metric per speedup)

### Language pool — TTFT p99 (ms) vs offered req/s

| curve | s=1 | s=2 | s=4 | s=8 | s=16 | s=32 | knee | first-over |
|---|---|---|---|---|---|---|---|---|
| head2k · poly | 249 (2.77 rps) | 277 | 473 | **1366 (22.2 rps)** | 23 729 | 42 975 | **s=8** | s=16 |
| head2k · aic  | 307 (2.77 rps) | — | **882 (11.1 rps)** | — | 40 163 | — | **s=4** | s=16 |
| burst1 · poly | 910 (2.17 rps) | **1458 (4.33 rps)** | 8743 | 1 428 028 | — | — | **s=2** | s=4 |

Throughput cross-check: measured rps tracks offered until the knee, then
collapses (head2k s=16: 21.7 vs 44.4 offered; burst1 s=8: 12.1 vs 17.3).
AIC timing knees one octave earlier than the polynomial default (882 ms at the
load where poly reads 473 ms) — the calibrated tails matter.

### Vision pool — encoder delay p99 (ms) vs offered img/s (AIC-costed)

| curve | s=1 | s=2 | s=4 | s=8 | s=16 | s=32 | knee | first-over |
|---|---|---|---|---|---|---|---|---|
| head2k | 200 (8.0 img/s) | 200 | 200 | 200 | 372 | **811 (255.5 img/s)** | **s=32 (censored — never crossed)** | — |
| burst1 | 5368 (116.2 img/s) | 25 479 | 1.50 M | 4.90 M | 6.72 M | 7.64 M | **none (over at s=1)** | s=1 |

head2k utilization stays ≤66% at s=32; the p99 is service-time-dominated until
s≥16. burst1 utilization: 29% (s=1) → 97% (s=4) → 100%; at s=1 the mean load is
comfortably under capacity but the ~20-minute 300+ img/s peak builds a backlog
that alone pushes p99 to 5.4 s — burst shape, not mean rate, saturates the pool.
(`queue_divergent` never fires because the FIFO always drains after arrivals
stop; utilization + the drain tail `vision_sim_end_s − sim_horizon_s` carry the
saturation signal, e.g. burst1 s=32 drains 8576 s for a 936 s window.)

### Decoupling per window

| window | vision knee | llm knee (poly) | verdict |
|---|---|---|---|
| head2k | ≥ s=32 (>255 img/s, censored) | s=8 (22.2 req/s) | knees differ ≥4× (≥8× vs AIC): language pool saturates first; at the llm knee the vision pool sits at 200 ms p99, 18% util |
| burst1 | < s=1 (≤116 img/s) | s=2 (4.33 req/s) | knees differ ≥2× in the **opposite** direction: vision saturates below the trace's own rate while llm has ≥2× headroom |

## Files

- `<pool>_<window>_<timing>_s<speedup>.json` — one point each: offered load +
  latency percentiles (+ throughput for llm; utilization/divergence for vision).
- `summary.json` — all points, curves, knees, decoupling verdicts, sanity checks
  (offered-scaling ≤2%, per-curve monotonicity, exit codes — all green).
- `traces/llm_<window>.jsonl(.stats.json)` — s=1 LLM-isolation mooncake traces.
- `traces/vision_<window>_s<s>.jsonl(.stats.json)` — converter output per vision point.
- `series/vision_<window>_s<s>.series.json` — per-second vision-pool series
  (arrivals/completions/queue depth/busy workers on the compressed clock).
- `reports/llm_*.report.json` — full dynamo.replay reports; `logs/` — run logs.
- `knees.png` — the two-panel figure (left llm, right vision; ringed dots =
  knees; dashed line = placeholder threshold).

## Re-run

```bash
cd /home/gio/tese/simulation
# idempotent: existing point JSONs are skipped (--force reruns)
python3 sweep_load.py --pool llm    --window head2k --timing poly --speedups 1 2 4 8 16 32
python3 sweep_load.py --pool llm    --window head2k --timing aic  --speedups 1 4 16
python3 sweep_load.py --pool llm    --window burst1 --timing poly --speedups 1 2 4 8
python3 sweep_load.py --pool vision --window head2k --speedups 1 2 4 8 16 32
python3 sweep_load.py --pool vision --window burst1 --speedups 1 2 4 8 16 32
python3 sweep_load.py --summary-only            # rebuild summary.json only
/home/gio/tese/eda/.venv/bin/python sweep_fig.py  # knees.png (needs matplotlib)
```

Thresholds: `--vision-p99-threshold-ms 1000 --llm-ttft-p99-threshold-ms 2000`
(defaults; placeholder SLAs). Workers: `--llm-workers 2 --encoder-workers 2`
(defaults). Custom window: `--window custom --offset O --max-requests N`.
