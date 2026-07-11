# P2-1 / M1 ablation: reactive + tail-aware headroom (trailing-window p90 + ρ=15)

**Gap closed.** The closed-loop encoder matrix pits a *forecast* controller
(p90 forecast band + ρ=15 conversion + cold-start lead L) against a *reactive*
baseline (trailing-observed **point** rate + ρ=15 + L). The reactive branch of
`simulation/forecast_schedule.py` **ignores `--quantile`** and reads only the
last complete bin's observed image rate, so the head-to-head bundles two dials:
**anticipation** (forecast sees the next bin) and **headroom** (the p90 band vs a
point). The missing cell — a purely reactive controller given the *same*
tail-aware headroom, sourced from **past** observation instead of a forecast —
was never run. This is the "one consensus experiment" (codex M1 + glm R2 + opus
M1). It is run here and isolates the two dials.

## Method

- **Controller** (`verification/scripts/reactive_quantile_schedule.py`): at bin
  *m* the controller knows complete bins `0..m-1` (reactive information set); its
  demand estimate is `q(m) = percentile_p90( observed_rate[m-W .. m-1] )`, the
  p90 of the trailing window of `W = react_window_s / bin_s` observed per-bin
  image rates. Everything downstream — `C = clamp(ceil(q/ρ))`, hysteresis
  (rolling max over 3 min), cold-start lead (min desired over trailing L), step
  collapse — is the **`_emit()` imported verbatim** from `forecast_schedule.py`.
  The **only** change vs the thesis reactive baseline is point → trailing-window
  p90; the **only** change vs the forecast policy is forecast-band → trailing
  observation. Validation: `--mode react_point` reproduces the existing
  `ct_matrix/reactive_burst3_obs_rho15.sched.json` **byte-for-byte**.
- **Config**: ρ=15 (tail-aware rating), hysteresis 3 min, encoder pool of 2 base
  workers scaling to ≤32, 25 Gbps handoff (matches `ct_matrix` + `aggregate44`
  references), image resolution 448². Leads L ∈ {30, 300}s. Trailing window W ∈
  {120, 240, 480}s swept so the conclusion is not an artifact of one window.
- **References**: forecast-p90 (a) and reactive-point (b) regenerated at
  L∈{30,300} for the bursts; aggregate references reused from
  `simulation/results/aggregate44/` (rho15, 25 Gbps). SLA: encoder-delay p99 <
  **1000 ms**.
- **Runners**: `verification/scripts/run_ablation.sh` (bursts),
  `run_ablation_aggregate.sh` (week). Outputs in
  `simulation/results/rerun_verify/`.

## Results — encoder-delay p99 (ms), PASS = p99 < 1000

### burst3 (1-min onset — the hardest cell)

| controller (L=30) | p99 | SLA | | controller (L=300) | p99 | SLA |
|---|--:|:--|---|---|--:|:--|
| **forecast p90** (ref a) | **588.4** | PASS | | **forecast p90** | **588.4** | PASS |
| reactive point (ref b) | 16 078.7 | FAIL | | reactive point | 54 169.5 | FAIL |
| reactive p90, W=120s | 4 291.7 | FAIL | | reactive p90, W=120s | 11 568.0 | FAIL |
| reactive p90, W=240s | 2 555.8 | FAIL | | reactive p90, W=240s | 11 568.0 | FAIL |
| reactive p90, W=480s | 1 973.3 | FAIL | | reactive p90, W=480s | 11 568.0 | FAIL |

Trailing-p90 headroom cuts the reactive p99 monotonically (16 079 → 1 973 ms at
L=30 as W grows) but **never crosses the SLA at any window or lead**. Only the
forecast passes.

### burst1 (220-min slow onset)

| controller | L=30 p99 | L=300 p99 | SLA |
|---|--:|--:|:--|
| forecast p90 (ref a) | 598.7 | 612.5 | PASS |
| reactive point (ref b) | 742.8 | 904.7 | PASS |
| reactive p90 (W=120/240/480) | 712 / 655 / 638 | 905 / 825 / 742 | PASS |

