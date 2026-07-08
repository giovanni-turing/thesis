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

**2026-07-08 additions — f(N) validation, shape infill, composition §.**
Post-campaign hardening while Phase 3 ran (details:
`collector_artifacts/phaseB_batch_validation/README.md` + `phaseC_vit_shape_infill/`):

- **Phase B — batch-axis validation**: real-ViT f(N) measured for every
  N∈[1,128] (no OOM; thesis-quoted points re-measured at 5×50, CIs
  ≤±0.3 ms). Measured/model ratio grows 1.37→1.62 over N≤64 (per-image
  unmodeled operators); measured batching gain saturates at N≈6 (1.56×,
  drifting to 1.41×) vs the model's 1.65×-at-64. Conservative direction
  for the thesis's saturation claims.
- **Phase C — targeted shape infill**: the exact ViT query shapes were
  never on the campaign grid (s=784 always interpolated; N≳42 GEMMs in
  the OOM-gap zone). 465-case infill at identical protocol → 448px query
  path now grid-exact (7,760/34,710 rows). Downstream: ch.6 numbers moved
  ≤1%, burst3 C* 6→7 (had sat 3 ms inside the bound). AIC-side commit
  656ac8ca on the PR branch is LOCAL — push awaiting user sign-off.
- **Chapter additions**: §5.3 composition mechanics (model vs measured vs
  lookup-table strata) + model-vs-silicon table; dated infill-correction
  note; all simulation-derived numbers refreshed (build: 65 pp clean).

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
   **⚠ Numbers above are under the old placeholder SLA — superseded by
   Phase 3.0 (adopted SLA): LLM knee s=2 both timings, steady gap ≥16×,
   burst LLM knee s=1 (no 2× headroom). Cite Phase 3.0's numbers, not
   these.**
4. **Extras banked for Phase 3**: 235B-A22B TP8 spot-check (Result E — same
   knee octave as 8B under the TTFT placeholder; under the adopted SLA the
   flagship knee is s=1, one octave below the 8B — see Phase 3.0; 2× decode;
   vision side family-invariant) · dynamo 1.3.0 source build with release wheel archived
   (`wheels/`, regression-verified; wheel's callback tail artifact corrected
   in chapter + docs) · model-size and runtime axes wired into
   `run_replay.sh` (`AIC_MODEL/AIC_TP/AIC_MOE_TP`, `REPLAY_PY`, `AIC_VER`).

## Phase 3 — Baselines — ✅ DONE (2026-07-08: SLA ✅ · 3.1 ✅ · 3.2 ✅)

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

1. **Static-optimal — ✅ DONE (2026-07-08)**: all 7 windows converged
   (results table + provenance in `phase3-baselines.md`). Headline: every
   burst window needs LLM TP2×N2 (4 H100s; TP1 is prefill-floor-infeasible
   at ANY replica count) with encoder `C*` 6–16, vs the calm day's
   2 encoders plus TP1×2 — **8× vision / 2× LLM overprovisioning AND a fleet-shape
   difference (TP2 vs TP1) no replica-scaler can morph**. Derived under
   grid-exact encoder data (Phase C infill; one marginal flip burst3
   `C*` 6→7; LLM corners re-verified on corrected traces, no changes).
   Remaining close-out checks (router-knob sensitivity at corners,
   binding-config verification) fold into the E2B pilot. Original work
   items below for reference:
   (a) grid driver `simulation/sweep_grid.py` extending `sweep_load.py`:
   C_enc ∈ {1,2,3,4,6,8} × N_llm ∈ {1,2,3,4,6,8}, coarse pass then refine
   around the frontier; encoder count is a converter param, LLM count a
   replay param.
   (b) windows: the six burst episodes + one diurnal steady window (same
   episode definitions as the EDA chapter — sanity-link the ids).
   (c) GPU-hours accounting: report **per hardware class** (5090-hours,
   H100-hours) — never summed; add one cost-weighted scalar only as a
   sensitivity note.
   (d) headline: the static config that meets the SLA on *all* windows is
   burst-sized — quantify its calm-traffic overprovisioning (the ≈10×/≥16×
   missizing made concrete).
