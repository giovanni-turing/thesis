# Figure regeneration spec — post-campaign pass (V01/V02/V03 + per-image deep dives)

Status: QUEUED until the silicon campaign STOPs (GPU/venv contention rule).
Owner: single dedicated agent, one pass over `figuras_new/` producers.
Every regenerated figure re-enters the visual mailbox for per-image re-verdict.

## Family-wide requirements (apply to every matplotlib PDF export)

1. `plt.rcParams['pdf.fonttype'] = 42` (Type 42 TrueType embedding) — kills the
   PUA codepoint substitutions (V01: 14 figures, U+E000–F8FF range) and the
   reversed rotated-text streams (V02: 6 figures, e.g. `snekot txetnoc`).
2. Canvas standardization (V03 + per-image 011): export on a compact canvas so
   nominal font sizes survive placement. Target: canvas width ≈ the LaTeX
   placement width (e.g. ≈265 pt for `0.62\linewidth`), fonts 8–10 pt nominal
   = 8–10 pt effective, line weights ≥0.6 pt effective, markers ≥3 pt
   effective. No figure may land below 6 pt effective text.
3. Data immutability: regeneration MUST NOT alter plotted data. Each figure's
   producer reads the same `figuras_new/_data/*.parquet`; re-verify per-figure
   that extracted series match pre-regen values (byte-diff of the underlying
   parquet + spot re-extraction of plotted points).
4. `sim_metric_frontier.pdf` is byte-gated: script + PDF must update together
   (delivery-suite regeneration gate).
5. After regen: rebuild `tese.pdf`, re-run `verification/metric_stack_gate.py`,
   re-raster every figure at 130 dpi + print-scale (0.38×) grayscale, and
   submit for visual re-verdict.

## Per-image acceptance criteria (from deep-dive packets, accumulating)

### eda_a_context_vs_numimages (packets 011 v1 [withdrawn] + 011 v2, MAJOR)
- Compact canvas ≈265×150 pt (current 690×390 → 0.383× scale, 3.06 pt text).
- Uncertainty bands: give p10–p90 and p25–p75 boundary styles or materially
  stronger luminance separation (current band-vs-band contrast 1.14:1; outer
  band 1.16:1 vs white — invisible in 150 dpi grayscale print).
- The captioned x=0 vs x=1 comparison must be readable: annotate or inset it
  (marker centers currently 0.27 pt apart vs 1.83 pt marker diameter).
- Keep: linear axes, solid-circle median vs dotted reference distinction.
- Caption itself already realigned (main-bridge D103, accepted 2/2).

### Per-image target canvases (deep-dive packets 012–020, all MAJOR)

Every packet so far instantiates the same triple defect — canvas overscale
(0.375–0.471×, effective text 3.0–3.8 pt), reversed rotated y-axis text
streams, PUA glyph corruption — with a per-figure target canvas:

| packet | figure | target canvas (pt) | placement |
|---|---|---|---|
| 012 | eda_c_seven_day_signals | ≈367×220 | — |
| 013 | eda_eval_windows | ≈405×150 | — |
| 014 | eda_d_img_vs_req_scatter | ≈265×160 | 0.62\linewidth |
| 015 | eda_i_burst_onsets | ≈350×155 | — |
| 016 | eda_q_multires | ≈376×165 | — |
| 017 | aic_fn | ≈427×166 | \linewidth |
| 018 | sim_knees | ≈427×175 | \linewidth |
| 019 | sim_burst_queue | ≈427×213 | \linewidth |
| 020 | pred_forecast_band | ≈376×148 | 0.88\linewidth |
| 021 | pred_horizon_wape | ≈367×245 | 0.86\linewidth |
| 022 | sim_frontier | ≈427×234 | \linewidth |
| 023 | sim_metric_frontier | ≈350 wide | 0.82\linewidth |
| 024 | pred_framework_diff | ≈427×160 | \linewidth |
| 025 | aic_fn_engines | ≈393×153 | 0.92\linewidth |
| 026 | pred_wape_heatmap | ≈427×148 | \linewidth |
| 027 | pred_models_burst | ≈376×148 | 0.88\linewidth |

Figure-specific extras: 014 colorbar + axis-title glyphs; 017 the 12 PUA
multiplier glyphs in numerical annotations; 020/027 PUA timestamp/date
colons; 024 vertical x-label wrapping corruption (3 panels); 025 PUA hyphens
+ vertical annotation streams; 026 the 200+ heatmap cell numbers must land
≥7 pt on paper (currently 2.65 pt — worst legibility in the set).

Verdict exceptions: 023 sim_metric_frontier is MINOR and already
V01/V02-free (fonttype-42 clean) — canvas compaction only, and it is the
byte-gated figure (script+PDF update together). 022 sim_frontier has no
font/stream defect listed — canvas compaction only.

FIGURE SERIES COMPLETE: 17 packets (011–027) cover the full included-figure
set. 15 MAJOR + 1 MINOR-compaction (023) + 1 compaction-only (022). The
regen agent must satisfy every packet's Required Action list plus the family
requirements above; each figure re-enters the mailbox for re-verdict.
