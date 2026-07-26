# Kernel-collection history (S4 depth)

The aiconfigurator (AIC) encoder cost-model campaign on RTX 5090, phase by
phase, plus the engine-sensitivity detail displaced from Appendix A. Every
phase has its own directory under `collector_artifacts/`; the directory *is*
the artifact, and the manuscript never cites a collection number that is not
re-readable from one of them.

Companion documents: `SUPPLEMENTARY.md` (archive index), `manifest_full.md`
(expanded element→artifact mapping), `progress/results-ledger.md` (S1, the
dated per-result record these phases feed).

## Phase inventory

| Phase | Directory | Files | Size | Role |
|---|---|---:|---:|---|
| 0 | `phase0_node_discovery/` | 2 | 12K | node/GPU discovery on the benchmark host (`nvidia-smi` capture: driver 595.71.05, CUDA 13.2, RTX 5090) |
| 1 | `phase1_prepare_repo/` | 1 | 8K | aiconfigurator checkout prepared for collection (editable install, data branch) |
| 2 | `phase2_system_metadata/` | 2 | 12K | system descriptor emitted for the collector (`rtx_5090.yaml`) |
| 3 | `phase3_preflight/` | 1 | 8K | registry preflight: which collector route each op resolves to (`encoder_attention` → `collector.vllm.collect_attn_encoder`, perf file `ENCODER_ATTENTION`, single module, no VersionRoute list) — `compat_notes.md` |
| 4 | `phase4_smoke/` | 2 | 12K | smoke collection (`smoke_rows.csv`, `collection_summary_vllm.json`) |
| 5 | `phase5_limited/` | 1 | 8K | limited collection (`limit20.parquet`) |
| 6 | `phase6_full/` | 0 | — | full collection (outputs landed in the aiconfigurator data tree, not duplicated here) |
| 6b | `phase6b_gemm/` | 1 | 8K | bf16 GEMM collection driver (`run_gemm_bf16.py`) |
| 7 | `phase7_sanity_charts/` | 2 | 92K | collected-vs-SOL sanity charts and the generation report (`gemm_rtx_5090_vllm_0.22.0.png`, `summary.md`) |
| 9 | `phase9_two_pool/` | 7,543 | 354M | two-pool bring-up: encoder pool simulation + the first composed report (`encoder_pool_sim.py`, `two_pool_report.json`) |
| A | `phaseA_validation/` | 3 | 16K | Route-A validation: HF `Qwen3VLVisionModel` bf16, 5 independent runs × 50 iterations, CUDA events, 95% CI, against AIC's `_run_encoder_phase` on `rtx_5090/vllm/0.22.0` collected at the same clock lock |
| B | `phaseB_batch_validation/` | 11 | 224K | batch-axis validation: `measured_f_n_5x50.csv`, `aic_f_n.csv`, `aic_f_n_postinfill.csv`, `kernel_ledger_N{1,64}.json`, `fn_figure.png` |
| B′ | `phaseB_fallback_trace/` | 1 | 8K | fallback-path trace captured while diagnosing the batch-axis gap |
| C | `phaseC_vit_shape_infill/` | 7 | 96K | ViT shape infill: `cases.json`, `run_infill.py`, `merge_parquet.py`, `gemm_perf.txt`, `encoder_attention_perf.txt`, `infill_errors.jsonl` |
| D | `phaseD_cold_start/` | 3 | 16K | encoder-worker model-side cold start (`measure_cold_start.py`, `trials.jsonl`, `README.md`) |
| E | `phaseE_physical_anchor/` | 105 | 3.7M | physical encoder anchor and the four-engine sensitivity study |

Sizes and counts are from the working tree at the pinned baseline; `phase9`
dominates because it retains the full composed replay output.

## Phase A — Route-A validation

Question: does AIC's composed encoder forward reproduce a measured vision-tower
forward at a fixed shape? Method: HuggingFace `Qwen3VLVisionModel` in bf16,
five independent runs of fifty iterations, CUDA-event timing, 95% confidence
intervals, with SM locked at 2407 MHz (reads 2385–2392), memory locked at
14001, persistence on; the AIC prediction is taken from the same silicon
descriptor collected under the same lock. Feeds `tab:aic-validation`.

## Phase B — batch axis

Extends the check from one shape to f(N), the encoder forward as a function of
batch size. `measured_f_n_5x50.csv` is the measurement, `aic_f_n.csv` the
composition before infill, `aic_f_n_postinfill.csv` after. The two kernel
ledgers (`kernel_ledger_N1.json`, `kernel_ledger_N64.json`) decompose the
composition operator by operator at the two ends of the serving regime, which
is what made the coverage gaps of Phase C findable at all. Feeds `tab:aic-fn`
and `fig:aic-fn`.

## Phase C — ViT shape infill

The perf tables blanked the ViT's large-batch shapes: the GEMM and attention
grids stopped well short of the shapes the ViT queries, so past N ≈ 42 the
model extrapolated beyond the grid. ViT-shape rows at large m, and attention
rows out to batch 512, were collected on the 5090 (with a collector
out-of-memory fix for a 32 GB card) and merged into the AIC branch
`656ac8ca`. Row counts: attention 7,679 → 7,760; GEMM 34,326 → 34,710. These
are **additive** data/tooling corrections — the previously committed rows are
preserved exactly, none rewritten.

## Phase D — encoder cold start

The lead-time grids assume the vision encoder (576M parameters, 1.15 GB bf16)
cold-starts much faster than a language worker. Phase D measures the
model-side floor instead of assuming it: one fresh interpreter per trial, wall
timestamps per phase (imports → CUDA context → checkpoint load → GPU
transfer → …). Artifact `trials.jsonl`; method note in the phase `README.md`.

