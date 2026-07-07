# Phase 2 — Two-pool simulation: fidelity upgrades

Companion to `thesis-roadmap.md` (Phase 2) and `phase1-trace-eda.md`. Records
the move from the phase-9 smoke test to real-trace, AIC-timed simulation, and
the results obtained so far.

Working tree: `workload/trace_to_two_pool.py` (converter, Phase 1) +
`simulation/` (run driver + results). All runs use a 2000-request head window
of the Azure trace (horizon ~721 s, 37% text-only, 8.0 img/s mean).

---

## Combined environment (Phase 2.1 unblock)

The roadmap flagged "dynamo source-build vs wheel" as a Phase-2 blocker. It is
**not** a blocker for AIC engine timing: the pinned `ai-dynamo==1.2.1` wheel
already exposes the engine-timing AIC surface (`aic_backend`, `aic_system`,
`aic_model_path`, `aic_tp_size`, `aic_backend_version` in `replay/main.py` and
`mocker/config.py`). It only failed in phase-9 because `aiconfigurator` was not
importable from the replay venv, and `dynamo._internal.aic.create_session`
needs the SDK in-process.

Fix (option A): add `ai-dynamo==1.2.1` into the aiconfigurator uv `.venv`. The
runtime wheel is `cp310-abi3`, so it loads on that env's Python 3.13; the
install is purely additive (42 new packages, zero downgrades of aiconfigurator
deps — restorable with `uv sync`). Now one interpreter has both the SDK (+ the
`h100_sxm/vllm/{0.14,0.19,0.22}.0` data on disk) and dynamo.replay.

Source-build only resurfaces later for the **SLA-Planner** baseline (Phase 3.2)
and `agentic_mooncake`/`tool_wait_ms` — a separate maturity axis from
engine-timing AIC.

Reproduce any run: `simulation/run_replay.sh <trace> <poly|aic> <report> [workers]`.

---

## Result A — Language-pool timing: polynomial vs AIC h100

LLM-pool **isolation** (raw trace arrivals, no encoder handoff; generated with
`trace_to_two_pool.py --no-encoder-shift`), 2 offline kv_router workers. Same
trace, same topology — only the mocker's timing model changes.

| Metric | Polynomial (default) | AIC h100 vLLM 0.22.0 |
|---|---|---|
| TTFT avg / p99 / max (ms) | 67.3 / 248 / 2,540 | 72.7 / 307 / 7,598 |
| Request latency avg / p99 (ms) | 1,413 / 6,879 | 1,609 / 8,850 |
| Inter-token latency avg / max (ms) | 6.79 / 181 | 7.75 / 847 |
| Output tok/s/user (avg) | 160.6 | 141.7 |
| Request throughput (rps) | 2.77 | 2.77 (arrival-paced) |

AIC gives **slower per-user decode (142 vs 161 tok/s) and much heavier tails**
(TTFT max 3×, ITL max 4.7×) — the calibrated model exposes burst behavior the
polynomial default flattens. `Wall Time` jumps 0.33 s → 32 s because AIC
predicts every request instead of evaluating a polynomial (proof the session is
live, not silently falling back).

**Two-pool vs one-pool (isolation) are nearly identical in this window**
(poly TTFT 67.2 vs 67.3; AIC 72.2 vs 72.7): encoder delay (p50 7.8 ms, max
591 ms) is small against the ~360 ms mean inter-arrival at 2 encoder workers, so
the vision handoff barely shifts LLM-pool load *here*. The decoupling argument
therefore lives in the **burst episodes / higher offered load**, not this steady
window — a load sweep (Phase 2.3) is needed to surface it.

---

## Result B — Vision-pool fidelity: simulator vs measured, like-for-like

The simulator (AIC ViT graph) models a specific op inventory and, **by design,
does not model** patch-embed conv, DeepStack concat/glue, or inter-kernel
dispatch/launch gaps. A fair simulator-vs-silicon comparison removes those terms
from the measured wall-clock first. Source: `collector_artifacts/phaseA_validation/`
(RTX 5090, locked clocks, HF Qwen3VLVisionModel bf16, 5×50 iters, 95% CI).

Per image @ 448² (784 patches):