2. **Reactive autoscaler — NEXT (after 3.1)**: Dynamo SLA Planner
   (`--planner-config`, mode agg, native 500/50 ms window-mean control law;
   source-built runtime per Standing decisions) through the same windows.
   Work items:
   (a) fix adjustment interval + min/max workers in the planner config
   (record in `phase3-baselines.md`);
   (b) **design decision — encoder-pool reactive policy**: the Dynamo
   planner does not see the vision pool, so define the fair reactive
   strawman for it (threshold scaler on window-mean utilization / queue
   depth, same actuation + cold-start lead as 4.3 will use);
   (c) fix the cold-start lead-time parameter set (e.g. 30/60/120 s,
   shared by 3.2 and 4.3 so baselines and contribution are comparable);
   (d) record scaling-action timeline, evaluation-SLA compliance, and
   GPU-hours integrated over the worker-count schedule. The expected
   finding — window-mean control satisfied while tail SLA is violated —
   is a result, not a bug (see `phase3-baselines.md`).
   (e) **Version note (verified in git, 2026-07-07)**: the planner's
   two-loop design (forecast-driven throughput loop with ARIMA/Kalman/
   Prophet + reactive load loop) landed 2026-04 (#8046, first in v1.1.0)
   and IS in the pinned 1.2.1/1.3.0; the pre-v1.1 planner (from v0.3.2,
   2025-06, #1420) was the observed-metrics SLA loop only. Baseline 3.2 =
   the reactive load/SLA loop (what the offline replay adapter feeds).
   **Optional extra comparison** if time allows: enable the throughput
   loop as "Dynamo's own single-signal classical-predictor scaling" —
   a middle rung between reactive and the thesis's per-pool TSFM policy.

## Phase 4 — Predictive scaling (the contribution) — IN PROGRESS (4.1–4.3 ✅, 4.4 NEXT)

**Status 2026-07-08 (details in `phase4-predictors.md`):** 4.3 is
delivered as infrastructure + v1 results — C(t) encoder hook (validated
bit-exact), forecast controller, `forecast_file` planner predictor, the
forecast-vs-reactive head-to-head (reactive fails the 1-min-onset burst
at EVERY cold-start lead, 16–54 s p99, converging to never-scaled;
forecast flat at 588 ms through 300 s lead — regime anticipation), and
the LLM pool SLA-green through the production planner path (knee-scaled
targets). Reactive baselines complete on both pools; four-column
comparison exists per pool. **Standing infrastructure: E2B fleet**
(template `tese-twopool`, driver `simulation/e2b_fleet.py`, exact-parity
certified 12/12; forecast-coverage rule: 1min from Oct 20 14:36, 15s
from Oct 16 09:36, burst2/6 structurally unforecastable).

**NEXT (4.4, fleet):** (a) full matrix — in-span windows × {forecast
p50/p90, reactive} × lead {30,60,120,300 s} × rho {10,15,20,25} × model
{chronos,toto,timesfm} ≈ 400–600 cells; (b) **weekly aggregate** over
the covered span (~5.2 days) → THE headline SLA × GPU-hours number
vs deployable static; (c) LLM principled mapping (mean-capacity/knee
ratio from AIC, replacing the ×8 knob) + LLM runs beyond burst1;
(d) template rev 2 (pip-install source, drop driver shims). Then the
baselines + closed-loop chapters draft from the phase docs and the
intro/thesis-statement placeholders resolve.

(Original phase plan below.)

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
3. **Closed loop — blocked on Phase 3 only**: forecast → provisioning
   decision (with cold-start lead time) → two-pool simulation → SLA
   compliance × GPU-hours vs both baselines on the six burst episodes.
   Planning notes (from the 2026-07-07 review):
   (a) **reuse the archived forecasts** — the 19.2 M-value parquet set
   already contains the stitched per-pool paths + quantiles at every
   cadence; the controller consumes them offline, no re-inference;
   (b) controller: per decision tick (1 min), map forecast demand →
   worker count via each pool's capacity model (encoder: batching-law
   img/s per worker at the SLA point; LLM: knee-derived req/s per
   worker), headroom policy = point vs p90 (the quantile-band finding);
   (c) **engineering risk — time-varying worker counts**: the encoder
   FIFO needs a worker schedule C(t) with cold-start delay (new workers
   usable after the lead time); the LLM pool should actuate through the
   same planner hook as 3.2 so all policies share actuation mechanics;
   (d) score exactly as 3.1/3.2 (evaluation SLA × per-class GPU-hours);
   (e) **controller architecture (decided 2026-07-07)**: two-tier.
   Headline runs = **offline controller** (standalone script: forecast
   parquet → capacity model + cold-start lag → C(t)/N(t) schedule
   consumed by the two-pool pipeline; identical actuation for all
   policies). Validation (Phase 5.1) = the winning policy **once** as a
   planner PREDICT/PROPOSE plugin behind Dynamo's plugin API, actuated
   via `VirtualConnector` (planner writes decision → sim polls
   `client.wait()` → acks `client.complete()`) against mocked workers.
   The encoder-pool controller mirrors the VirtualConnector decision/ack
   semantics inside the FIFO sim (no native interface exists for a
   vision pool) so both pools share actuation mechanics.
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
3. **Writing** — IN PROGRESS (front matter + all four result chapters
   drafted; closing chapters pending their phases).
   - ✅ Drafted: `tex/intro.tex`, `tex/related.tex`, `tex/trace-eda.tex`,
     `tex/predictors.tex`, `tex/aiconfigurator.tex`, `tex/twopool.tex`;
     workspace build `tex/tese.tex` (61 pp).
   - ✅ Review pass (2026-07-07): bibliography fully web-verified and
     extended to 55 entries (venue upgrades: WarmServe→ICML'26, EPD→ICML'25,
     SageServe→SIGMETRICS'25, BurstGPT→KDD'25, ServeGen→NSDI'26; ModServe
     authors/title corrected; added ElasticMM, TokenScale, HeteroScale,
     Chiron, Aegaeon, BlitzScale, InferLine, Paxson–Floyd, DynamoLLM,
     Time-MoE, Toto/BOOM, LLMServingSim 1/2.0, RServe, HeteroServe, dataset
     cite). Cross-chapter numbers reconciled to the adopted SLA (≥16×
     steady gap; burst reversal; AIC tail ≈2×; intro SLA-placeholder
     resolved). Layout: overfull 29→1 (0.4 pt residual); three figures
     regenerated for label legibility (`c_seven_day_signals`,
     `l_request_clusters`, `sim_knees`).
   - ✅ **Review adjudication (2026-07-08)**: all items of the three
     external review docs (IMPROVEMENTS.md, THESIS-FEEDBACK.md, report.md)
     checked, fixed-or-adjudicated, and marked in place. Highlights that
     CHANGED the thesis text: (a) **H1** — ran the missing LLM/AIC burst
     knee: TP1×2 FAILS at s=1 (1,868 ms vs poly's 910), TP2×2 passes
     (748 ms) → inversion reframed ("both fail at the naive topology,
     differently; at the SLA-shaped TP2 config the original contrast holds
     verbatim"); (b) **H2** — s=3 sweep → "≥16×" replaced by
     "order of magnitude" (poly knee s=3; calibrated s=2, fails s=3);
     (c) coverage computed: **p90 calibrated** (0.88–0.90 @1min, all
     models/signals) — the p90 headroom rule is now evidence-backed;
     (d) placeholders resolved 8/9 (statement, RQ4, contribution 5,
     organization) from the archived 4.3/3.x results; (e) front matter
     (title, abstract+resumo, LoF/LoT/abbreviations), architecture figure,
     f(N)+ledger figure, multi-model burst figure, reproducibility
     appendix, hyperref; (f) stale numbers purged (19.2M→21,404,640;
     83,432→56,510 units/83,376 forwards; 315→316.4; 975→2,726;
     147→148; duplicates retained not dropped; 87→101 windows/87 runs;
     persistence-estimator claim repaired — Hurst=(1+β)/2 identity
     disclosed, decode † quarantined). Build: 92 pp, 0 undefined refs.
     New runs ledgered. Deferred by decision: biblatex migration +
     et-al expansions + PNG→PDF (batched with institutional-template
     switch); global sentence-length pass (final copy-edit).
   - ⬜ Remaining placeholder (1, intentional): validation-anchor sentence
     in intro scope — resolves with Phase 5.1.
   - ⬜ Baselines chapter, closed-loop chapter, conclusion; fold into the
     mestrado build with Phase 0 cross-references. (The intro/related now
     STATE the delivered results with numbers, so the document argues
     end-to-end while these chapters are written.)

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
- **Results ledger (standing, 2026-07-08)**: every new result is entered in
  `progress/results-ledger.md` (artifact path, command, date, which tex it
  feeds/supersedes) at the moment it lands. Ledger-vs-tex sweep before any
  submission build. Guard against the stale-number drift `report.md` found.
