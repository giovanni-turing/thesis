# Thesis Roadmap — Disaggregated Multimodal Serving with Predictive Autoscaling

Master plan connecting the completed calibration work to the thesis's central
claim: each disaggregated pool of a multimodal serving system must be sized and
forecast on its own demand signal, because the vision stage's work is nearly
decoupled from the request rate a conventional autoscaler watches (constant-
fraction model explains only R² ≈ 0.12 of the image-load series; peak image
load spans 27–291 img/s while peak request rate spans only 2.35–7.05 req/s
across the trace's six largest bursts — a rate-sized vision fleet would be
missized by up to ≈10×, precisely during the bursts).

Architecture (locked): **vision pool = rtx_5090-class consumer silicon** (own
collected AIC data) → **language pool = h100_sxm + vllm 0.22.0** (shipped AIC
data) · **model = Qwen3-VL family** (one shared ViT across 8B/32B/235B) ·
composition via per-request encoder delay folded into LLM-pool arrival times.

Companion file: `rtx5090-aic-onboarding.md` (phase-level detail of Phase 0).
Chapter draft for the completed phase: `tex/aiconfigurator.tex`.

---

## Phase 0 — Calibrated cost model for the vision pool — ✅ DONE

Everything in this phase is complete, committed (this repo + fork), and
written up. Summary of what exists and can be relied on:

- **`rtx_5090` is a real AIC system**: system YAML (specs from observed node
  values, FLOPS at the 2407 MHz boost reference), `SupportedSystems`
  registration, and silicon data — 7,679 encoder-attention cases (0 errors,
  production FlashAttention kernel on SM 120) plus 34,326 unique bf16 GEMM
  rows — all collected inside the pinned `vllm/vllm-openai:v0.22.0` container
  at locked clocks (SM 2407 / mem 14001 MHz). Upstream draft PR:
  ai-dynamo/aiconfigurator#1312.
- **Validation verdict: AIC matched the empirical test.** Standalone extracted
  ViT (`models/Qwen3-VL-8B-ViT`, 576M params, architecturally identical to the
  235B tower) measured on the same GPU at the same clocks, 5×50 iters with 95%
  CIs. The collected attention operator agrees within 3%; the torch.profiler
  kernel ledger closes with no unexplained residual (dispatch gaps 15.3%,
  patch_embed conv 4.8%, DeepStack glue 2.6%, HF-vs-vLLM kernel variants ~12%
  of comparable work). Unmodeled-at-this-phase physical effects are exactly
  the serving-stack phenomena the Mocker/DynoSim phase studies.
- **Two independently valuable findings**: (1) AIC has NO usable fallback for
  encoder timing without collected data — SILICON/HYBRID/EMPIRICAL hard-error,
  SOL is ~5.9× optimistic, and support-matrix VLM "PASS" on such systems means
  text-only costing; (2) unlocked consumer-GPU clocks silently inflate
  collected performance ~17% while leaving validation ratios unchanged.
- **Two-pool minimal composition PASSED**: AIC-costed FIFO encoder-pool sim →
  timestamp-shifted mooncake trace → `dynamo.replay` offline with KV router →
  full AIPerf-style report. Pipeline scripts and report:
  `collector_artifacts/phase9_two_pool/`.

---

## Phase 1 — Azure trace → two-pool workload — ✅ DONE

Delivered as `workload/trace_to_two_pool.py` (commit `6b9bbc1`): per request,
an AIC-costed vision-pool arrival (rtx_5090 silicon, 448 px/image) + an
LLM-pool mooncake row with disjoint `hash_ids`; encoder FIFO delay folded
into the LLM arrival timestamp (`--no-encoder-shift` for the ablation).
Original scope below for reference.

**Goal**: replace the synthetic smoke workload with the real bursty signal the
thesis's motivation is built on, so every downstream experiment runs on the
actual trace.

