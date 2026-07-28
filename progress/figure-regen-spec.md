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

### eda_c_seven_day_signals (packet 012) — criteria TBD from packet
### eda_eval_windows (packet 013) — criteria TBD from packet

(Continue appending one block per deep-dive packet as the series streams in;
final pass must cover every packet's Required Action list plus the family
requirements above.)
