# Phase 1 — Azure Trace EDA + Two-Pool Workload Converter

> **EDA COMPLETE (2026-07-06)** — 12 scripts (A–L), 16 figures, 11 stats files in
> `analysis/trace_eda/`. **Narrative report: `analysis/trace_eda/REPORT.md`**
> (dataset characterization → proposal insights → design decisions → asset
> inventory). Per-section detail in `summary.md`; provenance in `data/source/`.
> Remaining in Phase 1: `trace_to_two_pool.py` implementing REPORT.md §6.1.

Plan agreed 2026-07-06. Companion to [`thesis-roadmap.md`](thesis-roadmap.md) Phase 1.

## Input

`data/AzureLMMInferenceTrace_multimodal.csv.gz` — 1,000,000 requests,
columns `TIMESTAMP` (ISO, ms precision, starts 2024-10-15T12:00Z),
`NumImages`, `ContextTokens`, `GeneratedTokens`.

Schema facts that shape the phase:

- **No image resolutions** — only counts. Decision: **fixed 448² baseline**
  for the encoder pool (matches the validated AIC/bench point: 7.82 ms
  predicted, 11.36 ms measured HF); sensitivity via one alternate size later.
- **`ContextTokens` semantics unknown** (text-only vs incl. vision tokens) —
  resolved empirically in script A before the converter fixes its
  `input_length` formula.

## Decisions (locked)

1. Deliverable: **committed scripts + figures** (audit discipline), not notebooks.
2. Image size: **fixed 448²** (196 post-merge vision tokens/image).
3. Fresh EDA — no cross-assertions against the mestrado trace chapter.
4. **Compute on GPU (CUDA)** per user request: `cudf` / `cudf.pandas` in
   `eda/.venv` on the RTX 5090 (this is what the eda project's RAPIDS stack
   was installed for).

## EDA structure (one script per block, figures + stats emitted per script)

- **A — quality & semantics**: monotonicity, gaps, duration, dupes/zeros,
  field ranges; ContextTokens | NumImages conditional analysis →
  text-vs-vision token accounting decision for the converter.
- **B — marginals**: NumImages (incl. text-only share), ContextTokens,
  GeneratedTokens distributions and tails; per-pool load implications.
- **C — temporal**: request-rate and image-rate series at multiple windows;
  seasonality; burstiness (CV², peak/mean); burst-episode extraction.
- **D — per-pool signals**: images/s vs context-tokens/s vs generated-tokens/s;
  cross-correlation and lag; autocorrelation horizons vs cold-start times
  (predictor feasibility input for roadmap Phase 4).

## Outputs

- `analysis/trace_eda/{a_quality,b_marginals,c_temporal,d_signals}.py`
- `analysis/trace_eda/figures/*.png`, `analysis/trace_eda/summary.md` (+ stats JSON)
- Converter-decisions section appended to summary → feeds `trace_to_two_pool.py`

## Converter & pipeline decisions derived from the EDA (project material,
## moved out of the EDA per scope: EDA = dataset analysis only)

1. **LLM-pool `input_length` = `ContextTokens` as-is.** It is the traced
   LLM-side load (already carrying the traced model's vision share); no
   subtraction is defensible given the non-constant per-image increment.
   `output_length = GeneratedTokens`.
2. **Encoder-pool work = `NumImages` × (448² image)** — fixed-size baseline
   per the phase decision; each image = one ViT forward (AIC-costed on
   rtx_5090 silicon). The k² tile structure means "images" arrive in bulk
   per request — encoder batching matters and the pool simulator must
   process a request's tiles as one arriving batch.
3. **hash_ids disjoint per request** (no cross-request prefix reuse assumed).
4. **Timestamps preserved** (open-loop replay); encoder-pool delay folded in
   per the established timestamp-shift composition.
5. **Scenario windows**: full 7 days for baselines; the top burst episodes
   (from `c_temporal_stats.json` top6) as headline autoscaling scenarios.
6. Drop the 151 duplicate rows; keep zero-token rows (they are real
   requests; give output_length max(1, GeneratedTokens) if the simulator
   requires ≥1).

## Pipeline design decisions (from EDA findings)

1. **Scenario selection**: full 7 days for baselines; burst episodes sampled
   by peak/duration (one burst type — EDA §K); six largest frames-floods as
   headline autoscaling scenarios.
2. **Predictor interface**: three per-pool signals at 1-min granularity
   (sub-minute is shot noise — EDA §F); horizon requirement determined by
   onset (EDA §I: p50 6 min) MINUS cold-start, which Phases 2–3 measure;
   frames-class signal is the highest-leverage target (2.7% of requests,
   81% of image work).
3. **Simulator fidelity**: encoder pool must batch per-request tile groups;
   burst prefill compounding (2.69× — EDA §G) must emerge from the workload,
   not be assumed.
4. **Evaluation framing**: SLA × GPU-hours vs static-optimal and reactive
   baselines, scored inside burst episodes.
