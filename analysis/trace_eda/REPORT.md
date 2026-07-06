# The Azure Multimodal Inference Trace: An Exploratory Characterization

**EDA report — dataset analysis only.** All analyses GPU-computed
(cuDF/cuML/CuPy 26.06, RTX 5090). Every number below is reproducible from a
committed script; every figure and stats file is inventoried in §9.

---

## 1. The dataset

`AzureLMMInferenceTrace_multimodal.csv.gz` is Microsoft's
**AzureLMMInferenceDataset2025** ([Azure Public
Dataset](https://github.com/Azure/AzurePublicDataset); CC-BY): 1,000,000
requests from a production multimodal-model inference cluster, exactly
7 days (2024-10-15 → 10-22), four fields per request — `TIMESTAMP`,
`NumImages`, `ContextTokens`, `GeneratedTokens`. It is the companion
dataset of the **ModServe** paper (Qiu et al., SoCC 2025,
arXiv:2502.00937) — the modality-disaggregated serving system this
thesis's proposal extends with forecast-driven per-pool autoscaling.
Provenance mirror, paper PDF, and the official example notebook:
`data/source/`.

**Quality** (§A, `a_quality_stats.json`): continuous coverage (largest gap
39 s, median inter-arrival 312 ms), 151 duplicate rows (1.5×10⁻⁴,
dropped by the converter), no negatives. Two structural facts shape all
downstream use:

- **Exactly 50.0% of requests are text-only** — a by-construction split to
  state when generalizing.
- **`NumImages` values are perfect squares** (71 k² values cover 99.99% of
  image-bearing requests, up to 97² = 9,409): images arrive as k×k
  tile/frame grids — bulk per-request batches, not independent singles.

**Semantics resolved** (§A, confirmed by the official schema): `ContextTokens`
**includes** the vision tokens of the traced model, with a *non-constant*
per-image increment (~277 tokens @1 image → ~66 @529) — no clean
"subtract k·images" decomposition exists. Converter consequence:
`input_length = ContextTokens` as-is; `NumImages` drives encoder-pool work
independently.

## 2. What a request looks like

**Marginals** (§B): heavy tails everywhere. Images per image-bearing
request: p50 = 1, p99 = 529, max 9,409. ContextTokens p50 = 1,124,
p99 = 35,932, max 148,569. GeneratedTokens p50 = 98, p99 = 1,066, max
16,384. Hill tail indices (§E): GeneratedTokens ≈ 1.9 (genuinely heavy —
decode capacity is quantile-, not mean-driven), ContextTokens ≈ 6.6,
NumImages ≈ 7.2.

**Modality split** (§E): multimodal requests have *longer inputs but
shorter outputs* (ctx p50 1,422 vs 792; gen p50 80 vs 147) — a
VQA/captioning profile against longer-form text chat.

**Four semantic archetypes** (§L; unsupervised cuML k-means, k=4 by
silhouette, `l_request_clusters.png`):

| group | requests | image volume | prefill volume | p50 img/ctx/gen |
| --- | --- | --- | --- | --- |
| text: conversational generation | 51.4% | 1.3% | 23.9% | 0 / 1,063 / 201 |
| text: short-answer / extraction | 31.0% | 1.1% | 9.6% | 0 / 738 / 22 |
| vision: doc/tiled understanding | 14.1% | 11.9% | 33.5% | 9 / 4,879 / 124 |
| vision: video/frame analysis | **3.4%** | **85.7%** | 32.9% | 400 / 31,512 / 56 |

Each archetype stresses a *different* serving stage: video → encoder +
prefill; text-chat → decode; extraction → almost nothing. Heterogeneous
demand arriving on one endpoint is the disaggregation motivation stated at
the workload level.

## 3. What the load looks like over time

**The arrival process is not Poisson at any operational scale** (§E,
`e_arrival_process.png`): inter-arrival CV 1.55, overdispersed per-second
counts, and a Fano factor that grows without bound — 1.8 (1 s) → 31.9
(1 min) → 938 (1 h). **No aggregation window smooths the burstiness away.**

**Spectrally** (§F/F2, `f_fourier_spectra.png`, `f2_fourier_ctx.png`): a
real diurnal family (24 h line + 12/8/6 h harmonics; in the request signal
the 12 h and 8 h harmonics *exceed* the 24 h fundamental — a multi-peaked
daily profile) over a strong 1/f^β long-range-dependent background. A
bin-exact significance check rejects any sub-diurnal line (e.g. ~18 h) and
marks the ≥84 h "peaks" as record-length artifacts.

**The persistence gradient** — the central summary of the temporal analysis:

| signal | CV² (1 min) | ACF half-life | spectral slope | Hurst |
| --- | --- | --- | --- | --- |
| requests/s | 0.32 | 9 min | 1/f^0.66 | ≈0.83 |
| ctx tokens/s | 0.85 | 15 min | 1/f^0.72 | ≈0.86 |
| — vision-borne part | — | — | 1/f^0.74 | ≈0.87 |
| — text-borne part | — | — | 1/f^0.51 | ≈0.76 |
| gen tokens/s (decode) | 0.40 | 5 min | 1/f^0.82 | ≈0.91 |
| images/s | 3.83 | 69 min | 1/f^0.86 | **≈0.93** |

The more vision-driven a signal, the burstier **and** the more persistent
it is: the signal most dangerous to reactive scaling is precisely the most
forecastable one.

## 4. The vision signal: decoupled, bursty, single-class

- **Request rate does not explain vision work** (§D,
  `d_img_vs_req_scatter.png`): constant-fraction fit R² = **0.123**
  (α = 15.1 img/req) — independently consistent with the thesis trace
  chapter's ≈0.12. By contrast, decode load tracks request rate well
  (gen~req r = 0.81, R² = 0.654 §M): the request-rate signal carries most of
  the decode demand's information but almost none of the vision demand's —
  what any scaling policy can do with this depends on system
  parameters (cold-start, per-replica capacity, cost) outside this dataset.
- **Bursts are invisible in the request signal** (§C,
  `c_seven_day_signals.png`): 87 p99-exceedances forming 18 merged
  episodes; the top episode peaks at **370 img/s while requests peak at
  4.48 req/s**. Vision CV² is ~12× the request CV² on the same clock.
- **Bursts are one workload class** (§J, `j_burst_attribution.png`): the
  frames class (k>10; 2.7% of requests) carries **81.2% of all image
  volume**, and every top-6 episode is **93–96% frames-class**. Episode
  clustering (§K, cuML) confirms a single burst type — 17 of 18 episodes
  are homogeneous frames-floods (one mixed outlier); they vary in
  magnitude and duration, not kind.
- **Bursts compound on the prefill side** (§G,
  `g_ctx_decomposition.png`): multimodal requests carry **72.5% of all
  prefill tokens**; during burst minutes the mean prefill length is
  **2.69×** calm minutes. More images AND longer prefills arrive together
  (window-level images~ctx r = 0.89): vision and prefill are one pressure.
- **Onset speed sets the design constraint** (§I, `i_burst_onsets.png`):
  baseline→peak in **p50 = 6 min, p10 = 2 min, fastest = 1 min**, with a
  median steepest single-minute jump of **208 img/s** (max 355). Against
  cold starts of tens of seconds to minutes, the fast half of bursts cannot be
  tracked reactively — the forecast-horizon budget (onset − cold-start)
  is the binding constraint.

## 5. Signal predictability

- The vision signal has **69 minutes of autocorrelation half-life** (vs 9
  for requests) and **H ≈ 0.93** — strong long-range dependence, i.e.
  structure a forecaster can exploit at exactly the horizons provisioning
  needs (ACF@5 min = 0.64).
- Demands are **not derivable from each other**: img~gen Spearman −0.06 at
  request level; window-level img/gen cross-correlation peaks sharply at
  lag 0 (no lead). Neither request rate nor any other pool's signal proxies
  the vision signal → **each pool must be forecast on its own signal**
  (vision ← images/s; language prefill ← ctx/s; language decode ← gen/s).
- H ≈ 0.93 also means short-memory models (Poisson/ARMA class)
  structurally underfit the vision signal — an a-priori indication that short-memory forecasters
  will underfit this signal class.
- The sub-minute band is a white shot-noise floor (§F): the *signals* carry
  no exploitable structure below ~1 minute. What decision/forecast frequency
  the system actually needs is not inferable from the trace — it depends on
  pool cold-start (warmup) times, per-replica capacity, and cost — system
  parameters outside this dataset; the floor only says finer-than-minute inputs add
  noise, not information.
- **Series semantics caveat**: all rate signals attribute a request's whole
  token volume to its *arrival* minute (the trace has no durations). This is
  faithful for images and prefill (executed near arrival) but makes gen/s an
  *offered-work arrival* series, not achieved decode throughput — real decode
  load is a smoothed, lagged version, so gen/s burstiness is an upper bound
  on what the decode pool feels.
- **Decode-signal properties** (§M): gen/s is the signal best explained by
  request rate among the three (R² = 0.654, α = 182 tok/req), the least
  bursty (CV² 0.40), fastest-mixing (ACF half-life 5 min), and nearly
  burst-neutral (rate ratio 1.78× during image bursts; per-request
  generation *shortens*, p50 84 vs 99). Whether this makes reactive scaling
  sufficient for the decode pool is a system question (cold-start, capacity,
  cost) that this dataset cannot answer — it only establishes that decode's
  demand signal is the most benign of the three.

## 6. Key findings (summary)

1. Half the requests are text-only; images arrive as k×k tile/frame grids;
   `ContextTokens` embeds a non-constant vision-token contribution.
2. Four request archetypes exist; the video/frame archetype (3.4% of
   requests) carries 85.7% of image volume and a third of prefill tokens.
3. The arrival process is non-Poisson at every scale (Fano 1.8→938), with
   a diurnal harmonic family over a long-range-dependent background.
4. The image signal is the burstiest (CV² 3.83) and most persistent
   (H ≈ 0.93) of the four demand signals; it is poorly explained by request
   rate (R² = 0.123) while decode load is largely rate-carried (R² = 0.654).
5. Bursts are homogeneous frames-class floods (93–96% of episode volume),
   ramping baseline→peak in a median of 6 minutes with single-minute jumps
   of ~208 img/s, and compounding with 2.69× longer prefills.
6. Demands are mutually non-derivable (img↔gen independent at request and
   window level); each demand signal carries information the others do not.

## 7. Global reference tables (percentiles)

Request-level marginals and 1-minute rate signals, all four signals
(`m_gen_and_global_stats.json`; generator: `m_gen_and_global.py`):

| signal | mean | p1 | p10 | p50 | p90 | p95 | p99 | p99.9 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| request-level: NumImages | 14.3 | 0.00 | 0.00 | 0.50 | 9.00 | 25 | 484 | 625 | 9,409 |
| request-level: NumImages_imagebearing | 28.7 | 1.00 | 1.00 | 1.00 | 25 | 196 | 529 | 1,089 | 9,409 |
| request-level: ContextTokens | 2,911.0 | 113 | 283 | 1,124 | 5,828 | 9,755 | 35,932 | 65,623 | 148,569 |
| request-level: GeneratedTokens | 186.6 | 1.00 | 10 | 98 | 433 | 603 | 1,066 | 3,943 | 16,384 |
| rate (1-min): requests_per_s | 1.7 | 0.23 | 0.53 | 1.55 | 2.88 | 3.33 | 4.35 | 5.73 | 8 |
| rate (1-min): images_per_s | 23.7 | 0.00 | 0.00 | 5.63 | 77 | 132 | 224 | 322 | 370 |
| rate (1-min): ctx_tokens_per_s | 4,813.1 | 281 | 940 | 3,537 | 10,326 | 14,157 | 21,610 | 30,647 | 39,108 |
| rate (1-min): gen_tokens_per_s | 308.6 | 42 | 103 | 281 | 531 | 629 | 1,010 | 1,599 | 2,164 |

## 8. Limitations (of the trace, to state in the thesis)

No image resolutions (counts only → fixed-448² scenario parameter); no
session/user identifiers; no latency or SLA ground truth (arrival-side
only); 7-day window (diurnal supported, weekly unsupported); 50/50
modality split by construction; `ContextTokens` embeds the *traced*
model's vision tokenization, not Qwen3-VL's (workload self-consistent, not
model-transferable).

## 9. Asset inventory

| script | figures | stats | one-line finding |
| --- | --- | --- | --- |
| `a_quality.py` | `a_context_vs_numimages.png` | `a_quality_stats.json` | ctx embeds non-constant vision tokens; k² structure |
| `b_marginals.py` | `b_numimages_spectrum.png`, `b_token_ccdfs.png` | `b_marginals_stats.json` | heavy tails; 50% text-only |
| `c_temporal.py` | `c_seven_day_signals.png`, `c_diurnal_profile.png` | `c_temporal_stats.json` | vision 12× burstier; 87 exceedances |
| `d_signals.py` | `d_img_vs_req_scatter.png`, `d_acf.png` | `d_signals_stats.json` | R²=0.123; half-life 69 vs 9 min |
| `e_comprehensive.py` | `e_arrival_process.png`, `e_tokens_by_modality.png`, `e_correlations.png` | `e_comprehensive_stats.json` | non-Poisson at all scales; modality profiles; independence img↔gen |
| `f_fourier.py` / `f2_fourier_ctx.py` | `f_fourier_spectra.png`, `f2_fourier_ctx.png` | `f_fourier_stats.json`, `f2_fourier_ctx_stats.json` | H gradient 0.83→0.93; diurnal family only |
| `g_ctx.py` | `g_ctx_decomposition.png`, `g_ctx_mixture_burst.png` | `g_ctx_stats.json` | 72.5% of prefill is vision-borne; bursts 2.69× longer prefills |
| `h_colormaps.py` | `h_pairwise_density.png` | — | pairwise structure, one hue per panel |
| `i_burst_anatomy.py` | `i_burst_onsets.png`, `i_burst_aligned.png` | `i_burst_anatomy_stats.json` | onset p50 6 min; 208 img/s 1-min jumps |
| `j_classes.py` | `j_class_signals.png`, `j_burst_attribution.png` | `j_classes_stats.json` | frames class = 81.2% of volume; bursts 93–96% frames |
| `k_episode_clusters.py` | `k_episode_clusters.png` | `k_episode_clusters_stats.json` | one burst type (honest negative) |
| `l_request_clusters.py` | `l_request_clusters.png` | `l_request_clusters_stats.json` | 4 semantic archetypes ↔ serving stages |
| `m_gen_and_global.py` | `m_gen_signal.png` | `m_gen_and_global_stats.json`, `m_global_percentiles.md` | decode-signal symmetry; global percentile tables |

Narrative summary with all numbers: `summary.md` (per-section detail).
Dataset provenance: `../../data/source/README.md`.
