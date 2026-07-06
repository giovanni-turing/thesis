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

## State

- Phase 1 ✅ real trace → two-pool converter, validated end-to-end.
- Phase 2.1 ✅ h100 AIC language-pool timing live; poly-vs-AIC delta quantified.
- Phase 2.2/2.3 next: encoder batching/handoff realism, then arrival-speedup
  load sweeps to locate each pool's saturation knee (where decoupling shows).

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

