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

## CORRECTION 1 — the reproduction is EXACT, but ONLY for p99 TTFT
My earlier delta column was a rounding artifact that UNDERSTATED the result. Raw float64:
  burst6 repro 735.3175669999328 == ledgered 735.3175669999328
  burst2 repro 766.2591829998419 == ledgered 766.2591829998419
Write "bit-identical reproduction of the ledgered p99 **TTFT**". Drop the delta column.
**SCOPE CORRECTION (peer review):** "bit-identical p99" without "TTFT" over-scopes. Only p99 TTFT
reproduces; p99 ITL does not (repro 9.3 / 7.3 ms against the runtime cell's 7.6 / 7.3 ms). The
ledger carries an expected TTFT only, so no ITL reproduction claim is licensed at all.
**PROVENANCE:** the burst6 anchor is the **C8** grid cell (735.318 ms), NOT the C6 cell (733.777)
tabulated at baselines.tex:109. State C8 explicitly or a reader will collide the two.

## CORRECTION 2 (ITSELF WRONG — WITHDRAWN) — the count is 42, not 40
My "40 distinct configurations" correction was **wrong and is withdrawn**. {w}_lang_static_C8 and
{w}_lang_runtime_gridC8 are NOT duplicates: they differ in **STARTUP_TIME** (60 s vs unset —
gen_g1_burst26.py:319-325; verification.json lead_s 60 vs null), and on burst2 their outputs
differ (TTFT p99 745.3585 vs 745.9045; the two reports differ on 34 keys). They coincide on burst6
only because that window's schedule happens not to exercise the startup delay.
**Honest count: 42 distinct configurations — 30 language cells + 12 encoder cells** (re-counted
from g1_runs/: 30 *_lang_*.report.json, 12 *_enc_*.stats.json).
The claim that this pair "is a genuine replicate proving the mocker is deterministic" is
**STRUCK** — the burst2 pair disproves it. Nothing in this delivery establishes bit-determinism,
and the 2.7-4.8% runtime offset below must therefore be described as a measured offset for one
build pair, not as noise-free.

## CORRECTION 3 — "canonical 588.37 on both windows" is FALSE as written
It holds in 5 of 6 encoder forecast cells. burst2_enc_fc_toto_L30 = 654.739.
Also: on burst2 the encoder REACTIVE arm ALREADY achieves 588.37, so the encoder-side
anticipation benefit exists only on burst6 (748.677 -> 588.37).

## CORRECTION 4 — THE ARMS ARE NOT COST-MATCHED (must be stated)
Forecast language cells consume 15.61-26.96 GPU-h; static_C8 7.598 / 5.468; reactive 3.259-6.159.
The forecast arm passes the SLA while spending 3-6x the reactive arm's GPU-hours, driven by
FORECAST_REQ_SCALE=8.0 (gen_g1_burst26.py:334). The gap to reactive is therefore a **capacity**
gap, not a policy gap: reactive averages 1.19-1.62 replicas against forecast's 4.36-7.10.
"Forecast passes, reactive fails" is arithmetically true but is NOT an efficiency claim. Any
sentence must either quote the cost or scope itself to SLA attainment only.

## CORRECTION 4b (NEW, AND THE ONE THAT MATTERS) — THE STATIC FLEET PASSES, AND IS FAR CHEAPER
This card omitted its own decisive comparator. The forecast-free **static two-replica fleet
(static_C8, no planner)** passes BOTH bounds on BOTH windows:
| window | TTFT p99 | ITL p99 | GPU-h | verdict |
|---|---:|---:|---:|:--|
| burst2 | 745.4 ms | 7.6 ms | 7.598 | PASS |
| burst6 | 700.3 ms | 7.3 ms | 5.468 | PASS |
Window-matched, **every** forecast cell is 2.2x-3.6x dearer (burst2 16.568-26.961 GPU-h against
7.598; burst6 15.610-18.438 against 5.468). Re-derived from g1_runs/*.report.json.
=> **Any sentence pairing the 17/18 with the 0/6 that does not name the static baseline's pass is
misleading and inverts the conclusion.** The result here is GRADABILITY, not superiority: these
episodes can now be graded by a forecast policy; on cost the forecast policy loses to a
forecast-free fleet on both of them.
(Note the ruling's cross-window "2.9x-4.9x" range compares a burst2 forecast cell against a
burst6 static cell; the window-matched range re-derived above is 2.2x-3.6x and is what should be
quoted.)

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
Runtime offset (measured; the bit-determinism justification is WITHDRAWN — see Correction 2):
the source build is 4.76% faster on burst6 and 2.66% on burst2 than the Chapter-5 wheel.
**Do NOT quote "-35.018 ms" / "-20.359 ms"** — those are the driver's rounded-input subtractions
(gen_g1_burst26.py:381-384). The exact deltas re-derived from raw float64 are
**-34.978 ms (-4.757%)** on burst6 (735.317567 -> 700.339172) and **-20.355 ms (-2.656%)** on
burst2 (766.259183 -> 745.904514). n=1 build-pair per window: a measured offset for THIS pair,
with uncharacterised uncertainty — not a distribution and not a demonstrated noise floor.

## What may be written
"The limitation that burst2 and burst6 are structurally un-gradable by a forecast policy is
removed once the forecast archive is expanding-context: both episodes sit inside the forecastable
span, and the encoder schedule is genuinely anticipatory there (issue-time gated, max staleness
165 s). A reproduction anchor recovers the ledgered Chapter-5 p99 TTFT bit-identically on the C8
grid cell of each window (766.259 ms and 735.318 ms), while the source build used here runs
2.7-4.8% faster than the ledgered wheel on the identical trace. Graded end to end against TTFT p99
<= 1000 ms and ITL p99 <= 100 ms, the forecast policy meets both bounds in 17 of 18 language cells
and the ARIMA reactive ladder in none of 6. A forecast-free static two-replica fleet, however,
also passes both bounds on both windows at 7.598 and 5.468 GPU-h — 2.2x to 3.6x cheaper than every
forecast cell on the same window. These episodes are therefore now GRADABLE by a forecast policy;
they are not evidence that forecasting is the economical policy on them."

## DO NOT WRITE (from this card)
- "40 distinct configurations" — it is 42.
- "the mocker is bit-deterministic" / any determinism claim.
- "reproduces the ledgered p99 bit-identically" without "TTFT".
- "-35.018 ms" / "-20.359 ms" (rounded-input artifacts).
- Any pairing of 17/18 with 0/6 that does not name the static baseline's pass.
