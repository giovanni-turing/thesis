# G1 — burst2/6 forecast grading (closes a STATED STRUCTURAL hole) — AUDITED, ROUND 2

Closes: tex/closedloop.tex Limitations — burst2/6 "are graded only by the forecast-free baselines
of Chapter 5, never by a FORECAST policy — the forecast is structurally absent there."

## What survived independent re-verification (round-2 audit, recomputed not read off)
- COVERAGE: burst2 has exactly 459 15-s rows in-window, burst6 exactly 331; the full set of
  consecutive ts diffs is {15.0 s} — no gaps, no duplicates. All 12 parquets covers_window=true,
  contiguous_15s=true, duplicate_ts=0, first_forecast_ts 2024-10-15 12:03:00.
- NO FUTURE LEAKAGE: benchmark_expctx.py:66-68 slices data[v][max(0,o-ctx):o] — strictly past,
  right-exclusive; targets are o..o+11, at or after the origin; load_series applies NO global
  normalization (no back-door scaling leak); the FMs are zero-shot and never fitted on this trace.
- NO LEAKAGE IN THE CONSUMER: forecast_schedule_issuetime.py:129-131 gates on issue+L <= ts with a
  runtime assertion; verified in-window issue<=ts for every row, max staleness exactly
  165 s = (12-1)x15. The script hard-refuses any lead > 165 s ("Refusing to fabricate lead").
- PREFLIGHT IS A HARD GATE: sys.exit before any cell is dispatched (gen_g1_burst26.py:414-431).
- CONTEXT IS NOT DEGENERATE: first in-window origin is bin 2220 (burst2) / 2736 (burst6) =
  >9.2 h / >11.4 h of accrued history, so context has effectively reached the model cap.
- WINDOW PARAMS: windows_ext.json and simulation/windows.json are byte-identical for both windows.
  Zero 'error' and zero 'warn' keys across all cells.

## CORRECTION 1 — the reproduction is EXACT, not "within 0.018 ms"
My earlier delta column was a rounding artifact that UNDERSTATED the result. Raw float64:
  burst6 repro 735.3175669999328 == ledgered 735.3175669999328
  burst2 repro 766.2591829998419 == ledgered 766.2591829998419
Write "bit-identical reproduction of the ledgered p99". Drop the delta column.

## CORRECTION 2 — honest cell count is 40, not 42
{w}_lang_static_C8 and {w}_lang_runtime_gridC8 consume md5-IDENTICAL trace files, both with no
planner and fixed 2 replicas; outputs are bit-identical (burst6: 700.3391719995998 / 7.2542050).
Honest count: 40 distinct configurations, 28 independent language cells. (The duplicate is still
useful: it is a genuine replicate proving the mocker is deterministic.)

## CORRECTION 3 — "canonical 588.37 on both windows" is FALSE as written
It holds in 5 of 6 encoder forecast cells. burst2_enc_fc_toto_L30 = 654.739.
Also: on burst2 the encoder REACTIVE arm ALREADY achieves 588.37, so the encoder-side
anticipation benefit exists only on burst6 (748.677 -> 588.37).

## CORRECTION 4 — THE ARMS ARE NOT COST-MATCHED (must be stated)
Forecast language cells consume 15.61-26.96 GPU-h; static_C8 7.598 / 5.468; reactive 3.259-6.159.
The forecast arm passes the SLA while spending 3-6x the reactive arm's GPU-hours, driven by
FORECAST_REQ_SCALE=8.0. "Forecast passes, reactive fails" is arithmetically true but is NOT an
efficiency claim. Any sentence must either quote the cost or scope itself to SLA attainment only.

## CORRECTION 5 — "L" means two different things across the pools
Encoder L=30 s is an ISSUED FORECAST LEAD (bounded by the 165 s archive limit).
Language L=60/120/300 is STARTUP_TIME, a modelled replica startup delay — NOT forecast lead.
No language cell demonstrates 300 s of anticipation; the archive cannot supply it.

## CORRECTION 6 — the language arm does NOT anticipate (the semantic gap that matters most)
replay_with_forecast.py:14-27,113-121: it samples the single archived bin at index 4*ticks with
the series starting at T0-1min, so the sampled bin runs ~60 s BEHIND sim time. Its own docstring
calls it "a same-input conversion signal, not anticipation ... not a timing or anticipation
instrument". tex/closedloop.tex already carries this caveat; my card omitted it.
=> The 17/18 language result is a CONVERSION comparison (tail-aware p90 conversion vs the ARIMA
ladder's mean-based conversion) on a held, same-input signal. It is NOT evidence that lead time
closes the hole. This is also WHY the language side cannot leak.

## Results (unchanged numbers, corrected framing)
Encoder (SLA 1000 ms): burst2 fc-chronos/timesfm 588.37, fc-toto 654.74, reactive 588.37,
static C8 855.83, static C2 6321.35 DIVERGENT. burst6 fc all three 588.37, reactive 748.68,
static C8 720.11, static C2 5333.17.
Language: forecast 17/18 PASS (exception burst2 fc_toto_L300 = 1055.9 FAIL); reactive 0/6,
violating BOTH bounds (TTFT 1627-1818, ITL 136-143).
Runtime offset (measured, deterministic — the duplicate-cell replicate proves the mocker is
bit-deterministic, so this is not sampling noise): source build is 4.76% faster on burst6
(-35.018 ms) and 2.66% on burst2 (-20.359 ms) than the Chapter-5 wheel. n=1 build-pair per
window: a measured offset for THIS pair, not a distribution.

## What may be written
"With expanding-context forecasts the two out-of-span episodes are no longer structurally
un-gradable, and the encoder schedule is genuinely anticipatory there (issue-time gated, max
staleness 165 s). Graded end to end, the forecast policy meets the SLA in 17 of 18 language cells
against the reactive baseline's 0 of 6, which violate both bounds — but at 3-6x the reactive
arm's GPU-hours, and on the language side this compares two CONVERSIONS of the same held signal
rather than demonstrating anticipation. The reproduction anchors reproduce the ledgered p99
bit-identically, and quantify a 2.7-4.8% runtime offset between this build and the Chapter-5
wheel that must be applied before cross-chapter comparison."