**Input**: `data/AzureLMMInferenceTrace_multimodal.csv.gz` (Azure multimodal
LLM inference trace — the same trace analyzed in the thesis's trace chapter).

**Work**:
1. Inspect the trace schema (timestamps, per-request image counts/dimensions,
   text input/output token counts) and document it in the converter.
2. Write `trace_to_two_pool.py`: for each request, (a) emit an encoder-pool
   arrival carrying its image count and per-image size; (b) emit the LLM-pool
   trace row with `input_length` = text tokens + post-merge vision tokens
   (size-dependent: (H/32)·(W/32) per image for the Qwen3-VL tower),
   `output_length` from the trace, and disjoint `hash_ids` (no spurious
   cross-image prefix reuse).
3. Decide and document the time-window policy (full trace vs the six burst
   episodes as focused scenarios; likely both — bursts as headline scenarios,
   a longer window for steady-state baselines).

**Deliverable**: converter script + versioned generated traces + a summary of
workload statistics matching the trace chapter's numbers (sanity link between
the two theses' artifacts).

## Phase 2 — Fidelity upgrades to the two-pool simulation — ✅ DONE

Chapter draft: `tex/twopool.tex` (composition + poly-vs-AIC + encoder
realism + saturation knees).

**Goal**: make both pools' timing defensible, not just plumbed.
Progress + results: `phase2-simulation.md`. Runner: `simulation/run_replay.sh`.

1. **Language-pool AIC timing** — ✅ DONE. h100_sxm/vLLM 0.22.0 AIC engine
   timing is live in `dynamo.replay`. The feared blocker was wrong: the pinned
   `ai-dynamo==1.2.1` wheel ALREADY exposes engine-timing AIC (`aic_backend`/
   `aic_system`/... in `replay/main.py` + `mocker/config.py`); it only needed
   `aiconfigurator` co-resident in the replay env (the wheel is cp310-abi3, so
   `uv pip install ai-dynamo==1.2.1` into the aiconfigurator .venv suffices — no
   source build). Poly-vs-AIC delta quantified (AIC: slower decode, ~1.8–1.9×
   heavier max tails, p99 +24% — artifact-corrected by the source build; see
   phase2-simulation.md "Source build"). `agentic_mooncake`/`--planner-config` maturity is a SEPARATE
   axis that only gates Phase 3.2 (SLA Planner) — decide source-build THEN.
2. **Encoder-pool realism** — ✅ DONE (Result C, `phase2-simulation.md`).
   Cross-request batching on AIC's batch dimension (probe: encoder cost is
   exactly f(total images); 1.6× throughput at full batch), oversized-request
   chunking (kills the >64-image extrapolation), analytic handoff bound
   (≈1.6 MB/img bf16 embeddings over a parameterized link), and the
   `--arrival-speedup` / per-second `--series-out` hooks for the sweeps.
   The trace has no image sizes → fixed 448²
   stays, documented (~1.14× conservative vs silicon).
3. **Load characterization** — ✅ DONE (Result D, `phase2-simulation.md`;
   `simulation/sweep_load.py`, `results/sweeps/knees.png`). Knees differ on
   both windows, opposite order: steady head — vision ≥4× the LLM's headroom
   (LLM knee s=8 poly / s=4 aic vs vision ≥s=32); largest burst episode —
   vision saturates at the trace's own rate (p99 5.4 s at 29% mean util;
   frames-class HOL blocking) while the LLM keeps 2× headroom. The decoupling
   argument, now in simulation. Worker-grid sweeps move to Phase 3.1.
4. **Extras banked for Phase 3**: 235B-A22B TP8 spot-check (Result E — same
   knee octave as 8B under the TTFT placeholder, 2× decode; vision side
   family-invariant) · dynamo 1.3.0 source build with release wheel archived
   (`wheels/`, regression-verified; wheel's callback tail artifact corrected
   in chapter + docs) · model-size and runtime axes wired into
   `run_replay.sh` (`AIC_MODEL/AIC_TP/AIC_MOE_TP`, `REPLAY_PY`, `AIC_VER`).

## Phase 3 — Baselines — IN PROGRESS (SLA ✅)

**Goal**: the two reference points every autoscaling claim needs.
Progress + SLA definitions: `phase3-baselines.md`.

0. **SLA — ✅ DECIDED (2026-07-07)**: evaluation SLA (all policies, per
   pool): LLM TTFT p99 < 1 s AND ITL p99 < 100 ms; vision encoder-delay
   p99 < 1 s. Reactive planner keeps its native window-mean 500/50 ms as
   policy config. Knees re-derived from existing sweeps: **LLM is
   ITL-(decode-)bound — knee s=2 both timings on the steady head
   (5.5 req/s), s=1 on the burst; vision unchanged** → steady decoupling
   gap ≥16×; burst reversal exact (LLM meets SLA at 1× where vision
   violates). 235B-TP8 knee: s=1 (decoder scale halves the LLM envelope).
   Chapter 4 updated to the adopted SLA.

