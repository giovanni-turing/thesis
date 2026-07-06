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

## Phase 1 — Azure trace → two-pool workload — NEXT

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

## Phase 2 — Fidelity upgrades to the two-pool simulation

**Goal**: make both pools' timing defensible, not just plumbed.

1. **Language-pool AIC timing**: wire h100_sxm AIC engine timing into
   `dynamo.replay`. Decision point (blocker for 2 and 3b): the PyPI `ai-dynamo`
   wheel used in the minimal test predates `agentic_mooncake`/`tool_wait_ms`
   and may lack engine-timing AIC and `--planner-config` maturity — evaluate
   building dynamo from source (maturin, per its CLAUDE.md) vs. a newer wheel.
   Resolve this FIRST; it determines the runtime for everything after.
2. **Encoder-pool realism**: per-request image counts and sizes from the trace
   (AIC latency queried per size — the collected sweep covers the shapes),
   batching effects on the encoder (AIC batch dimension), and a documented
   handoff-transfer term (embeddings cross pools; measure or bound it).
3. **Load characterization**: arrival-speedup sweeps on the composed trace to
   locate each pool's saturation knee — needed to place the SLA thresholds and
   to show the pools saturate at different offered loads (the decoupling
   argument, now in simulation).

## Phase 3 — Baselines

**Goal**: the two reference points every autoscaling claim needs.

1. **Static-optimal**: sweep encoder-workers × LLM-workers (and TP shape if
   in scope) under the TTFT/TPOT SLA on the trace → Pareto frontier →
   best-achievable static configuration and its GPU-hours. Tooling: DynoSim
   sweep / `replay_optimize`, or scripted grid over the two-pool pipeline.
2. **Reactive autoscaler**: Dynamo's SLA Planner in simulation
   (`--planner-config` on DynoSim runs) driven by the same trace — the
   established reactive baseline. Record SLA compliance, scaling actions, and
   GPU-hours over time, especially through the burst episodes.

## Phase 4 — Predictive scaling (the contribution) — `predictors/`

**Goal**: show that forecasting each pool's OWN demand signal beats both
baselines during bursts, at equal or lower GPU-hours.

1. **`predictors/predictor.py` = the interface** (file created, currently
   empty): sliding window of per-pool demand in → per-pool forecast out
   (vision pool: image-load series, the signal rate-based scaling cannot see;
   language pool: token-load series). Horizon must exceed replica cold-start
   (tens of seconds to minutes on the thesis's platform).
2. **Backends**: time-series foundation models already staged in `models/`
   (chronos, timesfm, toto) plus cheap baselines (naive last-value, seasonal,
   EWMA) — foundation-model-vs-naive is itself a reportable comparison.
3. **Closed loop**: forecast → provisioning decision (with cold-start lead
   time) → apply to the two-pool simulation → measure SLA compliance ×
   GPU-hours vs Phase 3 baselines, with the six burst episodes as the
   headline scenarios and the ~10× missizing case made quantitative.
4. **Ablations**: forecast horizon vs cold-start time; per-pool signals vs
   request-rate-only (the strawman the thesis argues against); forecast error
   sensitivity.

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
- The dynamo runtime decision (source build vs wheel) gates Phases 2–4; make
  it at the start of Phase 2, not mid-experiment.
- Every phase keeps the audit discipline: scripts + captured results under
  `collector_artifacts/<phase>/`, committed to this repo.
