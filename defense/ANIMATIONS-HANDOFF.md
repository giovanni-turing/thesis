# Handoff: Interactive Defense Animations for the Thesis Presentation

**Audience of this document:** an agent (or human) who will *build* the interactive
animations, without having read the thesis. Everything needed — thesis context, the
exact numbers each animation must show, data-artifact paths and schemas, interaction
design, delivery constraints, and build order — is in this file. Written 2026-07-19.

---

## 1. Context: what the thesis is and why animations

Thesis: **"Predictive Per-Pool Provisioning for Modality-Disaggregated Multimodal
Model Serving"** (Giovanni Oliveira, IME-USP; advisor Fabio Kon, co-advisor Emílio
Francesquini). Master's defense. Source: `/home/gio/tese/tex/tese.tex` (root) with
chapters `intro, related, trace-eda, predictors, aiconfigurator, twopool, baselines,
closedloop, validation, conclusion`. The defense deck is
`/home/gio/tese/slides/slides.tex` — a 21-frame Beamer deck following the RQ arc
(frame titles listed in §5 below). A Q&A prep doc exists at
`/home/gio/tese/defense/defense-qa.tex`.

The argument in one paragraph (the animations must serve THIS narrative):
multimodal serving splits into a **vision-encoder pool** (turns images into embedding
tokens) and a **language pool** (prefill + decode). Conventional autoscalers watch
request rate / utilization. On the only public production multimodal trace (Azure LMM,
1M requests / 7 days), the vision pool's demand signal (images/s) is **nearly
decoupled** from request rate (R² = 0.12), **~12× burstier** (CV² 3.83 vs 0.32),
**disjoint at the extremes** (Jaccard 0.02 between the two signals' top-1% minutes) —
yet the **most persistent/forecastable** (Hurst ≈ 0.93, 69-min ACF half-life).
Zero-shot time-series foundation models (Chronos-2, TimesFM-2.0, Toto-2.0) beat all
classical baselines at provisioning horizons; the p90 forecast edge is calibrated
(coverage 0.88–0.90). A two-pool simulator (encoder pool costed on RTX 5090 silicon
via NVIDIA aiconfigurator; language pool = Dynamo's discrete-event replay under
calibrated H100 timing) shows: saturation knees an order of magnitude apart; inside
the largest burst the encoder pool violates its tail SLA **at the trace's own rate at
29% mean utilization** — invisible to every dashboard signal. Closing the loop: a
p90-forecast-driven encoder schedule holds the tail SLA on **every window at every
cold-start lead 15–165 s** (burst windows pinned at the 588 ms zero-queueing service
floor) where an identically informed **reactive** controller loses the fastest-onset
burst (burst3, 1-minute onset) **at every lead** (p99 9.5–54 s). Week-scale: SLA met
in aggregate AND per-episode at **0.62× the deployable static encoder fleet's
GPU-time** (2.41M vs 3.87M worker-seconds). Language pool: the fix is a **tail-aware
capacity conversion** (mean-based conversion fails even with a perfect forecast);
language fleet near-break-even at 0.96×. Verdicts reproduce on the live Dynamo
control plane (mocked engines) within 1.1–6.8% TTFT p99.

Why animations: the thesis's core insights are *temporal dynamics* — queues flooding
while dashboards stay green, forecasts standing capacity up before a spike, lead time
killing a reactive controller — which static figures structurally cannot show. Each
animation replaces a static slide figure; none adds presentation time.

## 2. Hard constraints (non-negotiable)

1. **Fully offline, self-contained HTML.** One `.html` file per animation, all data
   inlined (JSON embedded in a `<script>` tag or JS const), no CDN, no fetch, no
   external fonts. Defense-room networks are unreliable. Target directory:
   `/home/gio/tese/defense/anim/`.
2. **Real data only.** Every curve must be subsampled at *build time* from the
   ledgered artifacts listed in §4 (never synthesized/faked). Put the source artifact
   path in a small footer on each page — if a committee member asks "is this the real
   trace?", the answer must be *yes, and here is the file*.
3. **Presenter-proof controls** on every animation: play/pause, scrub bar, reset,
   playback-speed control. A committee member may interrupt mid-playback; the
   presenter must be able to pause, scrub back, and resume. Keyboard: space =
   play/pause, ←/→ = step, R = reset.
4. **Static end state = the thesis figure.** When playback finishes (or on load,
   before pressing play), the display must match the corresponding figure in the
   thesis, so a total JS failure still leaves a presentable image.
5. **Big-room legibility**: dark-on-light, ≥18 px axis labels, thick strokes;
   projector-safe colors (avoid thin pastels). 16:9 layout.
6. Load the `dataviz` skill before writing any chart code (project convention).
7. Keep each animation's *interactive* moment ≤ ~30 s of live presentation time.

## 3. The four animations to build (priority order)

### A1. "The invisible failure" — queue replay vs. the operator's dashboard
**Slide it replaces/augments:** "The mechanics of decoupling: knees an order of
magnitude apart" (and echoes Fig. `sim_burst_queue` in the thesis, Ch. 6).
**Insight to convey:** the encoder pool violates its tail SLA *episodically all day at
the trace's own recorded rate*, while every signal a reactive operator watches reads
healthy. Mean utilization 29%; request rate ~2.2 req/s (unremarkable); queue spikes
past 1,000 images (peak 4,701 queued) for 805 s spread across the 8.3 h window; p99
encoder delay 5.0 s vs the 1 s SLA; the pool fully drains between excursions (that's
why the mean stays low).
**Design:** split screen. LEFT = "what the operator sees": request-rate strip
(flat), a mean-utilization gauge hovering ~29% with a green "HEALTHY" badge, minute-
averaged image rate. RIGHT = "what is actually happening": per-second queued-image
depth animating (area chart building in time), a running p99 encoder-delay counter
that crosses 1,000 ms and turns red, red event flashes at each excursion. Shared
scrub bar over the 8.3 h window; default playback ~500× real time (~60 s full pass);
speed control 100×/500×/2000×.
**Data:** `simulation/results/sweeps/series/vision_burst1_s1.series.json` —
schema: `{freq_s: 1, arrival_speedup: 1.0, series: [{t, img_arrived, img_completed,
queue_imgs_end, busy_workers_end}, ...]}`, 29,940 rows (one per second). Compute the
dashboard's "utilization" as a trailing 60 s mean of `busy_workers_end / 2` (the
window runs the locked 2-encoder topology) and the minute-mean image rate from
`img_arrived`. Note the window in this artifact is named `burst1` in the sweeps dir
but corresponds to the *largest burst episode* window of Ch. 6 (8.3 h, mean 116
img/s, peak 370 img/s). The p99-delay counter can be a precomputed running quantile
over completed work embedded at build time (approximate from queue depth × service
rate if per-request delays aren't in the artifact — but check
`simulation/results/sweeps/summary.json` first; it holds the official per-sweep
percentiles, and honesty requires the on-screen number to match the ledgered 5,013 ms
final p99).