1. **Static-optimal**: sweep encoder-workers × LLM-workers (and TP shape if
   in scope) under the TTFT/TPOT SLA on the trace → Pareto frontier →
   best-achievable static configuration and its GPU-hours. Tooling: DynoSim
   sweep / `replay_optimize`, or scripted grid over the two-pool pipeline.
2. **Reactive autoscaler**: Dynamo's SLA Planner in simulation
   (`--planner-config` on DynoSim runs) driven by the same trace — the
   established reactive baseline. Record SLA compliance, scaling actions, and
   GPU-hours over time, especially through the burst episodes.

## Phase 4 — Predictive scaling (the contribution) — `predictors/` — IN PROGRESS (4.1–4.2 ✅)

**Goal**: show that forecasting each pool's OWN demand signal beats both
baselines during bursts, at equal or lower GPU-hours.
Progress + results: `phase4-predictors.md`. Chapter draft: `tex/predictors.tex`.

1. **Interface** — ✅ DONE. `predictor.py`: Bucket (targets + covariates at one
   cadence) → Forecast (point + 9 quantiles); batch executor; clip-at-zero.
2. **Backends + benchmark** — ✅ DONE. Six backends (naive/EWMA/Holt–Winters +
   TimesFM-2.0-500M / Chronos-2 120M / Toto-2.0-2.5B zero-shot) benchmarked
   rolling-origin (H=12, shared origin grid, per-model max context − headroom)
   over all 5 resolutions × 4 signals, uni + native-covariate modes: **FMs beat
   every baseline in all 20 cells** (~⅓ lower WAPE at 1 s); Toto-2 wins fine
   resolutions, Chronos-2 coarse; horizon degradation mild (12 min lead ≈ free,
   covers median 6-min burst onset); covariates ±0.4 % (help only ≤15 s);
   median-point FMs are not improved by any fixed percentile (band = headroom).
   19.2 M forecasts + metrics archived (`predictors/results/`).
3. **Closed loop — NEXT**: forecast → provisioning decision (with cold-start
   lead time) → apply to the two-pool simulation → measure SLA compliance ×
   GPU-hours vs Phase 3 baselines, with the six burst episodes as the
   headline scenarios and the ~10× missizing case made quantitative.
   Note: Phase 2 prerequisites are done; blocked only on the Phase 3
   baselines (the comparison targets).
4. **Ablations**: forecast horizon vs cold-start time; per-pool signals vs
   request-rate-only (the strawman — forecast image load FROM request rate,
   using the covariate machinery); forecast error sensitivity; quantile
   calibration/coverage if p90-headroom provisioning is used.

## Phase 5 — Validation anchor + writing

1. **Live-mocker run** of the winning policy: real Dynamo frontend/router/
   planner code paths against mocked workers (CPU only) — confirms the
   simulated control loop behaves on the real stack.
2. **Optional physical anchor**: the extracted ViT served as one real encoder
   worker on the 5090 under a burst replay — one physical data point tying the
   whole simulation chain to silicon.
3. **Writing**: results chapter(s) mirroring `tex/aiconfigurator.tex` —
   trace-to-workload methodology, baselines, predictive-scaling results,
   validation. Fold the Phase 0 chapter's cross-references and citations when
   integrating into the mestrado build.

---

## Standing decisions & reminders

- Clock locks reset on reboot: relock (`nvidia-smi -lgc 2407,2407 -lmc
  14001,14001`, persistence on) before any GPU measurement session.
- GPU is shared with the RAG stack: `docker compose -p mmrag stop qwen-embed
  qwen-rerank` (dir `/home/gio/claude`) before GPU work; `start` to restore.
- ~~The dynamo runtime decision (source build vs wheel)~~ **RESOLVED: built
  from source** (dynamo 1.3.0, repo `.venv`; recipe
  `simulation/build_dynamo_src.sh`, regression + gotchas in
  `phase2-simulation.md` "Source build"). Phase 3.2 SLA-Planner +
  agentic_mooncake unblocked. Source runs: `REPLAY_PY=.../dynamo/.venv/bin/
  python AIC_VER=0.19.0` (rust AIC path needs the reuse-resolved version);
  wheel env untouched for Phase-2 reproducibility.
- Every phase keeps the audit discipline: scripts + captured results under
  `collector_artifacts/<phase>/`, committed to this repo.
