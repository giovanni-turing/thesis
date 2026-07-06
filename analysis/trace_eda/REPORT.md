# The Azure Multimodal Inference Trace: Characterization and Implications for Disaggregated, Forecast-Driven Serving

**EDA report — Phase 1 of the thesis pipeline.** All analyses GPU-computed
(cuDF/cuML/CuPy 26.06, RTX 5090). Every number below is reproducible from a
committed script; every figure and stats file is inventoried in §8.

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

**The persistence gradient** — the EDA's single most consequential table:

| signal | CV² (1 min) | ACF half-life | spectral slope | Hurst |
| --- | --- | --- | --- | --- |
| requests/s | 0.32 | 9 min | 1/f^0.66 | ≈0.83 |
| ctx tokens/s | 0.85 | 15 min | 1/f^0.72 | ≈0.86 |
| — vision-borne part | — | — | 1/f^0.74 | ≈0.87 |
| — text-borne part | — | — | 1/f^0.51 | ≈0.76 |
| images/s | 3.83 | 69 min | 1/f^0.86 | **≈0.93** |

The more vision-driven a signal, the burstier **and** the more persistent
it is: the signal most dangerous to reactive scaling is precisely the most
forecastable one.

## 4. The vision-signal problem (the proposal's motivation, quantified)

- **Request rate does not explain vision work** (§D,
  `d_img_vs_req_scatter.png`): constant-fraction fit R² = **0.123**
  (α = 15.1 img/req) — independently consistent with the thesis trace
  chapter's ≈0.12. By contrast, decode load tracks request rate well
  (gen~req r = 0.81): rate-based scaling is adequate for decode, blind for
  vision.
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
  cold starts of tens of seconds to minutes, the fast half of bursts is
  structurally unwinnable for a reactive scaler — the forecast-horizon
  budget (onset − cold-start) is the binding constraint.

## 5. Forecastability (the proposal's feasibility, quantified)

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
  structurally underfit the vision signal — the a-priori case for the
  long-context/foundation-model forecasters staged in `models/`
  (chronos, timesfm, toto), to be tested against naive baselines.
- The sub-minute band is a white shot-noise floor (§F): nothing of value is
  lost by forecasting at minute granularity.

## 6. Design decisions this EDA fixes for the proposal

1. **Converter** (`trace_to_two_pool.py`, next): `input_length =
   ContextTokens` as-is; `output_length = GeneratedTokens` (≥1); encoder
   work = NumImages × 448² ViT forwards (AIC-costed on rtx_5090 silicon);
   per-request tile batches preserved; disjoint hash_ids; timestamps
   preserved; class/group labels carried; 151 duplicates dropped.
2. **Scenario selection**: full 7 days for baselines; burst episodes
   sampled by peak/duration (no taxonomy needed — §K); the six largest
   frames-floods as headline autoscaling scenarios.
3. **Predictor interface** (`predictors/predictor.py`): three per-pool
   signals at 1-min granularity; horizon ≥ cold-start + onset budget
   (§I: minutes matter); frames-class signal is the highest-leverage
   target — burst detection on 2.7% of requests covers 81% of image work.
4. **Simulator fidelity**: encoder pool must batch per-request tile
   groups; prefill pressure super-linear during bursts (2.69× length ×
   higher rate) must emerge in the composed workload, not be assumed.
5. **Evaluation framing**: SLA compliance × GPU-hours against
   static-optimal and reactive baselines, scored specifically inside burst
   episodes — where §4 shows reactive scaling loses by construction.

## 7. Limitations (of the trace, to state in the thesis)

No image resolutions (counts only → fixed-448² scenario parameter); no
session/user identifiers; no latency or SLA ground truth (arrival-side
only); 7-day window (diurnal supported, weekly unsupported); 50/50
modality split by construction; `ContextTokens` embeds the *traced*
model's vision tokenization, not Qwen3-VL's (workload self-consistent, not
model-transferable).

## 8. Asset inventory

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

Narrative summary with all numbers: `summary.md` (per-section detail).
Dataset provenance: `../../data/source/README.md`.