### A2. "The race" — forecast vs. reactive at burst3's one-minute onset, lead slider
**Slide:** "Forecast holds the SLA where reactive breaks". This is RQ4 as an
experience; the single most persuasive artifact for the committee.
**Insight:** both controllers watch the SAME image signal with the same worker law
(C = ⌈demand/ρ⌉, ρ = 15 img/s per worker, 3-min scale-down hysteresis, cold-start
lead L). The reactive one reads the trailing observed rate → orders workers *after*
the onset → they arrive L seconds late into a fatal backlog. The forecast one reads
the archived Chronos p90 band at issue time → capacity (~21 workers) is standing
before the spike. Reactive p99: 9,481 ms at L=15 s, 16,079 at 30, 28,342 at 45,
54,170 at 300 (degrading toward never-scaled). Forecast p99: **588 ms at every lead**
(the zero-queueing service floor = f(64) 316.4 ms full-batch forward + 272 ms p99
handoff). Lead-invariance is the signature of anticipation.
**Design:** two synchronized lanes (top: FORECAST p90, bottom: REACTIVE), each
showing: offered image rate (same curve both lanes), the policy's worker-count
staircase, queued-image area, and a live p99 badge (green/red vs the 1,000 ms bound).
THE control: a **cold-start lead slider L ∈ {15, 30, 45, 300} s**. Dragging it
re-runs/re-displays both lanes: reactive worsens monotonically, forecast does not
move. Precompute all four lead scenarios per lane at build time (8 scenario bundles
embedded); the slider just swaps datasets — no in-browser simulation needed.
**Data:** worker schedules: `simulation/results/aggregate44/fc_p90_L{15,165}_issuetime.sched.json`
(format: list of `[t_seconds, worker_count]` step points) — but these are week-scale;
crop to the burst3 window. Reactive schedules and per-lead outcomes: the reactive
rows live in the factorial results
`simulation/results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json`
and the reactive table numbers are ledgered (Table `tab:base-react-enc` in
`tex/baselines.tex`). Burst3 offered-load series: derive from the trace-window series
(see `analysis/trace_eda/series/rates_*.parquet`, 1 s or 15 s resolution, cropped to
burst3's 27-min span; burst3 ≈ 3,093 requests, onset 1 min, peak ~370 img/s — the
exact window envelope is in the eval-windows definition used by
`simulation/run_44_factorial_issuetime.py`). If a per-second reactive queue series
for burst3 isn't already archived, reconstruct the queue with the simple FIFO law
(arrivals from the trace, service = C(t)·ρ) — but label it "schematic queue,
ledgered endpoints" OR regenerate properly via
`workload/trace_to_two_pool.py` with the converter flags (ask the owner before
regenerating; GPU/venv conventions in §6).
**Fallback static end state:** the four-lead reactive-vs-forecast p99 bar pairs
(9.5/16.1/28.3/54.2 s vs 0.588 s ×4).

