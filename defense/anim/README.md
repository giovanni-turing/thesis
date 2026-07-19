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
| `a2_the_race.html` | A2 "The race" — forecast (Chronos p90, issue-time) vs reactive (trailing observed rate), identical law/ρ/hysteresis. **Episode selector** across the onset gradient (burst3 1-min · burst5 35-min · burst4 60-min · burst1 220-min · calm day) × **cold-start-lead slider** (15/30/45/165 s; keys 1–4) = 40 ledger-verified converter runs. Per lane: worker staircase + busy, per-bin worst-delay dots (log, SLA line), and **live tickers**: cost so far (worker-h), mean delay (image-bearing), running p99 (all requests — converges to the ledgered verdict), queue now/peak. On burst3 reactive climbs 9.5→54 s while forecast pins at 588 ms with peak queue 0; on slower onsets both pass (reactive even costs more on the calm day); at L165 reactive newly fails burst4/5. | "Forecast holds the SLA where reactive breaks" |

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
