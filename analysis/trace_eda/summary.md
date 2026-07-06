# Azure Multimodal Trace — EDA Summary

Trace: `data/AzureLMMInferenceTrace_multimodal.csv.gz` · 1,000,000 requests ·
exactly 7 days (2024-10-15T12:00Z → 2024-10-22T12:00Z) · computed on GPU
(cuDF 26.06, RTX 5090). Scripts: `a_quality.py` … `d_signals.py`; figures in
`figures/`; per-script stats in `*_stats.json`.

## A — Quality & semantics

- Continuous coverage: largest gap 39 s; median inter-arrival 312 ms; 151
  duplicate rows (1.5e-4, ignorable); no negatives.
- **Exactly 500,000 (50.0%) requests are text-only** — a by-construction
  multimodal split, worth stating in the thesis when generalizing.
- **`ContextTokens` includes a vision contribution, but not a constant
  per-image one**: median context rises monotonically with image count
  (792 @0 images → 35,932 @529), yet the per-image increment falls from
  ~277 tokens @1 image to ~66 @529. No clean "subtract k·images"
  decomposition exists for the traced model.
- **`NumImages` values are k² (perfect squares)** — 71 square values cover
  499,947 of 500,000 image-bearing requests (53 exceptions): tile/frame
  structure (k×k grids), up to 97² = 9,409 images in one request.

## B — Marginals

- Images per image-bearing request: p50 = 1, p99 = 529, max = 9,409 —
  extremely heavy-tailed; single-image requests dominate but tail requests
  carry hundreds of tiles.
- ContextTokens: p50 = 1,124, p99 = 35,932, max = 148,569 (top 1% of
  requests carries 15.2% of context volume).
- GeneratedTokens: p50 = 98, p99 = 1,066, max = 16,384 (top 1% → 13.4%).

## C — Temporal structure

- 1-min windows: requests/s mean 1.65, max 7.8, CV² 0.32; images/s mean
  23.7, max 370, **CV² 3.83 — the vision signal is ~12× burstier** than the
  request signal at the same clock. Peak/mean: 15.6× (images) vs 4.7×
  (requests). At 1-s windows image CV² reaches 25.7 (single-request spikes
  up to 9,411 img/s).
- 87 episodes exceed the p99 image-rate (224 img/s); the top episode peaks
  at 370 img/s while requests peak at just 4.48 req/s — bursts are
  invisible in the request-rate signal.
- Diurnal profile exists but is mild compared to burst regimes; the
  seven-day small-multiples figure (`c_seven_day_signals.png`) shows
  multi-hour image-burst regimes (Oct 15–16, 18–19, 20–21, 21–22) over a
  quasi-stationary request signal.

## D — Per-pool signals & predictability

- **Constant-fraction fit images/s ~ α·requests/s: α = 15.1, R² = 0.123** —
  computed fresh here and independently consistent with the thesis trace
  chapter's ≈0.12. Vision work is not a fraction of request rate.
- Pearson @1min: img~req 0.36; ctx~req 0.66; **gen~req 0.81** — language-pool
  decode load tracks request rate reasonably; vision load does not.
- **Autocorrelation half-life: images 69 min vs requests 9 min.** The vision
  signal has an order of magnitude more memory — it is simultaneously the
  signal a rate-based autoscaler cannot see and the more forecastable one at
  cold-start-relevant horizons (ACF@5min: 0.64 vs 0.52). This is the
  feasibility premise for the predictive-scaling phase.

## Converter decisions (feed `trace_to_two_pool.py`)

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

## E — Comprehensive: arrival process, modality splits, correlations

### Arrival process is bursty at every operational scale (not Poisson)

- Inter-arrival CV = 1.55 (Poisson would be 1); the survival curve is
  heavy-tailed against the exponential reference.
- Per-second counts are overdispersed vs Poisson(1.65).
- **Fano factor grows without bound with window size**: 1.8 (1 s) → 8.0
  (10 s) → 31.9 (1 min) → 186 (10 min) → 938 (1 h). Burstiness is
  scale-free / long-range dependent — no aggregation window "smooths it
  away", so reactive smoothing alone cannot absorb it.

### Distributions by modality

- Multimodal requests have **longer inputs but shorter outputs**:
  ContextTokens p50 1,422 vs 792 (text-only); GeneratedTokens p50 80 vs
  147 — a VQA/captioning profile vs longer-form text chat.
- Hill tail indices (top 1%): GeneratedTokens ≈ 1.9 (genuinely heavy tail),
  ContextTokens ≈ 6.6, NumImages ≈ 7.2 (bounded-ish power-law tails).

