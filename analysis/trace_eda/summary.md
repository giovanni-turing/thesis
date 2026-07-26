# Azure Multimodal Trace — EDA Summary

Trace: `data/AzureLMMInferenceTrace_multimodal.csv.gz` · 1,000,000 requests ·
exactly 7 days (2024-10-15T12:00Z → 2024-10-22T12:00Z) · computed on GPU
(cuDF 26.06, RTX 5090). Scripts: `a_quality.py` … `m_gen_and_global.py` (sections A–M below,
in analysis order); figures in `figures/`; per-script stats in `*_stats.json`.
Narrative synthesis: `REPORT.md`. Converter decisions: final section.

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

## F2 — Fourier analysis of the ctx signal (with modality decomposition)

`f2_fourier_ctx.png`: ctx_total 1/f^0.72 (**H ≈ 0.86**); decomposed,
ctx_multimodal 1/f^0.74 (H ≈ 0.87) vs ctx_text_only 1/f^0.51 (H ≈ 0.76).
The total prefill signal's spectral shape and persistence are inherited
almost entirely from the vision-borne component — the frequency-domain
counterpart of the 72.5% volume share (§G) and the r≈0.89 images~ctx
coupling (§E). Diurnal lines present in all three; text-only prefill hits
its noise floor sooner (less forecastable structure).

### Spectral-line significance check (bin-exact, SNR vs local median)

Tested whether any sub-diurnal line (e.g. ~18 h) is real. Verdict: **no** —
the 18.67 h bin (k=9 of the 168 h record) has SNR 2.6 in requests and is
absent from the top lines of images/ctx; apparent sub-diurnal peaks are
fluctuations on the steep 1/f background. Credible lines are the diurnal
family only, with a notable shape detail: in the request signal the **12 h
(SNR 5.6) and 8 h (SNR 4.7) harmonics exceed the 24 h fundamental (2.9)** —
a multi-peaked daily profile rather than a single smooth cycle. ctx's
strongest line is 24 h (SNR 6.5). Very-low-frequency "peaks" (84 h, 33.6 h,
28 h = record/k for k=2,5,6) have 2–6 cycles of support and sit where LRD
power concentrates — record-length artifacts, not periodicities.

## H — Pairwise density maps

`h_pairwise_density.png`: three log-log 2D densities, one sequential hue per
panel. imgs×ctx shows the tight ~66-tok/img ridge at high counts over wide
text-driven spread at low counts; imgs×gen shows discrete k² stripes with no
trend (independence); ctx×gen a diffuse weak-coupled cloud (ρ=0.17).

## I — Burst anatomy (onset dynamics)

18 merged episodes (from 87 raw p99-exceedances; boundaries extended to p50
crossings). **Onset baseline→peak: p50 = 6.5 min, p10 = 2 min, fastest = 1 min**;
median ramp 38 img/s per minute; **median steepest single-minute jump =
208 img/s** (max 355). Design consequence: with cold starts of tens of
seconds to minutes, the fast half of bursts cannot be caught reactively —
the forecast-horizon budget (onset minus cold-start) is the autoscaler's
binding constraint. (`i_burst_onsets.png`, `i_burst_aligned.png`)

## J — Workload classes on the k² structure

| class | k | req share | image share | ctx p50 | CV² (img rate) |
| --- | --- | --- | --- | --- | --- |
| text | 0 | 50.0% | — | 792 | — |
| single | 1 | 33.0% | 2.3% | 1,069 | 1.1 |
| tiled_small | 2–5 | 13.1% | 10.6% | 4,558 | 1.1 |
| tiled_large | 6–10 | 1.1% | 5.9% | 13,747 | 15.6 |
| frames | >10 | 2.7% | **81.1%** | 33,722 | 5.4 |
| nonsquare | — | 0.005% | 0.07% | 4,785 | — |

(nonsquare = the 53 requests whose positive image count is not a perfect
square; kept as an explicit class instead of being rounded into single/tiled.)

**Every top-6 burst episode is 92–96% frames-class image volume.** The
vision pool's demand — and its bursts — are effectively one workload class
(video-like frame jobs, 2.7% of requests). Per-class signals
(`j_class_signals.png`) show frames switching between off and full-on
regimes while single/tiled_small stay quasi-stationary. Implication:
monitoring/forecasting the frames-class signal specifically is the leverage
point; the converter should carry class labels.

## K — Episode clustering (cuML KMeans, GPU)

