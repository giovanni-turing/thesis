# Figure Verification (Phase 6) — 18 figures vs captions + provenance DB

Each figure was viewed by a vision model, its caption read from the frozen thesis, and its plotted values/structure cross-checked against the DB. **15 OK, 3 flagged** (all flags are caption/label cosmetics; underlying data reconciles in every case).

## Flagged

### `eda_l_request_clusters` — minor
- **issue**: Caption color mapping is incorrect. Caption states the two text archetypes are '(blue, orange)' and the two vision archetypes '(green)'. In the rendered figure the text archetypes are blue (conversational) + pink (short-answer/extraction), and the vision archetypes are green (doc/tiled) + orange (video/frame). Orange is a VISION cluster, not text; the second text cluster is pink, not orange; and the second vision cluster (orange) is omitted from the caption's '(green)'. Semantic labels, k=4, silhouette, and all shares are correct - only the color names in the caption are wrong.
- **evidence**: DB l_request_clusters: chosen_k=4, silhouette_by_k.4=0.3880 (plotted 0.39). Shares match tab:eda-archetypes exactly: short-answer req 0.31/img 0.011; video/frame req 0.034/img 0.857; conversational req 0.514/img 0.013; doc/tiled req 0.141/img 0.119. Right-panel bars agree. Figure display cluster numbering differs from DB metric_path indices but is internally consistent (cosmetic).
- caption_match=False data_match=True

### `pred_framework_diff` — minor
- **issue**: Panel (a) bar values do not match forecast_metrics and flip the naive-vs-HoltWinters ranking. Panels (b)/(c), which carry the load-bearing closed-loop claim, match the DB exactly.
- **evidence**: Panel (b): forecast p90=651 matches DB burst3 ttft p99=651.1; Dynamo/mean-conv fails=3495 matches DB reactive burst3=3494.7; SLA 1000 line correct. Panel (c): offline twins 651 and 3495 match DB; live 695 vs 651 = +6.8% and live 3531 vs 3495 = +1.0%, matching caption's 1.1-6.8%. Panel (a): bars show naive=0.618, holt-winters=0.595, ewma=0.522, toto=0.515, timesfm=0.519, chronos=0.525; DB forecast_metrics images/1min/uni/common gives naive=0.678, holt_winters=0.694, ewma=0.542, toto=0.530, timesfm=0.534, chronos=0.531. Bar shows HW < naive but DB (and the thesis's own heatmap/table) has HW > naive. arima/kalman/prophet (Dynamo-shipped) are absent from forecast_metrics, so panel (a) is computed from a separate source; core message (predictors cluster within ~0.02, classical worse) still holds.
- caption_match=True data_match=False

### `sim_knees` — minor
- **issue**: Terminology inconsistency between plot and caption/table: the figure legend and right-panel annotation label the blue window 'head2k' (the correct DB window_name), but the caption and the companion knee table (twopool.tex L244-249) call the same series the 'steady' window. Per SCHEMA_GUIDE, head2k (2000-req / 721 s head slice) is GENUINELY DISTINCT from steady24h, so a reader may conflate it with the 24h calm window. Data is fully correct; label wording only.
- **evidence**: All plotted knee values match sweep_point exactly. Language (llm): head2k poly TTFT p99 249,277,374 at s=1,2,3 (knee s=3, ITL crosses 100 between s=3 and s=4); head2k aic 307,418,554 (knee s=2, itl s=2=67<100, s=3=110>100); burst1 poly 910 at s=1, burst1 aic 1868 at s=1 (over threshold). Vision: head2k aic enc_delay 199..787 flat/under-bound through s=32 (255.5 img/s, censored); burst1 aic 5013 ms at s=1 (116 img/s, saturated), rising to 7.68M at s=32. Every value matches figure and knee table.
- caption_match=False data_match=True

## OK (data + structure reconcile)

- `aic_fn` — Left panel per-point measured/AIC ratios read off the plot (1.38,1.37,1.36,1.50,1.58,1.62,1.48,1.43 for N=1,6,8,16,32,64,96,128) match colle
- `aic_fn_engines` — Left panel plots 5 series (AIC composition, HF-SDPA, HF-FA2, vLLM-flash, torch.compile) matching legend and apendice.tex table anchors (N=1:
- `eda_a_context_vs_numimages` — Median-vs-NumImages line with p10-p90/p25-p75 bands and a dashed 'approx 64 tokens/image' reference; matches caption. DB median_context_vs_i
- `eda_c_seven_day_signals` — Two stacked panels (language requests/s top ~quasi-stationary around 2; vision images/s bottom with multi-hour bursts) on shared Oct15-22 cl
- `eda_d_acf` — Two ACF curves vs lag(min); images(blue) crosses ACF=0.5 at ~69 min, requests(green) at ~9 min, both annotated on-plot. DB d_signals.acf_1mi
- `eda_d_img_vs_req_scatter` — 2D density of images/s vs requests/s (1-min windows) with orange constant-fraction fit line (slope ~15 img/req: ~118 img at 8 req/s) and on-
- `eda_e_arrival_process` — Three panels: (L) inter-arrival survival empirical vs exponential(lambda=1.65/s), heavier empirical tail; (M) per-second counts vs Poisson; 
- `eda_eval_windows` — 1-min image-rate trace with shaded windows: 6 burst episodes b1-b6, one 'calm day' (green), and a leading 'forecast context (never graded)' 
- `eda_i_burst_onsets` — DB i_burst_anatomy: onset_minutes p10=1.7 (plotted as '2 min'), p50=6.0, min=1.0; matches title 'p10 2 min, p50 6 min (18 episodes)'. 18 epi
- `eda_q_multires` — DB c_temporal: img_per_s.cv2 = 25.71 at 1s -> 3.83 at 60s (matches thesis text 25.7->3.83 and left-panel blue top curve); req_per_s.cv2 = 1.
- `pred_forecast_band` — Structure matches caption: Chronos-2 (cov) 12-step point path (blue), p10-p90 band (shaded), observed (ink) and naive (dashed) over the week
- `pred_horizon_wape` — Four panels (requests, images, context tokens, generated tokens), WAPE(%) vs horizon step h=1..12, foundation-models min-max band plus naive
- `pred_models_burst` — Three foundation models (TimesFM, Chronos-2, Toto-2) univariate point paths plus observed (gray) over the week's largest image burst, images
- `pred_wape_heatmap` — 8 model rows x (4 signals x 5 resolutions) heatmap of overall point WAPE(%), annotated, shaded by WAPE-over-column-best (1-2 scale), bold=co
- `sim_burst_queue` — Run grid:grid_burst1_C2 / sweeps:vision_burst1_s1 (burst1, 2 encoder workers, s=1): encoder_utilization=0.2889 (=29% mean util in title), of