Every configuration passes; headroom is not even needed. burst1 is not a timing
test (consistent with P2-2).

### aggregate week (749,601 reqs)

All controllers PASS (p99 ≈ 588–905 ms). The week is smooth enough that the p99
is the intrinsic encoder service+handoff tail (~588 ms), not queueing; the
reactive-point L=300 case is the only one that ticks up (904.7) and the p90
headroom brings it back to 700–785 ms. Not diagnostic — the aggregate is not
where reactive fails (matches the thesis).

## Mechanism (burst3 capacity at the onset)

Observed rate is 0 img/s at t=645s, then 131 → 521 → 544 img/s across
t=660–690s. Workers standing at each instant:

| L=30, workers at | t=645 | t=660 | t=690 | t=720 |
|---|--:|--:|--:|--:|
| forecast p90 | **19** | **19** | **19** | 19 |
| reactive point | 3 | 1 | 1 | 32 (60 s too late) |
| reactive p90 W=240 | 7 | 5 | 4 | 6 |
| reactive p90 W=480 | 12 | 12 | 11 | 11 |

The forecast has ~19 workers **in place before** the spike (anticipation).
Trailing-p90 headroom raises the reactive standing capacity from 1–3 to 5–12
workers (why its p99 falls 8×) but it is calibrated to **past** (near-zero) load
and cannot reach the ~36 workers the spike demands — it never saw it coming. At
L=300 the forecast stays at 17 workers through the onset while every reactive
variant is stuck at 1–12 for the whole spike (forecast p99 flat at 588 across
both leads — the lead-invariance signature of anticipation; reactive degrades
from ~2k to ~12k–54k ms).

## Interpretation / attribution

On the encoder pool the tail-aware headroom (p90 band + ρ=15) is **necessary but
not sufficient** on a fast onset: it materially improves the reactive controller
(up to 8× lower p99) yet **cannot repair burst3 at any lead** — the fast-onset
SLA is crossed **only** by anticipation. On slow onsets (burst1) and at the week
aggregate, headroom is moot because the reactive controller already passes. So
the p90-forecast win on fast onsets is attributable to **anticipation, not
headroom+conversion** — the two dials the raw head-to-head bundled are now
separated, and the separation holds across three trailing-window sizes and both
leads. This sharpens rather than overturns the "information, not plumbing"
reading: the conversion/headroom is the *shared, helps-everywhere* dial; on the
hardest onset, anticipation is the *decisive* one.

## Proposed addition for `tex/closedloop.tex` (encoder matrix, near the
## reactive-strawman caveat at lines 34–38)

> To separate anticipation from headroom directly, we also run the reactive
> controller with the tail-aware headroom it was denied — the trailing-window
> p90 of the observed image rate (windows of 2--8\,min) at the same
> $\rho{=}15$ and lead. On the slow onset (burst1) and at week scale this
> reactive-with-headroom controller passes, as the point reactive already does;
> but on the 1-minute onset (burst3) it fails at every lead and window
> (p99 $1{,}973$--$11{,}568$\,\si{\milli\second} vs the forecast's
> $588$\,\si{\milli\second}), even though the added headroom cuts its p99 up to
> $8\times$ below the point reactive. Tail-aware headroom is thus necessary but
> not sufficient on a fast onset: it is calibrated to past load and cannot stand
> up the replicas a sub-minute spike demands, which only anticipation places
> ahead of the onset. The p90-forecast's fast-onset win is therefore
> anticipation, not headroom alone.

---
*Artifacts:* schedules + stats in `simulation/results/rerun_verify/`
(`react_p90_W{120,240,480}_{burst3,burst1,aggregate}_L{30,300}.*`, plus
regenerated `fc_p90_*` / `react_point_*` burst references). Scripts:
`verification/scripts/reactive_quantile_schedule.py`,
`run_ablation.sh`, `run_ablation_aggregate.sh`. Aggregate references reused from
`simulation/results/aggregate44/`. No `.tex` or existing code/artifacts modified.