Features: log peak/onset/duration/ctx + class shares; silhouette selects
k=2 but the split is 17-vs-1 — a single mixed-composition outlier (66%
frames) against a homogeneous majority (median 95% frames). **Honest
negative: there is one burst type in this trace**, varying in magnitude
and duration, not kind. No episode taxonomy is needed downstream; scenario
selection can sample by peak/duration alone. (`k_episode_clusters.png`)

## L — Request-level semantic groups (cuML KMeans, GPU, k=4 by silhouette)

Clustering all 1M requests on log(imgs, ctx, gen) recovers four archetypes
(`l_request_clusters.png`, silhouette 0.39):

| group | req share | image share | ctx share | profile (p50: img/ctx/gen) |
| --- | --- | --- | --- | --- |
| text: conversational generation | 51.4% | 1.3% | 23.9% | 0 / 1,063 / 201 |
| text: short-answer / extraction | 31.0% | 1.1% | 9.6% | 0 / 738 / 22 |
| vision: doc/tiled understanding | 14.1% | 11.9% | 33.5% | 9 / 4,879 / 124 |
| vision: video/frame analysis | 3.4% | **85.7%** | 32.9% | 400 / 31,512 / 56 |

Reading: the text half splits on generation length (chat vs extraction);
the vision half splits into document understanding vs video/frame jobs.
The video group — 3.4% of requests — carries 85.7% of image volume and a
third of all prefill tokens, converging with §J's frames-class attribution
(the unsupervised grouping rediscovers the k² class structure). Decode
pressure lives in the text-chat group (gen p50 201); vision groups are
short-decode. Per-group demand signals map cleanly onto pool stages:
video group → encoder + prefill; text-chat → decode.

## M — Decode-signal symmetry + global percentile tables

gen tokens/s (1-min): mean 309, CV² 0.40, max 2,164. Constant-fraction fit
vs request rate: R² = 0.654 (α = 182 tok/req) — the best rate-explained of
the three pool signals. ACF half-life 5 min (fastest-mixing); spectral
slope 1/f^0.82 (H ≈ 0.91 in the LRD band — variance concentrates at high
frequency, so short practical memory despite LRD scaling). Nearly
burst-neutral: during image-burst minutes decode rate rises 1.78× and
per-request generation *shortens* (p50 84 vs 99). NOTE: these are signal
properties only — whether reactive scaling suffices for decode, and what
forecast/decision frequency any pool needs, depends on cold-start (warmup)
times, per-replica capacity, and cost, which the trace does not contain
(Phases 2–3 measure them). Consolidated global percentile tables
(p1→p99.9, request-level + 1-min rates, all four signals):
`m_global_percentiles.md` / `m_gen_and_global_stats.json`.

## Q — Multi-resolution analysis + tail-regime marginals

**Multi-resolution** (`q_multires.png`): aggregation attenuates observed
peaks unevenly — at 60 s windows the visible peak is only **3.9%** of the
1 s peak for images/s (gen 6.5%, ctx 11.2%, requests 37.1%). A
minute-resolution monitor underestimates the vision signal's instantaneous
peak by ~25×; the encoder pool's true arrival surges live below the
monitoring floor of coarse windows. CV² decays with window size most
slowly for images (25.7 → 3.83; shallow log-log slope, consistent with
H ≈ 0.93) and fastest for gen (4.7 → 0.40, fast-mixing).

**Tail regimes** (`q_tail_regime_kdes.png`; global vs conditioned KDEs of
each marginal, log scale):
- **large_ctx** (top 1% ContextTokens): 82% multimodal, NumImages p50 = 529,
  gen p50 = 59 — large-context traffic *is* the frames class; the imgs
  marginal collapses onto ~23² tiles.
- **large_img** (top 1% image-bearing): ctx p50 = 35,932 (deterministic
  ctx–img coupling at the tail), gen p50 = 53.
- **high_req_rate** (top 1% req/s minutes): per-request marginals barely
  move (ctx p50 1,210 vs 1,124; gen 105 vs 98; img p50 = 1) — request-rate
  spikes carry *ordinary-composition* traffic.
- **Regime overlap**: hot-request minutes ∩ hot-image minutes = **5 of 106**
  (Jaccard 0.02) — the extreme events of the two signals are essentially
  disjoint. This sharpens the decoupling finding: not merely uncorrelated
  on average, the two demand signals spike at *different times*.