### A3. Forecast-band player — tiles issued, then reality lands
**Slide:** "Zero-shot foundation models forecast the pool signals" + "What makes a
forecast provisioning-grade".
**Insight:** each 12-step forecast tile is *issued before* the bins it predicts
(rolling origin, stride = horizon, so tiles abut into a continuous path — the signal
a scaler consumes). The p90 edge is calibrated: ~11% of image bins pierce it
(nominal 10%). The point path rides the burst *plateau* (the provisioning envelope),
not individual spikes. p50 hugs the median → downstream it sizes to the mean and
fails; p90 is the provisionable headroom. All three models are nearly coincident —
kills the "did you pick a lucky model" question.
**Design:** the week's largest image burst (2024-10-21, peak 370 img/s) at 1-min
bins. Playback: at each origin, the 12-step point path + p10–p90 band stamps forward
from a "now" cursor as a highlighted tile; then realized bins draw in as ink dots —
inside the band or piercing it (pierce events flash + increment a running "p90
exceedance: n/N ≈ 11%" counter). Toggles: model (Chronos-2 / TimesFM / Toto-2),
quantile emphasis (p50 vs p90), naive baseline overlay. End state = thesis Fig.
`pred_forecast_band`.
**Data:** `predictors/results/{chronos,timesfm,toto}_images.parquet`. Schema
(verified): columns `resolution (string, e.g. "1min"), variate, origin (int),
h (1–12), step, ts (timestamp[ns]), y_true, point, p10…p90`. 648,420 rows in the
chronos images file; filter `resolution == "1min"` (or the 1-minute label present in
the file — verify distinct values), crop ts to the burst day, export a compact JSON
at build time. Quantile-coverage ground truth:
`predictors/results/metrics/quantile_coverage.json`.

### A4. Decoupling as a week-long clock
**Slide:** "The decoupling: request rate cannot see vision demand" (the premise
slide — the committee must *believe* this before anything else matters).
**Insight:** the two pools' demand signals live on the same clock but different
planets. Requests/s is quasi-stationary (weekly p99 4.35, max 7.8); images/s erupts
to 370 img/s ≈ 16× its mean while the request rate in those same minutes stays under
4.5. R² of the best constant-fraction fit: 0.123 (α = 15.1 img/req). The two
signals' top-1% minutes share only 5 of ~100 each (Jaccard 0.02).
**Design:** two vertically stacked strips playing across the 7 days (60–90 s full
pass): requests/s on top, images/s below (log or dual-scale — images dwarf).
Alongside, the img-vs-req scatter builds point-by-point at the playhead minute, the
R² = 0.12 fit line appearing after enough mass; when a "hot" minute occurs in either
signal, tick marks drop on that signal's edge — at the end, the two tick sets are
visibly disjoint, with the 5 shared minutes flashed. End state = thesis Fig.
`eda_d_img_vs_req_scatter` + `eda_c_seven_day_signals` combined.
**Data:** `analysis/trace_eda/series/rates_1min.parquet` (per-minute totals of all
four signals; this is the canonical materialized series — the forecast parquets'
metadata names it as their source). 10,080 rows → inline directly.

### Bench (build only if time remains)
- **A5 Knees explorer:** latency-vs-offered-load per pool with a speedup slider and a
  polynomial-vs-AIC timing toggle that flips the burst verdict live (910 ms "pass" →
  1,868 ms fail). Data: `simulation/results/sweeps/summary.json` + the
  `llm_burst1_{poly,aic}_s*.json` files. Best held for Q&A (RQ3 fidelity).
- **A6 Cost odometer:** week-scale worker-schedule ribbons (static C=8, forecast p90,
  reactive) with racing GPU-time counters → 3.87M vs 2.41M (0.62×) vs 2.61M, plus
  per-episode pass/fail lights — reactive's aggregate metric shows green while its
  burst3 light is red (dashboard-masking inside the evaluation metric). Data:
  `aggregate44/*.sched.json` + `*.stats.json`.
- **A7 Chunk-dispatch micro-anim:** a 9,409-image request shattering into 148
  ≤64-image chunks fanning across free workers (FIFO, chunk-parallel). Explanatory
  only; for the architecture slide if the committee is systems-shallow.

## 4. Data-artifact index (all paths relative to `/home/gio/tese`)

| Artifact | Contents / schema | Feeds |
|---|---|---|
| `simulation/results/sweeps/series/vision_burst1_s1.series.json` | per-second `{t, img_arrived, img_completed, queue_imgs_end, busy_workers_end}`, 29,940 s, freq 1 s, speedup 1.0 | A1 |
| `simulation/results/sweeps/series/` (others) | same for s2..s32 and head2k window | A5 |
| `simulation/results/sweeps/summary.json` | official knee/percentile numbers per sweep | A1, A5 |
| `simulation/results/aggregate44/fc_p90_L{15,165}_issuetime.sched.json` | worker schedule `[[t, C], ...]`, week-scale | A2, A6 |
| `simulation/results/aggregate44/*.stats.json` | ledgered p99 / worker-time per policy/lead | A2, A6 |
| `simulation/results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json` | 60-cell issue-time factorial (window × model × lead, warm+strict) | A2 |
| `simulation/results/riders44/detection_delay.json` | onset-detection leads/lags per episode | A2 annotations |
| `predictors/results/{chronos,timesfm,toto}_images.parquet` | forecast archive; cols: resolution, variate, origin, h, step, ts, y_true, point, p10–p90 | A3 |
| `predictors/results/metrics/quantile_coverage.json` | empirical band coverage (p90 ≈ 0.88–0.90) | A3 counter |
| `analysis/trace_eda/series/rates_1min.parquet` (and finer) | canonical per-bin demand series, all 4 signals | A4, A2 offered load |
| `analysis/trace_eda/*_stats.json` | every EDA number (R², CV², Jaccard, onsets...) | A4 labels |
| `simulation/results/live51/` | live-vs-twin runs (validation chapter) | optional Q&A material |
| `progress/results-ledger.md` | provenance ledger: artifact + command + date per result | verify any number |

**Cross-check duty:** before inlining any number into an animation, verify it against
the thesis text (`tex/*.tex`) and/or `progress/results-ledger.md`. On any
discrepancy between an artifact and the text, the *ledgered/text* number wins on
screen; flag the discrepancy to the owner rather than silently reconciling.

## 5. The deck (21 frames) and where each animation lands

Frame titles, in order: The thesis in one breath / Outline / Multimodal serving
disaggregates by modality / Research questions (= the chapter arc) / Positioning /
Dataset characterization / **The decoupling** (→ A4) / ...but that demand is the most
persistent / **Zero-shot foundation models forecast the pool signals** (→ A3) / What
makes a forecast provisioning-grade (→ A3's toggles) / System architecture (→ A7 if
built) / Encoder costs collected and validated on real silicon / **The mechanics of
decoupling: knees** (→ A1; A5 as Q&A backup) / Per-pool mechanism / **Forecast holds
the SLA where reactive breaks** (→ A2) / What makes it work: the ablation ledger /
**Headline economics** (→ A6 if built) / Three evidence layers / Scope and future
work / Contributions.

## 6. Practical build notes

- **Environment:** parquet reading needs pandas/pyarrow — use the EDA venv
  (`eda/.venv`, RAPIDS stack, has pyarrow) or any python3 with pyarrow. Build-time
  data extraction scripts should live in `defense/anim/build/` (one script per
  animation, writing the inlined-JSON `.html`). Keep extraction scripts versioned —
  workspace convention is *every number from a versioned script over archived
  inputs*.
- **Subsample budget:** keep each HTML ≤ ~3–5 MB. A1: 29,940 rows × 5 ints is fine
  raw. A3: filter to 1-min resolution + burst day ≈ a few hundred tiles. A4: 10,080
  minutes × 2–4 signals raw is fine.
- **Tech (decided):** vanilla JS + canvas for A1/A2 (synchronized multi-panel
  replays with custom transport — Plotly fights these); Plotly.js *inlined*
  (~3.5 MB, still offline) is acceptable for A3/A4/A5 if it speeds you up, but
  vanilla is the default. Mathematica was considered and rejected (no offline
  HTML export path, license on the presentation laptop, can't ingest the
  artifacts). Shared tiny helper (scrubber, transport controls, number badges)
  can be copy-pasted per file — self-containment beats DRY here.
- **Status:** A1 and A2 are BUILT (`anim/a1_invisible_failure.html`,
  `anim/a2_the_race.html`; both reviewed at 1080p and 720p; build scripts +
  templates in `anim/build/`, README in `anim/`). A2 went the option-(b) route:
  real converter re-runs per policy×lead with `--series-out`, endpoint-asserted
  against the ledger (see README provenance notes — includes the
  `a2_conv_snapshot.py` shim that restores the manuscript's snapshot encoder
  graph against the venv's newer patch-embed operator). A1's
  template is the reference implementation for transport controls, unified
  crosshair/tooltip, per-pixel max-bucket downsampling (stride sampling hides
  the spikes — don't), `#t=<seconds>` deep links, and headless-chromium review
  screenshots. Copy it for A2–A4. Note: snap chromium can only write screenshots
  under `$HOME`; the Playwright MCP plugin needs Chrome at /opt/google/chrome
  (absent) — use `chromium --headless --screenshot` instead.
- **Presentation mechanics:** presenter shows the Beamer PDF in a browser tab (or
  pdfpc) with one tab per animation; Ctrl-Tab/⌘-Tab to switch. Optionally build
  `defense/anim/index.html` with keyboard-navigable links (1–4). Test on the actual
  presentation laptop at projector resolution (1920×1080 and 1280×720).
- **Do not commit large intermediate JSON** to the repo root; generated HTML in
  `defense/anim/` is fine (the `defense/` dir is currently untracked — ask the owner
  whether to commit it).
- **Results-ledger habit:** when an animation is finalized, add a line to
  `progress/results-ledger.md` (artifact, generating script, date, which slide it
  feeds) — standing workspace convention.

## 7. Key numbers cheat sheet (for on-screen badges; all ledgered)

- Trace: 1,000,000 requests, exactly 7 days (2024-10-15→22 UTC), 50.0% text-only;
  image counts are perfect squares (k×k grids), max 97² = 9,409 images/request;
  frames class (k>10) = 2.7% of requests, 81.2% of image volume; bursts are 93–96%
  frames-class.
- Decoupling: R² = 0.123 (images vs requests; α = 15.1 img/req), 0.654 for decode;
  Pearson r 0.36 vs 0.81; Jaccard of top-1% minutes 0.02 (5 shared of ~100/106).
- Burstiness/persistence (1-min): CV² 3.83 vs 0.32; peak/mean 15.6× vs 4.7×; ACF
  half-life 69 vs 9 min; Hurst ≈0.93 vs ≈0.83; Fano 1.8 (1 s) → 938 (1 h).
- Onsets: median 6 min baseline→peak, fastest 1 min; median steepest single-minute
  jump 208 img/s. Largest burst: 370 img/s peak while requests ≤ 4.48 req/s.
- Forecasting: FMs win all 20 cells; images 1-min WAPE ≈ 53% (best), EWMA 54.2,
  naive 67.8; 12-step degradation ≈ +2 WAPE pts; p90 coverage 0.88–0.90; ~11% of
  image bins pierce p90.
- Encoder cost: f(1) = 8.16 ms, f(64) = 316.4 ms (4.94 ms/img amortized); dispatch
  cap 64 images; largest request = 148 forwards ≈ 46 s kernel time; AIC vs vLLM
  within 12.8% (N ≤ 64); vs HuggingFace-eager 1.4–1.6× (execution-stack effect).
- Burst window (largest, 8.3 h): mean 2.17 req/s but 116 img/s; encoder p99 delay
  5,013 ms at 29% mean utilization, 2 workers; queue > 1,000 imgs for 805 s, peak
  4,701; worst second lands 2,726 images.
- SLA: TTFT p99 < 1 s, ITL p99 < 100 ms, encoder-delay p99 < 1 s.
- Knees: language s=2 (calibrated, ITL-bound; 5.5 req/s) vs vision uncensored at
  s=32 (≥256 img/s) — >10× apart. Burst at TP1: TTFT p99 1,868 ms (polynomial
  wrongly reads 910 ms "pass"); TP2×2 same GPUs passes at 748 ms.
- Static optima: bursts need C* = 6–8 encoders + TP2×2; calm day 2 + TP1×2;
  deployable static = 8 + TP2×2 (4×/2× calm-day overprovisioning).
- Reactive encoder (ρ=15): burst3 fails at EVERY lead — p99 9,481 / 16,079 /
  28,342 / 54,170 ms at L = 15/30/45/300 s. Forecast p90: 588 ms at every lead
  (= f(64) 316.4 + p99 handoff 272 ms floor); calm day ≤ 734 ms; 60/60 factorial
  cells pass at ρ ∈ {10,15,20}; ρ=25 drops 9 cells (all burst5).
- Language pool: reactive fails all 14 configs on tails while meeting its own
  window-mean law; tail-aware conversion (belief 10.07 req/s vs tail-knee 1.62
  req/s per TP2 replica) flips burst1 to PASS at 736 ms; p90 week pass at 651 ms,
  518.6 H100 GPU-h = 0.96× burst-static (Chronos-specific; Toto/TimesFM pass at
  1.16–1.19×); p50 passes week on language (828 ms) but fails encoder everywhere.
- Week aggregate (5.60-day span, 749,601 requests, 11.4M images): p90 forecast
  2.41M worker-s = **0.62×** static 3.87M, p99 588 vs 644 ms, per-episode clean;
  reactive 2.61M appears to pass aggregate but fails burst3 (masked: burst3 ≈
  3,100 requests < 0.5% of span); p50 0.25× but p99 2,735 ms FAIL. ρ frontier:
  0.89× (ρ=10) → 0.48× (ρ=20, clean) → 0.40× (ρ=25, dirty).
- Live anchor (burst3, real Dynamo control plane, mocked engines): forecast PASS
  695 vs 651 ms (+6.8%); reactive FAIL 3,531 vs 3,495 ms (+1.1%); replica-seconds
  within 5.3–7.6%; ITL verdicts agree both directions.
- Handoff/fabric caveat: 588 ms floor assumes embedding-only handoff or ≥100 Gbps
  fabric; at 4× DeepStack payload on 25 Gbps every policy fails (1,087 ms handoff
  floor) — fabric requirement, not policy weakness. Do not let an animation imply
  otherwise.

## 8. Honesty guardrails (repeat: the committee will probe)

- Label the reactive controller as **identically informed** (same image signal, same
  law/ρ/hysteresis/lead) — the win is anticipation + calibrated headroom, not signal
  access or tuning.
- burst3's forecast pass is **graduated headroom, not clean detection** (the p90 band
  lags the onset at h=1 there); don't animate it as an "alarm fires early" story.
- The 588 ms floor rows are distinct runs that coincide at the service floor; say
  "pinned at the service floor", not "identical runs".
- A2's lead-invariance is *feasibility* invariance; cost is flat only under the
  warm-pool readiness model (0.59–0.62× under strict re-warm).
- Language-pool closed loop is a **conversion result under a held forecast cursor**,
  not a second anticipation experiment — if A6 touches the language pool, phrase it
  that way.
- Everything derives from ONE 7-day trace of one cluster (50/50 modality split by
  construction); simulation is open-loop; decode signal is an offered-work upper
  bound. Keep a one-line scope footnote available on each page (hidden behind an
  "ⓘ" toggle is fine).