| Quantity | Latency (ms) | vs AIC |
|---|---|---|
| **AIC prediction (simulator)** | **7.822** | — |
| Measured wall-clock (raw) | 11.360 | 1.45× |
| − dispatch/launch gaps (1.736, not modeled) | 9.624 | 1.23× |
| **− patch_embed conv (0.459) − DeepStack glue (0.248)** | **8.917** | **1.14×** |
| Attention op alone (the collected quantity) | 1.300 vs AIC 1.342 | within 3% |

Stripping the by-design-unmodeled preprocessing brings agreement to **~12–14%**,
fully attributed to HF-vs-vLLM kernel-variant selection and unfused elementwise
— not an error in the cost model. The raw 1.45× overstates the gap by charging
AIC for work it never claims to model. At 896²/1344² the *raw* ratios are
already 1.14/1.16× because those fixed preprocessing terms are a smaller
fraction of a larger forward — consistent with the same story.

Implication for the workload sim: the encoder service time the converter feeds
is AIC's ~7.8 ms; a physically-faithful encoder would be ~1.14× higher on
comparable work (more on preprocessing-heavy small images). This is a bounded,
documented under-estimate of vision-pool load — conservative for the decoupling
argument, and a knob to sweep.

---

## Result C — Phase 2.2: encoder batching + handoff realism (converter)

The converter's vision pool is now an event-driven FIFO with cross-request
batching on AIC's batch dimension, a handoff-transfer bound, an
`--arrival-speedup` load knob, and a per-second `--series-out` series.
Probe-backed simplification: AIC's encoder prediction is EXACTLY a function of
total images per forward — (batch_size=1, n=64) ≡ (64, 1) ≡ every factoring,
delta 0.000000 ms — so batches are costed by their image total. f(1)=7.822 ms
vs f(64)=314.498 ms ⇒ 4.91 ms/img amortized (~1.6× throughput at full batch,
~2.9 ms fixed per-forward overhead). Oversized requests (>64 images, up to
9409) are chunked into sequential ≤64-image forwards on one worker —
eliminating the old AIC batch-axis extrapolation. Handoff bound: post-merge
embeddings (196 tok/img × 4096 × bf16 ≈ 1.6 MB/img) at `--handoff-gbps` 25 +
0.2 ms RTT ≈ 0.71 ms/img-request at p50; 62 ms for a 121-image request; async
(not worker-occupying). Validation: isolation JSONL byte-identical to Phase 1;
delay percentiles unchanged at the idle 2k head (p50/p90/p99 exactly equal;
max +5.9 ms from chunking the one 121-image request); replay smoke TTFT avg
67.13 ms vs Result A's 67.2.

## Result D — Phase 2.3: saturation knees — the decoupling, in simulation

`simulation/sweep_load.py` sweeps arrival speedup per pool (LLM: native
`dynamo.replay --arrival-speedup-ratio` on the isolation trace; vision:
converter `--arrival-speedup`), 2 encoder × 2 LLM workers, placeholder SLA
thresholds (TTFT p99 < 2 s, encoder delay p99 < 1 s). 25 points, all sane
(offered scaling exact, curves monotone). Figure:
`simulation/results/sweeps/knees.png`; data: `summary.json`.

| Curve | knee | first-over | metric at s=1 → knee |
|---|---|---|---|
| llm · head2k · poly | s=8 (22.2 req/s) | s=16 | TTFT p99 249 → 1,366 ms |
| llm · head2k · aic  | s=4 (11.1 req/s) | s=16 | 307 → 882 ms |
| llm · burst1 · poly | s=2 (4.3 req/s)  | s=4  | 910 → 1,458 ms |
| vision · head2k     | s=32 (256 img/s, censored — never crossed) | — | 200 → 811 ms |
| vision · burst1     | **none — saturated at s=1** (116 img/s mean) | s=1 | p99 5,368 ms |

