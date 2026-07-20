# A16 decode — FINAL (all 9 audit defects fixed, re-run 23:15, both conventions shipped)

Target: tex/intro.tex:504 and :148 — "arrival-side stamping makes the decode series an
offered-work UPPER BOUND."

## SOURCE THE CLAIM FROM THE ft_llm ARMS, NOT timesfm_e2e
| arm | n | trace join | trace fidelity | truth-sel top1% | arrival-sel top1% |
|---|---:|---|---:|---:|---:|
| ft_llm_static | 1,000,000 | USABLE (0.889) | 7.82e-07 | -0.836% | **+54.48%** |
| ft_llm_reactive | 1,000,000 | USABLE (0.887) | 7.82e-07 | -1.199% | **+55.60%** |
| timesfm_e2e | 999,599 | NOT usable (0.0074) | 1.67e-05 | -1.297% | +54.38% |
The two ft_llm arms carry the full 1 M trace, a genuine trace join, and 21x better trace
fidelity. timesfm_e2e falls back to the composed arrival (its vs_primary == vs_composed,
flagged primary_is_composed_duplicate=true), so it cannot support any "against the trace"
sentence. Use ft_llm_static as the loose-bound arm and ft_llm_reactive as the violation arm.

## THE FINDING: the headline FLIPS SIGN by selection convention, and the flip is ARM-INVARIANT
**AT A 15-SECOND BIN WIDTH.** Selecting the busiest 1% of bins on the TRUE (unobservable) series
gives -0.84% (static) / -1.20% (reactive). Selecting on the OBSERVABLE arrival-stamped series
gives **+54.48% / +55.60%** — a 1.1 pp spread across the two ft_llm arms.
This is the result: the stamp exceeds the realised rate with respect to what a controller can see
at 15 s, while its shortfalls concentrate in bins no controller can identify ex ante.

**BIN WIDTH IS LOAD-BEARING AND MUST TRAVEL WITH THE NUMBER** (ft_llm_static / ft_llm_reactive,
arrival-selected top-1% signed bias):
| bin width | bias | note |
|---|---:|---|
| 1 s | +328.6% / +354.7% | far below any control cadence |
| 15 s | **+54.5% / +55.6%** | the shipped artifact labels this "NOT the controller's cadence" |
| 30 s | +14.4% / +14.8% | — |
| 60 s | **+2.9% / +3.2%** | **the planner's actual interval** |
(Truth-selected over the same ladder: -6.8% / -13.2% at 1 s, -0.8% / -1.2% at 15 s,
-0.8% / -1.5% at 30 s, -0.8% / -0.8% at 60 s — negative at every width, on both arms.)
The +54% may never appear without "at 15-second bins". At the interval the operator actually
decides on, the figure is under three percent.

