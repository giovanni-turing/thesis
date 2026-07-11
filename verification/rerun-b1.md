# Blocker B1 fix — static-optimal fleet on the image-bearing encoder p99

**Script:** `verification/scripts/rerun_b1.py` (run under
`/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python`)
**Raw output:** `verification/rerun_b1_results.json`
**Date:** 2026-07-10

## What B1 is and what this run does

The grid grades encoder-delay p99 over the **mixed** request population:
image-bearing delays plus a `0.0` for every text-only request
(`workload/trace_to_two_pool.py:481-495`, and the identical padding in the
grid's feasibility gate), then calls that the "worst percentile of vision-pool
users." The text-only zeros sit at the bottom of the sorted array, so the
99th-percentile index falls *shallower* into the image-bearing tail than a true
per-image-user p99 would. The mixed p99 therefore **understates** the tail the
SLA is meant to price.

This run reuses the grid's exact machinery — `simulate_vision_pool`,
`load_window`, `percentiles`, `build_series` from `trace_to_two_pool.py`, and the
`AICEncoder` f(N) costing from `silicon_multiworker.py` — and changes exactly one
thing: the feasibility p99 is taken over **only `NumImages>0` requests, no zero
padding** (image-bearing / stage-conditional). The feasibility gate keeps its
form: `image p99 < 1000 ms AND not queue_divergent`. The divergence test is
image-queue-based and is byte-identical under both metrics; only the p99 that
feeds the threshold changes.

The mixed branch reproduces `grid_summary.json` **exactly** for all seven windows
(e.g. burst1 C=6 → 995.9, burst5 C=16 → 588.4, steady C=2 → 733.6), which
validates the machinery.

## Per-window results (VERIFIED)

| Window | span_h | current C\* (mixed) | mixed p99 @C\* | **image p99 @ current C\*** | corrected C\* (image) | image p99 @ corrected C\* | ΔC\* |
|--------|-------:|----:|------:|------:|----:|------:|:--:|
| burst1 |  8.316 |  6 | 995.9 | **1118.0** (FAIL) |  **7** | 986.1 | +1 |
| burst2 |  1.899 |  8 | 855.8 | 946.8 (pass) |  **8** | 946.8 | 0 |
| burst3 |  0.450 |  7 | 904.7 | **1071.1** (FAIL) |  **8** | 852.9 | +1 |
| burst4 |  3.150 |  7 | 933.7 | **1037.0** (FAIL) |  **8** | 875.8 | +1 |
| burst5 |  1.349 | 16 | 588.4 | 588.4 (pass) | **16** | 588.4 | 0 |
| burst6 |  1.366 |  6 | 933.8 | **1148.3** (FAIL) |  **8** | 894.8 | **+2** |
| steady | 23.999 |  2 | 733.6 | 733.6 (pass) |  **2** | 733.6 | 0 |

The image p99 @ current-C\* column reproduces the audit's recompute
(`verification/adjudicated-issues.md`: burst1 995.9→1118, burst3 904.7→1071,
burst4 933.7→1037, burst6 933.8→1148) to the decimal.

**Confirmation of the expected pattern — with one correction:**
- burst1, burst3, burst4 rise by **+1 worker** (6→7, 7→8, 7→8). ✓
- burst2, burst5, steady are **unchanged** (8, 16, 2). ✓
- **burst6 rises by +2 (6→8), not +1.** At the intermediate rung C=7 the
  image-bearing p99 is **1049.1 ms**, still over the 1000 ms bound (divergence
  is False there — it is purely the p99 threshold), so burst6 needs C=8. The
  task's and fix-plan's "burst1/3/4/6 each move up one worker" is **imprecise
  for burst6**: it is a two-worker move. Every other +1 is exact.

**Why burst2/5/steady are unchanged:**
- burst5 is **divergence-bound, not p99-bound.** At C=13–15 the image p99 is
  already ≤ 716 ms (588.4 at C=15), well under the SLA, but the backlog is
  divergent; C=16 is the first non-divergent rung. Since divergence is metric-
  independent, C\*=16 holds under either p99. (This is exactly why the deployable
  static denominator is untouched — see B5.)
- burst2 already sits at C\*=8 whose image p99 (946.8) is under the bound; the
  rung below (C=7) fails under both metrics.
- steady is so calm that at C=2 the image and mixed p99 coincide (733.6): the
  tail is service-time-dominated with negligible queueing.

## Deployable static and the "service floor" (VERIFIED)

- **Deployable static = max C\* across windows = 16 (burst5), UNCHANGED.**
  Old max = 16 (burst5), new max = 16 (burst5). The C=16 denominator that the
  0.27–0.31× cost ratio divides by is therefore identical, so the **headline
  cost ratio survives** (it is a worker-seconds ratio; worker-seconds of the
  static fleet do not move).
- **The 588.4 ms zero-queueing service floor is genuinely image-bearing and
  UNCHANGED.** At high C (zero queue) every burst window's image-bearing p99
  floors at exactly **588.4 ms**, decomposing as
  `f(64) = 316.4 ms` (a full 64-image forward) `+ handoff(529 images) = 272.0 ms`
  — i.e. the p99 image request is a **529-image frames-class request**, which is
  image-bearing by construction. burst5 C=16 = 588.4 under both metrics. The
  floor value was never the error.
- steady's zero-queue image floor is lower (417.3 ms; its largest frames request
  is smaller).

