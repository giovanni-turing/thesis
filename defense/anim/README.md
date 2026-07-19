# Defense animations

Interactive, fully offline HTML animations for the defense presentation. Design
brief and remaining backlog: `../ANIMATIONS-HANDOFF.md`. Each page is a single
self-contained file (data inlined at build time from ledgered artifacts, no
network, no CDN) — open it in any browser, present alongside the Beamer PDF.

## Built

| File | Animation | Slide it serves |
|------|-----------|-----------------|
| `a1_invisible_failure.html` | A1 "The invisible failure" — split-screen replay of the largest burst window: the operator's dashboard (request rate, utilization — green all day) vs reality (offered image load, encoder FIFO backlog, SLA-excess in red). Ends on the verdict pair: HEALTHY dashboard vs encoder-delay p99 = 5,013 ms (5× the SLA) at 28.9% mean utilization. | "The mechanics of decoupling" |
| `a6_the_week.html` | A6 "The week" — five policies racing over the full 5.60-day evaluation span (749,601 requests): static C8, **Toto-2 p90** (issue-time, ρ=15, L=30 s), reactive, Toto p50, static C2. Per row: worker ribbon, cost odometer in both accountings with live ×-vs-static ratio, running p99, and per-episode verdict chips (b3/b5/b4/calm/b1 + week) that light as the playhead passes each episode. Reactive's aggregate p99 stays green while its burst3 chip goes red — the dashboard-masking phenomenon, annotated live. All 5 endpoints reproduce the ledgered week numbers (Toto p90: 588 ms at 0.6176× static). | "Headline economics" |
| `a2_the_race.html` | A2 "The race" — forecast (Chronos↔Toto p90, issue-time) vs reactive (trailing observed rate), identical law/ρ/hysteresis. **Episode selector** across the onset gradient (burst3/5/4/1 + calm + e10/e11/e13/e17) × **cold-start-lead slider** (15/30/45/165 s) + model toggle. Per lane: worker staircase, per-bin worst-delay dots (log, SLA line), live tickers (dual-account cost, mean delay, running p99, queue), SLA-infraction counter. e13 = the p90 forecast-miss boundary case (both fail). | "Forecast holds the SLA where reactive breaks" |
| `a8_onset_map.html` | A8 "The onset map" — all **18 burst episodes** as a phase diagram (onset speed × peak volume); fill = reactive verdict at a chosen lead, ring = forecast verdict; click a dot → replay in A2. Answers "how general is the reactive failure?" (9/18 reactive fails at L=30 s; 1 forecast miss). | Q&A / generality |
| `a9_dataset_kde.html` | A9 "Request-anatomy KDE" — all **1M requests** as a rotatable 3D density over (context, generation) tokens (Plotly, inlined) with an image-count range selector (k×k buckets). Text-only mountain range collapses to a needle for the frames class. | "Dataset characterization" |
| `a11_llm_race.html` | A11 "The race: language pool" — the A2 race for the **language pool** through Dynamo's real planner: forecast + tail-aware conversion vs reactive SLA planner. **5 windows** (incl. full week) × Chronos↔Toto × replica-lead 60/120/300 s = 39 planner replays. Live: TP2-replica staircase, running TTFT/ITL p99, GPU-h. Forecast 651 ms PASS vs reactive 3.49 s FAIL (window-mean law met, tail violated); week forecast 651 ms vs reactive 1.19 s at ½ the cost. Every L60 anchor reproduces the ledgered twin. | "Per-pool mechanism" (language) |
| `a12_composed_e2e.html` | A12 "The composed system" — **true end-to-end, both pools**. Each policy's encoder schedule → seam → language planner, with a **request-linked** ingress→first-token join (own encoder delay + own replayed TTFT; alignment asserted < 1 ms). Forecast E2E p99 **1.24 s** (enc 588 + TTFT 651) == thesis Ch. 6 modelled reconstruction, now MEASURED; reactive E2E **21.9 s** (encoder queue compounds into language). | The composed system / RQ3 |

## Controls (all pages)

- **space** play/pause · **←/→** step ±1 min · **R** reset · scrub bar · speed
  selector (250–2000×; 500× ≈ 60 s full pass)
- Hover any chart: synchronized crosshair + tooltip with all signals at that time
- Deep-link to a moment with `#t=<seconds>` (e.g. `a1_invisible_failure.html#t=29939`
  opens on the end-state verdict)
- `ⓘ` (bottom right) shows the scope/methodology note

## Build