## "Upper bound" is NOT supportable as a pointwise claim  [RE-SOURCED to the ft_llm arms]
At 15 s, within the truth-selected busiest 1%: frac_bins_short = **55.4%** (static) / **57.9%**
(reactive); shortfall p90 = **230.8 / 269.9** tok/s; shortfall max = **934.7 / 927.3** tok/s
(**72.0% / 60.2%** of that bin's own true rate); max_frac_bins_under_provisioned = **11.4% /
12.3%** at 200 tok/s/replica. A mass-weighted MEAN of -0.8% to -1.2% cannot license a no-risk tail
conclusion.
*(The previously printed 56.7% / 249.6 / 909.8 / 71.5% / 12.19% were `timesfm_e2e` values — the
arm caveat (a) disqualifies. Superseded by the figures above.)*

## Onsets: MASS-WEIGHTED, and NEVER as a property of the stamp  [RE-SOURCED to the ft_llm arms]
At 15 s: onset ratio mass-weighted = **2.759** (static) / **2.839** (reactive); unweighted median
= **3.377 / 3.454**, shipped only as ratio_p50_unweighted_diagnostic. Onsets are **403 of 40,324**
15-s bins; onset+decay together carry 5.65% of stamped mass, so neither characterises the series.
Decay bins are the genuinely anti-conservative region: mass-weighted decay ratio **0.509 / 0.522**
(the stamp carries about HALF the true decode mass there).
**These are SELECTION statistics, not properties of the stamp**, and the caveat must be
STRENGTHENED rather than softened: at a 60 s bin width the mass-weighted onset ratio collapses to
**1.12 / 1.14** and the median to **1.03 / 1.04**, exactly as the truth-selection collapse does.
No onset ratio may be presented as a property of the stamp, and none is load-bearing.
*(2.796 / 3.406 / 0.506 / "40,316 bins" were `timesfm_e2e` values. Superseded.)*

## Total volume: quote the right number
Trace fidelity on the ft_llm arms = **7.82e-07** (a real trace-vs-replay figure, since their
joins are usable). Do NOT quote the mass_conservation_rel_err ~1e-14: on timesfm_e2e that is a
construction identity engineered by the horizon padding, not evidence.

## The controller does NOT consume a 15-s series
planner_forecast_smoke.json:11 sets throughput_adjustment_interval_seconds = 60, and
replay_with_forecast.py:106-119 takes a STRIDE-4 POINT SAMPLE, so 3 of every 4 15-s bins are
never read. **Re-sourced to ft_llm_static** (n=10,081 per phase):
  per-phase bias over the actually-sampled bins: **+1.29 / -1.58 / -2.62 / -1.42 %**
  control-interval estimator vs true 60-s mass: **+0.86 / +3.77 / +0.13 / -8.02 %**
Spans zero on both ft_llm arms, and the phase is not controllable — so NO single-signed
provisioning claim survives this population.
*(The previously printed +2.17/-1.59/-3.56/-1.53 and +1.27/+4.67/+0.04/-9.43 were `timesfm_e2e`
values. Superseded.)*

## Fixes applied (all 9) and now verifiable
D1 both conventions emitted side by side · D2 full tier curve (top 10/1/0.1/0.01%) · D3 trace
fidelity separated from the construction identity · D4 key renamed vs_primary_arrival with a
duplicate flag · D5 mass-weighted onset ratio load-bearing · D6 frac_bins_short + shortfall
p90/max + under-provisioned share reported · D7 1-s and 30-s series SHIPPED (gzipped) so the
previously JSON-only figures recompute · D8 controller-sampled population added · D9 one sign
convention throughout (+ = stamp exceeds truth = CONSERVATIVE).

## Proposed thesis wording (tex/intro.tex:504 and :148)
REPLACE "an offered-work upper bound" with:
"The rate signals stamp each request's full token volume at its arrival minute. For encoder and
prefill work this is faithful; for decode it is NOT a pointwise upper bound. The stamped decode
series is exact in total volume (7.8e-7 of the replay over 1,000,000 requests) but displaces mass
in time: on the busiest one percent of FIFTEEN-SECOND bins selected by the stamp itself it exceeds
the realised decode rate by 54 percent, while on the busiest one percent selected by the realised
series it falls short. Both figures shrink with bin width — at the planner's sixty-second interval
the conservative figure is under three percent — and the sign of the bias over the population the
controller actually samples spans zero, so the series licenses NO provisioning claim of either
direction."
The earlier wording ("**strongly conservative** on the bins an operator can actually identify") is
**deleted**: the operator decides at 60 s, where the figure is +2.9% and **42.6% of the
flagged-hottest bins are still under-stated**. The card's own controller section undercut it.

## Residual risks (carry these)
- The onset ratio is a SELECTION statistic, and so is the +54%. Defining onsets on the TRUE series
  collapses the ft_llm median ratio to ~1.0x, and the mass-weighted ratio collapses the same way
  (2.76x -> 1.12x from 15 s to 60 s). Never present any onset ratio as a property of the stamp.
- **The +54% is a selection error, not headroom.** The arrival-selected "busiest 1%" at 15 s have a
  true mean rate of 1084.7 tok/s against the genuinely busiest 1%'s 1435.1 — **24% lower**. They
  are largely not the hot bins. And **18.8% of them are still short** at 15 s, rising to **42.6%
  at 60 s**.
- **STRUCK — the "+4.8% de-smoothing" residual risk.** It had NO artifact behind it and pointed the
  wrong way. No de-smoothing code path exists anywhere in the generator, and the generator's own
  docstring (gen_a16_decode_spread.py:56-58) states the opposite direction: the uniform 1/itl
  spreading "flattens D_true's peaks, which INFLATES any peak-overstatement figure — i.e. this
  assumption biases the analysis TOWARD the 'the arrival stamp is conservative' conclusion."
  **The correct residual risk is therefore the reverse: the +54% is itself inflated by the
  spreading model.** Nothing may be reinstated here until an artifact exists.
- The decode series enters the planner only as osl = gen/req (replay_with_forecast.py:138),
  never as a decode rate. No bin-level decode-rate bias has been shown to propagate to a replica
  decision, because the co-stamped req denominator may partially cancel it. Any provisioning-risk
  sentence built on A16 is ONE INFERENTIAL STEP SHORT.

## DO NOT WRITE (from this card)
- "strongly conservative" (in any form).
- The +54% without its **15-second bin width**.
- Any onset ratio (2.76, 2.84, 3.38, 3.45 — and certainly not the withdrawn 2.796 / 3.406)
  presented as a property of the stamp.
- Any safety-margin, headroom, or provisioning-risk reading of this track.
- Any number in this card sourced from `timesfm_e2e`.

## PROVENANCE STATUS
`ingest_log` matching %a16_decode% = 0 rows. Admissible as a **correction that weakens an existing
claim** (which needs no new provenance); NOT admissible as a new positive result until ingested.