**So the B1 defect is two things, not a wrong floor:** (a) the per-window static
**C\*** was under-graded on 4 windows (mixed p99 under-counted the image tail),
and (b) the **aggregate forecast's achieved p99** was quoted as 588 ("exactly
the floor") when the image-bearing aggregate p99 is **825.1 ms** — the forecast
fleet sits *above* the 588.4 floor, carrying mild residual queueing at the
image-bearing tail, still under the 1000 ms SLA at 0.27–0.31× cost.

## Corrected 5090 encoder GPU-hours (VERIFIED)

`5090 GPU-h = C* × span_h`. H100 GPU-h (the language pool, `llm_gpus × span_h`)
is **unchanged** — the LLM shape (TP2×2 on the bursts, TP1×2 on steady) is
untouched by an encoder-count change.

| Window | old C\* | old 5090 GPU-h | new C\* | **new 5090 GPU-h** | H100 GPU-h (unch.) |
|--------|----:|-----:|----:|-----:|-----:|
| burst1 |  6 | 49.9 |  7 | **58.2** | 33.3 |
| burst2 |  8 | 15.2 |  8 | 15.2 | 7.6 |
| burst3 |  7 | 3.2 |  8 | **3.6** | 1.8 |
| burst4 |  7 | 22.1 |  8 | **25.2** | 12.6 |
| burst5 | 16 | 21.6 | 16 | 21.6 | 5.4 |
| burst6 |  6 | 8.2 |  8 | **10.9** | 5.5 |
| steady |  2 | 48.0 |  2 | 48.0 | 48.0 |

(burst3's old table value 3.2 is a rounded 7×0.45=3.15; new 8×0.45=3.6 is exact.)

## Aggregate forecast floor (item 4 — confirmed elsewhere, stated here)

The whole-week (5.60-day) aggregate `fc_p90_L30` forecast schedule passes at
**825.1 ms image-bearing** (vs 588.4 ms mixed) — confirmed independently in
`verification/adjudicated-issues.md` and `verification/fix-plan.md`; not
recomputed here (it requires the whole-week two-pool replay, outside the
static-grid machinery). The corrected "service floor" the forecast fleet reaches
on the aggregate is therefore **825 ms**, replacing the mislabeled 588 ms — while
the per-request zero-queueing floor remains 588.4 ms and the cost ratio remains
0.27–0.31×.

---

# PROPOSED EXACT TEX EDITS

> **Scope legend:** [V] = verified by this run, ready to apply.
> [C] = number confirmed by the caller / audit (825.1), framing rewritten here.
> [F] = flagged: computed on the mixed metric elsewhere, **needs a separate
> recompute** (whole-week or reactive replay) before its number is changed — do
> **not** blind-swap.

## A. `tab:base-grid` in `baselines.tex` (lines 76–82) — [V]

Only the four changed windows need edits (C\* column and 5090 GPU-h column;
burst2/burst5/steady rows stay verbatim).

```
OLD: burst1 & 8.32 & 6 & TP2$\times$2 & 49.9 & 33.3 \\
NEW: burst1 & 8.32 & 7 & TP2$\times$2 & 58.2 & 33.3 \\
```
```
OLD: burst3 & 0.45 & 7 & TP2$\times$2 & 3.2 & 1.8 \\
NEW: burst3 & 0.45 & 8 & TP2$\times$2 & 3.6 & 1.8 \\
```
```
OLD: burst4 & 3.15 & 7 & TP2$\times$2 & 22.1 & 12.6 \\
NEW: burst4 & 3.15 & 8 & TP2$\times$2 & 25.2 & 12.6 \\
```
```
OLD: burst6 & 1.37 & 6 & TP2$\times$2 & 8.2 & 5.5 \\
NEW: burst6 & 1.37 & 8 & TP2$\times$2 & 10.9 & 5.5 \\
```

**Prose that stays valid** (no edit needed): the caption; "the encoder
requirement swings from 2 workers on the calm day to 16 on burst5"
(baselines.tex:102 — steady=2, burst5=16 both hold); "$C{=}16$ encoders …
overprovisions the calm day by $8\times$ on the vision side" (baselines.tex:107
— 16/2 = 8 holds).