### Correlations

Request level (Spearman, all): imgs~ctx **0.50**, imgs~gen **−0.06**,
ctx~gen 0.17. Within multimodal only: imgs~ctx **0.83** (image tiles drive
context length), imgs~gen **0.08** (decode length is independent of image
count — median gen tokens stays ≈50–140 across 1…529 images, with one
distinct 435-token class at 225 images worth noting as a workload cluster).

Window level (1 min, Pearson): images~ctx **0.89** (vision load ≈ prefill
load — the two are the same pressure), images~gen 0.28 with the lagged
cross-correlation peaking sharply **at lag 0** (no lead/lag): image load
does not forecast decode load and vice versa.

### Implications for the thesis pipeline

1. **Independent per-pool forecasting is justified**: vision and decode
   demands are weakly coupled and contemporaneous — neither is derivable
   from the other (nor from request rate; §D).
2. **Prefill and vision pressure travel together** (r≈0.89): the encoder
   pool and the LLM prefill stage stress simultaneously — relevant for
   disaggregated prefill/decode splits on the language side.
3. **Scale-free burstiness** means SLA compliance under bursts is a
   provisioning-lead-time problem, not a smoothing problem — exactly the
   regime where forecast-driven scaling can beat reactive scaling.
4. GeneratedTokens' heavy tail (Hill ≈ 1.9) makes decode-side capacity
   planning quantile-driven, not mean-driven.

## F — Fourier analysis of the arrival process

Per-second counts (604,800 samples), CuPy FFT, log-binned periodograms
(`f_fourier_spectra.png`, `f_fourier_stats.json`).

- **Diurnal harmonics** (24 h line + 12/8/6 h overtones) are present in both
  signals — real periodicity with ~7 cycles of support. Apparent periods
  ≥ 84 h are record-length artifacts of the 7-day window, not weekly cycles.
- **Long-range dependence, quantified in the frequency domain**: mid-band
  (10 min–12 h) spectral slopes 1/f^0.66 (requests, H ≈ 0.83) and
  **1/f^0.86 (images, H ≈ 0.93)**. Agrees with the Fano growth (§E) and the
  ACF half-lives (§D) — three independent estimators, one conclusion: strong
  persistence, strongest in the vision signal.
- **White shot-noise floor** above ~0.02 Hz in both signals: sub-minute
  fluctuations are irreducible arrival granularity; forecastable structure
  lives at provisioning timescales (minutes and up).
- Phase-4 implication: H ≈ 0.93 means short-memory models (Poisson/ARMA
  class) structurally underfit the vision signal — an a-priori case for
  long-context forecasters, to be tested against naive/seasonal baselines.

## G — ContextTokens as a demand signal (prefill load)

Signal (`ctx tokens/s`, 1-min): mean 4,813, max 39,108, **CV² 0.85** —
between the request signal (0.32) and the image signal (3.83).
Constant-fraction fit vs request rate: **R² = 0.438** — better than vision
(0.12) but still far from sufficient for rate-based sizing. ACF half-life
**15 min** (requests 9, images 69); spectral slope 1/f^0.72, **H ≈ 0.86**.

**Volume decomposition**: multimodal requests carry **72.5% of all prefill
tokens** while being 50% of requests; the minute-level multimodal share
swings 0.1–0.95 with clear regime structure (`g_ctx_decomposition.png`) —
prefill capacity is mostly a vision-driven concern.

**Mixture structure** (`g_ctx_mixture_burst.png`): multimodal prefill has a
hard lower edge (~200 tokens — minimum context of an image-bearing request)
and a secondary mass at 10⁴–10⁵ tokens (the tile-heavy k² classes);
text-only spans the low end more broadly.

**Burst composition shift**: during p99-image-rate burst minutes, requests
have **2.69× the mean prefill length** of calm minutes (p50 1,428 vs 1,117;
the burst CCDF shows a fat shelf near 3×10⁴ tokens). Bursts compound: more
images AND longer prefills per request — prefill pressure during bursts is
super-linear in arrival rate, which any SLA/scaling policy must price.

Pipeline implications: (i) the language pool's prefill stage inherits
vision-borne burstiness (r≈0.89 with images/s, 72% of volume) — sizing it
off request rate alone underestimates burst pressure ~2.7×; (ii) ctx/s is
itself forecastable (H≈0.86, 15-min memory) and should be forecast as its
own signal alongside images/s, per the per-pool-signals design.