**The pools' knees differ on both windows, in opposite directions.** On the
steady head the vision pool has ≥4× (vs poly; ≥8× vs aic) the LLM pool's load
headroom. On the burst episode the vision pool violates its SLA at the trace's
own recorded rate — p99 encoder delay 5.4 s at only **29% mean utilization** —
while the LLM pool still has 2× headroom. Mechanism (from the per-second
series): 7,716 frames-class requests are chunked (>64 images; batch service
p90 2.4 s, max 6.0 s) and the peak second lands 975 images at once — the queue
reaches 4,452 images and stays >1,000 for 417 s of the 8.3 h window. Episodic
FIFO head-of-line blocking at low mean utilization: invisible to request-rate
(2.2 req/s mean) or mean-utilization monitoring, exactly the provisioning gap
the predictive-scaling contribution targets.

## Result E — 235B-A22B at TP8: the model-size spot-check

The family flagship, priced on the same shipped h100_sxm/vLLM 0.22.0 data
(`Qwen3VLMoEModel`, tp=8 + moe_tp=8), on the same head2k isolation window and
topology — via `run_replay.sh` env overrides (`AIC_MODEL`, `AIC_TP`,
`AIC_MOE_TP`; defaults unchanged = 8B/TP1). Results: `simulation/results/235b/`.

| s (offered) | 8B-TP1 TTFT mean/p99 (ms) | 235B-TP8 TTFT mean/p99 (ms) | 235B TPOT / tok/s/user |
|---|---|---|---|
| 1 (2.8 req/s) | 73 / 307 | 124 / 398 | 14.9 ms / 86.9 |
| 4 (11.1 req/s) | 140 / 882 | 329 / 1,402 | 87.9 ms / 25.8 |
| 16 (44.3 req/s) | 17,336 / 40,163 | 27,354 / 61,438 | 158 ms / 15.6 |

Reading: under the placeholder TTFT p99 < 2 s target the 235B-TP8 knee sits in
the same swept octave as the 8B (s=4), with ~1.6× higher p99 at the knee and
2× the decode latency everywhere (a TPOT/ITL-based SLA would bind earlier for
the 235B). The steady-window decoupling gap vs the vision pool (knee ≥ s=32)
is therefore ≥8× for the flagship too, and the burst-window direction is
untouched — the vision pool (ViT + projector→4096 shared between 8B and 235B,
Phase 0) saturates below the trace's own rate regardless of decoder size.

## Source build — Phase 3.2 unblocked (decision resolved: build from source)

dynamo **1.3.0** built from the local checkout into its repo `.venv`
(`simulation/build_dynamo_src.sh` = the reproducible recipe; aiconfigurator
installed editable alongside — the reverse co-residence of Phase 2.1). The
pinned wheel env is untouched, so all Phase-2 results stay reproducible;
`run_replay.sh` switches runtimes via `REPLAY_PY` (default = wheel).
Environment fixes baked into the recipe: user-level `protoc` 29.3
(`~/.local/protoc`, etcd-client build script), `BINDGEN_EXTRA_CLANG_ARGS`
pointing at GCC-13's freestanding headers (libclang-18 ships without its
resource headers; nixl-sys bindgen needs `stdbool.h`), and
`maturin develop --features aic-forward-pass` (the engine-timing AIC callback
is feature-gated; the PyPI wheel ships it, default features do not).

Feature surface verified on `dynamo.replay --help`: `--planner-config`
(advisory agg/disagg), `agentic_mooncake` trace format,
`--arrival-speedup-ratio`, full `aic_*` engine args incl. MoE.

One data-path difference: the source build's AIC runs in **Rust**
(aiconfigurator-core) and reads perf parquet directly — it does not resolve
the `SHARED_LAYER_REUSE` marker, so h100_sxm/vllm **0.22.0 must be requested
as 0.19.0** (`AIC_VER=0.19.0`; verified: SDK predictions at 0.22.0 == 0.19.0
exactly, and wheel replay at 0.19.0 == 0.22.0 to <0.1%, max TTFT identical).

Regression, head2k isolation, 2 workers (wheel 1.2.1 vs source 1.3.0):

| Timing | Metric | wheel | source |
|---|---|---|---|
| poly | everything | — | **bit-identical** (TTFT 67.3/248/2,540; TPOT 6.90) |
| aic | TTFT p99 | 307.4 | **307.4 (identical)** |
| aic | TPOT mean | 7.851 | 7.767 (−1.1%) |
| aic | TTFT mean / max | 72.7 / 7,598 | 68.2 / 4,518 |

