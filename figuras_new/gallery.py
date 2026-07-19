"""Build index.html: old (matplotlib) vs new (plotly) side-by-side per figure,
with the design rationale. Open figuras_new/index.html in a browser to review;
each 'interactive' link opens the zoomable/hover plotly version."""
import html, os

HERE = os.path.dirname(os.path.abspath(__file__))

# (new_name, old_relpath, title, change)
FIGS = [
 # ---- EDA ----
 ("eda_a_context_vs_numimages", "../figuras/eda/eda_a_context_vs_numimages.png",
  "Context tokens vs image count",
  "Added a two-level uncertainty band (p10–p90 + p25–p75) and an explicit "
  "≈64-tokens/image reference line so the slope claim is visible on-chart; "
  "hover exposes the sample count n behind each image-count bin."),
 ("eda_c_seven_day_signals", "../figuras/eda/eda_c_seven_day_signals.png",
  "Seven-day arrival signals",
  "Shared-x zoomable panels with midnight day-boundary gridlines and a filled "
  "vision area so the diurnal rhythm and burst envelope are legible; p99 line kept."),
 ("eda_d_acf", "../figuras/eda/eda_d_acf.png",
  "Demand-signal autocorrelation",
  "Marked the actual half-life crossings (9 vs 69 min) with droplines + labels — "
  "the scientific payload — instead of only the generic 0.5 line."),
 ("eda_d_img_vs_req_scatter", "../figuras/eda/eda_d_img_vs_req_scatter.png",
  "Images vs request rate",
  "Replaced a 10k-point overplotted scatter with a 2-D density heatmap: the mass "
  "concentration near the origin and the weak trend are now both readable; R² called out."),
 ("eda_e_arrival_process", "../figuras/eda/eda_e_arrival_process.png",
  "Arrival process (non-Poisson)",
  "Faithful 3-panel port with interactive log axes and hover; cleaner Poisson-vs-"
  "empirical marker contrast."),
 ("eda_i_burst_onsets", "../figuras/eda/eda_i_burst_onsets.png",
  "Burst onset times",
  "Replaced a 25-bin histogram over ~18 episodes (mostly empty bins) with an ECDF "
  "that reads p10/p50 directly; kept the peak-vs-onset scatter."),
 ("eda_l_request_clusters", "../figuras/eda/eda_l_request_clusters.png",
  "Semantic request clusters",
  "Kept the WebGL cluster scatter but replaced the redundant second scatter with a "
  "request-share vs image-share bar — surfacing the headline stat (3.4% of requests "
  "= 86% of images) as its own mark."),
 ("eda_q_multires", "../figuras/eda/eda_q_multires.png",
  "Burstiness vs binning window",
  "Faithful port; added faint guide lines at common monitoring windows (1/15/60 s) "
  "and percent-formatted attenuation axis; interactive hover per signal."),
 ("eda_eval_windows", "../figuras/eda/eda_eval_windows.png",
  "Stratified evaluation harness",
  "Same timeline; staggered the burst labels onto two rows to stop b2/b6 and b4/b5 "
  "collisions; hover reveals each window."),
 # ---- predictors ----
 ("pred_horizon_wape", "../figuras/pred/pred_horizon_wape.png",
  "Point-forecast error vs horizon",
  "Collapsed the three near-identical foundation-model lines into a min–max envelope "
  "(honest: the band is thin because they agree) and kept the baselines as distinct "
  "dashes — 6 lines → 1 band + 3 lines per panel."),
 ("pred_forecast_band", "../figuras/pred/pred_forecast_band.png",
  "Forecast band over the burst",
  "Faithful port with on-chart coverage callout (p90 pierced by ~8% of bins) and "
  "interactive zoom into the regime collapse."),
 ("pred_wape_heatmap", "../figuras/pred/pred_wape_heatmap.png",
  "WAPE heatmap (all cells)",
  "Faceted into 4 target panels (cleaner than white separators), bold = column-best, "
  "shared ÷column-best colorbar."),
 ("pred_framework_diff", "../figuras/pred/pred_framework_diff.png",
  "Framework comparison (3 panels)",
  "Panel (a) now starts at 0 instead of 0.50 — the truncated baseline exaggerated "
  "differences and undercut the 'accuracy is nearly identical' message; value labels "
  "preserve the ranking detail. SLA lines kept."),
 ("pred_models_burst", "../figuras/pred/pred_models_burst.png",
  "Three models over the burst",
  "Faithful port; observed demoted to a thin grey reference so the three coincident "
  "model paths read as the subject; interactive."),
 # ---- sim ----
 ("sim_knees", "../figuras/sim/sim_knees.png",
  "Saturation knees per pool",
  "Faithful two-panel port with ringed knee markers, de-duplicated legend, and hover "
  "on every swept point."),
 ("sim_burst_queue", "../figuras/sim/sim_burst_queue.png",
  "Vision-pool burst queue",
  "Faithful port; peak backlog marked with a labelled point; utilization folded into "
  "the panel titles to sharpen the 'low util yet 4,701 queued' contrast."),
 # ---- aic ----
 ("aic_fn", "../figuras/aic/aic_fn.png",
  "Encoder f(N): AIC vs silicon",
  "Reproduced the (script-less) thesis figure from its data; ratio labels kept, and "
  "the kernel ledger now uses proper hatching for out-of-graph categories so the "
  "growing elementwise/gather overhead is legible."),
 ("aic_fn_engines", "../figuras/aic/aic_fn_engines.pdf",
  "Encoder f(N) across engines (appendix)",
  "Faithful port of the multi-engine comparison + ratio panel; palette-consistent "
  "colours, the ±12.8% band and N=64 FIFO-cap line kept, interactive hover. "
  "(Original is a PDF, shown as a link.)"),
]