```
# A1
python3 build/extract_a1.py   # ledgered artifacts -> data/a1_data.json (checks cross-verified)
python3 build/build_a1.py     # data + build/a1_template.html -> a1_invisible_failure.html
# A2 (regenerates real simulator runs; needs the eda + aiconfigurator venvs)
python3 build/gen_a2_fleet.py                   # 5 windows x {forecast,reactive} x L{15,30,45,165} = 40 runs (+series), ledger-asserted
eda/.venv/bin/python build/extract_a2_fleet.py  # per-request delays + running cost/mean/p99 tickers -> data/a2_data.json
python3 build/build_a2.py                       # -> a2_the_race.html
# (build/gen_a2_runs.py + build/extract_a2.py are the superseded burst3-only v1)
# A6 (5 aggregate-week runs; ~10 min)
python3 build/gen_a6_runs.py            # toto p90/p50, reactive, static C8/C2 over the 5.60-day span, ledger-asserted
eda/.venv/bin/python build/extract_a6.py  # 300-s bins + running tickers + per-episode p99 -> data/a6_data.json
python3 build/build_a6.py               # -> a6_the_week.html
```

A2 provenance notes: `gen_a2_runs.py` refuses to proceed unless each run's p99
reproduces the ledgered value (reactive rho15 cells of `results_44.jsonl`; the
p90/rho15 issue-time factorial). The converter runs through
`a2_conv_snapshot.py`, which restores the manuscript's load-bearing snapshot
encoder graph (the venv's current data branch adds a guarded patch-embed GEMM
operator, +0.93 ms at f(64), that postdates the thesis numbers). Reactive at
L=165 s is a new cell under the same ledgered law (its table entry is L=300 s).

Extraction prints cross-checks that must match the thesis text exactly
(queue > 1,000 imgs for 805 s; peak queue 4,701; worst second 2,726 images) and
fails loudly otherwise. Screenshots for review: `build/shots/` (generated with
headless chromium; regenerate with `--screenshot` against the `#t=` deep links).

Data sources (all in the results ledger):
`simulation/results/sweeps/series/vision_burst1_s1.series.json`,
`simulation/results/sweeps/traces/vision_burst1_s1.jsonl`,
`simulation/results/sweeps/summary.json`.

## Conventions

- Colors follow the thesis figures: requests = green `#008300`, image-side
  signals = blue `#2a78d6`; SLA-excess/critical = `#d03b3b`; status-good =
  `#0ca30c`. Palette validated (CVD + contrast) with the dataviz validator.
- Light mode only, deliberately — projector safety.
- Every on-screen headline number is the ledgered value (e.g. the verdict quotes
  the official per-request p99 from `summary.json`, not a recomputation);
  derived conveniences (backlog-implied wait = queue ÷ 404.6 img/s full-drain
  rate) are labeled as such in the `ⓘ` note.

## Full-trace coverage (every request simulated, both pools)

The `a13_runs/` batch simulates **all 1,000,000 trace requests** through both
pools with per-request records, on the policies defined over the whole 7-day
trace (statics + reactive; forecast policies are structurally undefined on the
first 1.4 days — no archived forecast exists there, the thesis coverage
boundary):

- **encoder**: `ft_static_C8`, `ft_static_C2`, `ft_reactive_L30` — each priced
  by the AIC converter, all reporting exactly 1,000,000 requests.
- **language**: `ft_llm_static` (TP2×2 on the C8-composed trace),
  `ft_llm_reactive` (SLA planner on the reactive-composed trace) — each a full
  1,000,000-request dynamo.replay with per-request records.

`build/build_coverage_manifest.py` reads every fleet's `verification.json` and
hard-asserts the guarantee → `data/coverage_manifest.json`.

Speedup: the mocker's virtual clock simulates 5.6 days in minutes at **exact**
validity (event-ordered discrete-event sim). Arrival timestamps are never
compressed — that would change the queueing physics (it is the knee-sweep
instrument, not a fast-forward).

## Build — A11 / A12 / A13 (need the source-build dynamo venv + patch)

```
# source-build dynamo carries the per-request planner-bridge patch (committed
# in ai-dynamo/dynamo @ 70c965db26). Rebuild if the tree changes:
#   cd ai-dynamo/dynamo/lib/bindings/python && maturin develop --uv --release --features aic-forward-pass

# A11 language race (39 planner replays; ~hours)
python3 defense/anim/build/gen_a11_runs.py            # + week cells; ledger-asserted at L60
eda/.venv/bin/python defense/anim/build/extract_a11.py
python3 defense/anim/build/build_a11.py

# A12 composed E2E (15 arms on the ledger-verified composed traces)
python3 defense/anim/build/gen_a12_e2e.py
eda/.venv/bin/python defense/anim/build/extract_a12.py   # request-linked join, alignment asserted
python3 defense/anim/build/build_a12.py

# A13 full-trace coverage (throttled: converters 2-way, 1M-req replays sequential)
python3 defense/anim/build/gen_a13_fulltrace.py
python3 defense/anim/build/build_coverage_manifest.py
```