## Phase E — physical anchor and engine sensitivity

Two distinct collections live here and must not be conflated:

1. **Physical encoder anchor** (`bench_encoder_anchor.py`, `silicon_in_loop.py`,
   `silicon_multiworker.py` → `anchor_sdpa_*.json`, `oneworker_artifact/`,
   `silicon_multiworker.json`), run **single-tenant persistence-mode**
   (delivered SM 2377–2400 MHz, *not* a hard lock; no memory-clock reading or
   lock-command log captured).
2. **Matched-engine sweep** (`vllm_eager_dense.py`, `vllm_multires.py`,
   `vit_compile_dense.py`, `tier2_vllm_replay.py`, `make_engine_fig.py`), a
   *separate recollection* under an **external `nvidia-smi` clock lock**
   (target SM 2400 MHz, memory 14001 MHz).

### Engine-sensitivity detail

The batch-axis discrepancy between AIC's composed encoder forward and
end-to-end measurement is predominantly **execution-stack-specific** — a
property of the execution engine used for measurement more than of the cost
model. Four execution paths were timed on the same Qwen3-VL vision-tower
forward (bf16, 448²): HuggingFace eager with SDPA attention, HuggingFace with
FlashAttention-2, vLLM's own `Qwen3_VisionTransformer` with the
FlashAttention backend, and `torch.compile` (max-autotune).

- HuggingFace eager (SDPA) runs **1.36–1.62×** above the composition, rising
  with N, and climbs to **1.69×** by N=512.
- FlashAttention-2 recovers part of that but leaves the unfused elementwise,
  DeepStack and patch-embed overhead intact.
- `torch.compile` (max-autotune) closes most of the rest without being either
  engine's default.
- vLLM's own vision tower through its FlashAttention backend is the
  like-for-like anchor — AIC's collected operators *are* vLLM's kernels
  (attention `kernel_source=vllm_vit_flash_attn`, GEMMs vLLM
  `RowParallelLinear`) — and matches the composition across the anchor shapes.

Against the engine it targets, the composition stays within **12.8%** across
the whole N ≤ 64 serving regime (residual up to +12.7% inside the regime,
growing to +21.8% only past the FIFO cap at N=64, reaching that value at the
N=512 sweep endpoint). The earlier "1.4–1.6× gap" is therefore the
HuggingFace→vLLM execution-stack difference, not a cost-model error.

**Scope of the check** (the limits that travel with the number): it times
eager vLLM's *standalone* vision-tower forward on synthetic GPU-resident
inputs with randomly initialised weights (latency is shape-determined, so
weight values are not expected to materially affect these dense-kernel
timings). It is the forward compute, **not** the complete serving path (image
preprocessing, host-to-device transfer, scheduling, prefill). Sampling is a
**dense N=1–64 sweep plus five off-cap probes** (N ∈ {96, 128, 192, 256,
512}) — not a dense sweep to 512.

Fed through the encoder FIFO — the AIC-sized winning week schedule replayed
with f(N) repriced at the measured vLLM curve (`tier2_vllm_replay.py`) — the
week-scale encoder-delay p99 moves to **606 ms** (from **589 ms** under AIC),
non-divergent, so the AIC-priced cost ratio carries no separate silicon
penalty. Agreement generalises across resolution (224²–896²), holding within
**15.5%** at the two largest, where AIC slightly under-prices the largest
forwards (the same beyond-cap drift direction); per-resolution ratios are
archived in `vllm_multires.json`.

A **live-worker confirmation over the full serving path** (with weight-loaded
provenance) remains future work. The vision controller itself is simulated;
the live anchor runs Dynamo's real control plane with mocked engines.

### Upstream encoder-coverage contributions

Two gaps in AIC's encoder path were found and returned to the
`aiconfigurator` project as a draft PR (**ai-dynamo/aiconfigurator #1312**,
campaign through commit `b55dd0b7`):

1. The operator graph omitted the pixel-to-hidden patch-embedding GEMM. A
   *subsequent* branch added a guarded `encoder_patch_embed_gemm` (≈0.3% of
   the forward at N=64; the DeepStack mergers were already modelled). **This
   addition postdates the load-bearing simulation snapshot used in the
   manuscript, in which the operator is absent** — the two are consistent, and
   the manuscript's numbers are not silently rebased onto the later branch.
2. The large-batch ViT shapes described under Phase C.

Both are additive data/tooling corrections; the committed rows are preserved
exactly.

## Ledger cross-index

Entries in `progress/results-ledger.md` (S1) that record these phases and the
results they feed — search by heading text:

- `Measured f(N), chapter protocol` (2026-07-08)
- `Composed f(N), post-infill` (2026-07-08)
- `Kernel ledgers N=1/N=64` (2026-07-08)
- `Phase C shape infill` (2026-07-08)
- `Encoder model-side cold start (Phase D)` (2026-07-08)
- `Vision knee sweeps, post-infill` (2026-07-08)
- `Encoder cap sensitivity (S4.4)` (2026-07-08)
- `DeepStack ×4 handoff-payload sensitivity` (2026-07-09)
- `Physical encoder anchor (Phase E, first, unlocked-clock)` (2026-07-09)
- `Physical encoder anchor — stable-clock confirmation (Phase E)` (2026-07-10)
- `Silicon-in-the-loop encoder burst replay (Phase E) — measured-service FIFO` (2026-07-10)
- `Multi-worker silicon feasibility` (2026-07-10)
- `Single-worker silicon amplification, all 6 windows (Phase E)` (2026-07-10)
- `Closed-loop cost ratio under measured silicon` (2026-07-10)
- `Dense multi-engine encoder matrix + vLLM queue-replay` (2026-07-12)