The bulk of the distribution is identical; the extreme tail is LIGHTER on the
source build. Attribution: the wheel's AIC callback runs per-request Python
SDK predictions in-process (the known 0.33 s → 32 s wall-time inflation of
Result A) and that wall-time bleeds into the simulated tail; the Rust path
predicts in-core in microseconds. Data is ruled out (wheel@0.19.0 ==
wheel@0.22.0, max bit-identical). The source build is the cleaner simulator —
Phase 3+ runs use it (`REPLAY_PY=.../dynamo/.venv/bin/python AIC_VER=0.19.0`);
wheel numbers remain the Phase-2 record.

## State

- Phase 1 ✅ real trace → two-pool converter, validated end-to-end.
- Phase 2.1 ✅ h100 AIC language-pool timing live; poly-vs-AIC delta quantified.
- Phase 2.2 ✅ encoder batching (probe-backed f(total-images) costing),
  handoff bound, speedup + series hooks (Result C).
- Phase 2.3 ✅ per-pool arrival-speedup sweeps + knees on head2k and burst1
  (Result D). Remaining sweep axes (worker grids, six-episode battery, long
  steady window) belong to Phase 3's baseline runs.
- 235B-A22B TP8 spot-check ✅ (Result E): same knee octave under the
  placeholder SLA, 2× decode latency; model-size axis available in
  `run_replay.sh` via env overrides.

Open items: run the six burst episodes + full-trace window (not just the 2k
head); decide encoder resolution/size distribution (currently uniform 448²);
Phase 3.2 gates on the dynamo source-build decision for the SLA Planner.

---

## Full simulation run — plan

Goal: replace the 2k-head smoke window with the runs the thesis actually
reports on — load characterization (Phase 2.3) and the substrate for the
Phase 3 baselines — driven by the real trace at defensible timing.

**Windows** (the 2k head is not representative — it is a steady stretch):
1. **Six burst episodes** (headline scenarios) — offsets/spans from the EDA
   burst onsets (`analysis/trace_eda/i_burst_*`). These are where vision load
   spikes decouple from request rate (27–291 img/s vs 2.35–7.05 req/s). Cheap
   at AIC timing (minutes each).
2. **One long steady window** (≥ a full diurnal cycle) for baseline GPU-hours.
3. **Full trace** (1M req, 168 h) — only if needed; budget below.

**Axes per window**:
- timing: `poly` (coverage) + `aic` (headline fidelity).
- arrival-speedup sweep (`--arrival-speedup-ratio`) → each pool's saturation
  knee. Run the vision pool (converter FIFO) and language pool (replay)
  sweeps separately so the two knees can be shown at different offered loads —
  the decoupling argument, in simulation.
- encoder-workers × LLM-workers grid → the Phase 3 static-optimal frontier.

**Outputs to collect per run** (not just the AIPerf LLM report):
- vision pool: encoder-delay percentiles + images/s series (already in the
  converter `.stats.json`; extend to emit the per-second queue-depth series).
- language pool: the report JSON (TTFT/TPOT/throughput).
- join into SLA-compliance × GPU-hours tables keyed by (window, config, timing).

**Compute budget** (measured: AIC ≈ 16 ms/req, poly ≈ 0.17 ms/req, single
process): full-trace AIC ≈ 4.4 h/config; full-trace poly ≈ 3 min/config; a
burst episode (~5–20k req) ≈ 1–5 min AIC. ⇒ episodes + steady window at AIC are
cheap; reserve full-trace AIC for one or two final configs. Concurrency cap is
disk/CPU, not GPU (mocker is CPU-only) — can parallelize configs.

**Prerequisites / decisions before launching**:
- Finalize the **encoder image model**: keep uniform 448², or draw a size
  distribution (the trace lacks sizes — would be a documented synthetic
  overlay). This scales vision-pool GPU-hours; decide before the sweeps bake it
  in. Fair-comparison note: AIC underestimates comparable ViT work by ~1.14× at
  448² (Result B) — a bounded, conservative bias for the decoupling claim.
- Decide the **>64-image handling** (AIC batch extrapolation; rare rows) —
  cap, or accept with the flag already emitted.
- Decide **full-trace inclusion** vs episodes+steady only (compute budget).
- Phase 3.2 SLA-Planner still gates on the dynamo source-build decision.