cards = []
for new, old, title, change in FIGS:
    old_el = (f'<a href="{html.escape(old)}" target="_blank">open original PDF ↗</a>'
              if old.endswith(".pdf")
              else f'<img loading="lazy" src="{html.escape(old)}">')
    cards.append(f"""
    <section class="fig">
      <h2>{html.escape(title)} <span class="fn">{new}</span></h2>
      <p class="change">{html.escape(change)}</p>
      <div class="pair">
        <figure><figcaption>original (matplotlib)</figcaption>
          {old_el}</figure>
        <figure><figcaption>new (plotly) &middot;
          <a href="{new}.html" target="_blank">interactive ↗</a> &middot;
          <a href="{new}.pdf" target="_blank">pdf</a></figcaption>
          <img loading="lazy" src="{new}.png"></figure>
      </div>
    </section>""")

doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Thesis figures — redesign review</title>
<style>
  :root{{color-scheme:light dark}}
  body{{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    max-width:1500px;margin:0 auto;padding:24px;color:#111;background:#fafafa}}
  h1{{font-size:24px;margin:0 0 4px}}
  .lead{{color:#555;margin:0 0 24px}}
  .fig{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;
    margin:0 0 20px}}
  .fig h2{{font-size:17px;margin:0 0 4px}}
  .fn{{font:12px ui-monospace,monospace;color:#888;font-weight:400}}
  .change{{color:#374151;margin:0 0 12px;max-width:110ch}}
  .pair{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
  figure{{margin:0}}
  figcaption{{font-size:12px;color:#6b7280;margin:0 0 4px}}
  img{{width:100%;height:auto;border:1px solid #eee;border-radius:6px;background:#fff}}
  a{{color:#2a78d6}}
  @media (max-width:900px){{.pair{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>Thesis figures — redesign review</h1>
<p class="lead">18 figures, each rendered fresh in plotly from the same underlying data
(no GPU; CPU-reproduced the few GPU-only derivations). Left = current thesis figure,
right = proposed replacement. Nothing in <code>figuras/</code> was touched.
PDFs + interactive HTML are alongside each PNG in <code>figuras_new/</code>.</p>
{''.join(cards)}
</body></html>"""

open(os.path.join(HERE, "index.html"), "w").write(doc)
print("wrote", os.path.join(HERE, "index.html"))