**Consistency flags for the surrounding text:**
- If a sentence anywhere states each of burst1/3/4/6 "moves up one worker,"
  correct it: burst6 moves up **two** (6→8). [V]
- `tab:base-tp` (baselines.tex:126–130) reports TP2×2 TTFT p99 "at each window's
  static-optimal encoder count." Those p99s were computed at the *old* C\*; at
  the new (higher) C\* they shift slightly, but TP2×2 stays feasible on every
  window (grid `llm_curve` shows `C8_TP2_N2` passing burst1/3/4/6). The
  chapter's conclusion (TP2 beats TP1) is unaffected. Regenerate the five p99
  cells for exactness. [F, second-order]

## B. `tab:base-react-enc` in `baselines.tex` (lines 205–212) — [F, partial]

These are the **reactive controller's** per-window encoder-delay p99 by lead,
computed on the mixed metric. The `588` cells (where the controller reaches the
zero-queue state) are the genuine image-bearing floor and **stay 588** (verified:
every burst window's zero-queue image floor is 588.4). The non-588 cells that
carry queueing (638, 749, 905, and the bold failures 4{,}282 / 3{,}063 / 6{,}729
/ 4{,}606 / 9{,}481… and steady's 548/682/734/884) **would rise** under the
image-bearing metric and require a **reactive-replay recompute** — out of this
task's static-grid scope. Do not change them from this run.

## C. `twopool.tex` — SLA-wording / denominator fix (the core B1 label bug) — [V]

The SLA definition (twopool.tex:199–200) grades "encoder delay p99 $<$ 1 s"
without stating its denominator; combined with the "worst percentile user"
framing (twopool.tex:198) it reads as a per-vision-user guarantee while the grid
computed it over the mixed population. Make the denominator explicit. Suggested
minimal edit:

```
OLD: ... the vision pool must hold encoder delay p99
     $<\SI{1}{\second}$, matching the language TTFT budget.
NEW: ... the vision pool must hold encoder delay p99
     $<\SI{1}{\second}$ over image-bearing requests (the stage-conditional
     population; text-only requests incur no encoder delay), matching the
     language TTFT budget.
```

This is the wording that makes the whole recompute honest; every downstream
number in Ch.\ 7–8 should be understood as image-bearing after it.

## D. `closedloop.tex` — the aggregate "588 = service floor" language — [C]

The forecast fleet's **achieved aggregate p99** is 825.1 ms image-bearing, not
588 ms. But the 588.4 ms **zero-queueing floor** (f(64)+handoff) is still real
and image-bearing. The edits must keep the floor and correct the achieved p99.

**D1. Headline sentence (closedloop.tex:319–321).** The worker-second ratio is
unchanged; only the achieved p99 moves. Minimal exact swap of just the
parenthetical (the surrounding `\textbf{…}` and lead-in are untouched):
```
OLD: (2.12--2.38M
     versus 7.74M worker-seconds, at p99 \SI{588}{\milli\second} versus the
     static fleet's 565).
NEW: (2.12--2.38M
     versus 7.74M worker-seconds, at image-bearing p99 \SI{825}{\milli\second},
     above the \SI{588}{\milli\second} zero-queueing floor but well within the
     \SI{1000}{\milli\second} bound).
```
(The "static fleet's 565" is the aggregate static C=16 mixed p99; it also moves
under image-bearing but was **not** recomputed here — [F]. Either recompute it
or drop the comparison. The NEW above drops it rather than quote a stale number.)

**D2. sec:cl-matrix (closedloop.tex:74–79).** The per-window forecast p99 is no
longer "pinned exactly at the floor."
```
OLD: On the
     burst windows the p90 schedule's p99 encoder delay is pinned at
     \SI{588}{\milli\second}, exactly the platform's zero-queueing
     service floor: a full-batch forward ($f(64) =$
     \SI{316.4}{\milli\second}) plus the p99 handoff transfer
     (\SI{272}{\milli\second}). Anticipated capacity removes
     queueing entirely, and what remains is physics.
NEW: On the
     burst windows the p90 schedule's image-bearing p99 encoder delay sits at or
     just above the platform's zero-queueing service floor of
     \SI{588}{\milli\second} --- a full-batch forward ($f(64) =$
     \SI{316.4}{\milli\second}) plus the p99 handoff transfer of a frames-class
     request (\SI{272}{\milli\second}). Anticipated capacity removes nearly all
     queueing; what remains is physics plus a thin residual tail.
```

**D3. tab:cl-aggregate (closedloop.tex, caption L289–295 + rows L302–312).**
The forecast-p90 rows read 588 (mixed) → **825** (image-bearing). The other p99
cells (static 565; reactive 588/905; p50 3{,}047) are mixed and were **not**
recomputed here — [F]; recompute the whole table on the image-bearing metric in
one pass rather than swapping cells piecemeal. The caption's claim that "three
rows … coincide at the zero-queueing service floor" no longer holds image-bearing
(the runs carry different residual tails), so the caption needs rewording once the
full column is regenerated. Concretely, the two verified forecast rows become:
```
OLD: Forecast p90, $L{=}30$\,s & 588 & 2.38 & 0.31$\times$ & pass \\
NEW: Forecast p90, $L{=}30$\,s & 825 & 2.38 & 0.31$\times$ & pass \\
```
```
OLD: Forecast p90, $L{=}300$\,s & 588 & 2.12 & 0.27$\times$ & pass \\
NEW: Forecast p90, $L{=}300$\,s & 825 & 2.12 & 0.27$\times$ & pass \\
```
(cost/compliance columns unchanged — the ratio is worker-seconds, not p99.)

**D4. Handoff-floor caveat (closedloop.tex:395).** This uses 588 as the
*floor definition* (f(64)+handoff), which stays image-bearing. Keep 588 here; if
you want to reflect the achieved p99 too, add "(the aggregate forecast reaches
\SI{825}{\milli\second} image-bearing, above this floor)." [C, optional]

**D5. ρ-sweep numbers (closedloop.tex:337–347, 414).** The 588 (ρ=10) / 899 /
994 / 664 figures are mixed aggregate p99s at other capacity ratings — [F], need
the same whole-week image-bearing recompute; not changed here.

## E. Consistency beyond the three named files (flagged for the same pass)

Not in scope of "baselines/twopool/closedloop," but the same 588→825 achieved-p99
correction applies, for thesis-wide consistency:
- `intro.tex:256` — "(p99 \SI{588}{\milli\second}, the zero-queueing service
  floor)" → the forecast's achieved image-bearing p99 is 825; reword like D2.
- `conclusion.tex:57–58` — "leaving the service floor (\SI{588}{\milli\second}
  p99)" → same.
- `intro.tex:477`, `conclusion.tex:82` — "the \SI{588}{\milli\second} floor and
  the … result assume an embedding-only handoff" use 588 as the **floor
  definition**; those stay 588 (image-bearing floor), like D4.

## Summary of what is solid vs. what still needs a run

- **Solid, apply now [V]:** `tab:base-grid` four-row edit (C\* + 5090 GPU-h);
  the burst6 "+2 not +1" correction; the twopool denominator wording; the two
  verified forecast rows in `tab:cl-aggregate` (825).
- **Confirmed number, framing rewritten [C]:** the aggregate forecast achieved
  p99 = 825 ms and the closedloop/intro/conclusion "588 service floor" prose.
- **Needs a separate recompute before its cell changes [F]:** the aggregate
  static-C16 (565) and reactive/p50 rows of `tab:cl-aggregate`;
  `tab:base-react-enc`'s queued (non-588) cells; the ρ-sweep p99s; the
  `tab:base-tp` p99 cells at the new C\*. All are whole-week or reactive replays
  outside the static-grid machinery this run reused.
