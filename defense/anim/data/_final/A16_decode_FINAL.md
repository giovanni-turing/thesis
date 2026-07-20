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
Selecting the busiest 1% of bins on the TRUE (unobservable) series gives -0.8% to -1.3%
(mildly anti-conservative). Selecting on the OBSERVABLE arrival-stamped series gives
**+54.5% to +55.6%** (strongly conservative). Reproduces on all three arms within 1.2 pp.
This is the result: the stamp is strongly conservative with respect to what a controller can
actually see, while its shortfalls concentrate in bins no controller can identify ex ante.

## "Upper bound" is NOT supportable as a pointwise claim
At 15 s the stamp understates a majority of bins on the truth-selected population; within the
truth-selected busiest 1%, frac_bins_short = 56.7%, shortfall p90 = 249.6 tok/s, max = 909.8
tok/s (71.5% of that bin's own true rate); max_frac_bins_under_provisioned = 12.19% at
200 tok/s/replica. A mass-weighted MEAN of -1.3% cannot license a no-risk tail conclusion.

## Onsets: use the MASS-WEIGHTED figure
onset ratio mass-weighted = **2.796** (the load-bearing number).
unweighted median = 3.406 — shipped only as ratio_p50_unweighted_diagnostic. Onsets are 403 of
40,316 bins; onset+decay together carry 5.65% of stamped mass, so neither characterises the
series. Decay bins are the genuinely anti-conservative region: mass-weighted decay ratio 0.506
(the stamp carries HALF the true decode mass there).

## Total volume: quote the right number
Trace fidelity on the ft_llm arms = **7.82e-07** (a real trace-vs-replay figure, since their
joins are usable). Do NOT quote the mass_conservation_rel_err ~1e-14: on timesfm_e2e that is a
construction identity engineered by the horizon padding, not evidence.

## The controller does NOT consume a 15-s series
planner_forecast_smoke.json:11 sets throughput_adjustment_interval_seconds = 60, and
replay_with_forecast.py:106-119 takes a STRIDE-4 POINT SAMPLE, so 3 of every 4 15-s bins are
never read. Per-phase bias over the actually-sampled bins: +2.17 / -1.59 / -3.56 / -1.53 %;
control-interval estimator vs true 60-s mass: +1.27 / +4.67 / +0.04 / -9.43 %. Spans zero on
every arm, and the phase is not controllable — so NO single-signed provisioning claim survives
this population.

## Fixes applied (all 9) and now verifiable
D1 both conventions emitted side by side · D2 full tier curve (top 10/1/0.1/0.01%) · D3 trace
fidelity separated from the construction identity · D4 key renamed vs_primary_arrival with a
duplicate flag · D5 mass-weighted onset ratio load-bearing · D6 frac_bins_short + shortfall
p90/max + under-provisioned share reported · D7 1-s and 30-s series SHIPPED (gzipped) so the
previously JSON-only figures recompute · D8 controller-sampled population added · D9 one sign
convention throughout (+ = stamp exceeds truth = CONSERVATIVE).

## Proposed thesis wording (tex/intro.tex:504 and :148)
REPLACE "an offered-work upper bound" with:
"the decode series is exact in total volume to within 8e-7 of the replay, and strongly
conservative on the bins an operator can actually identify (+54% on the busiest 1% selected by
the arrival stamp itself); it is not a pointwise upper bound, and its shortfalls concentrate in
bins identifiable only in hindsight."

## Residual risks (carry these)
- The onset ratio is a SELECTION statistic: defining onsets on the TRUE series collapses the
  median ratio from 3.41x to 1.02x. Never present it as a property of the stamp alone.
- Truth-selected anti-conservatism figures are FLOORS: the uniform 1/itl spreading smooths
  D_true, and de-smoothing moves the hot-bin bias from -1.30% to +4.8%. Fixing this needs
  per-token timestamps the mocker does not emit.
- The decode series enters the planner only as osl = gen/req (replay_with_forecast.py:138),
  never as a decode rate. No bin-level decode-rate bias has been shown to propagate to a replica
  decision, because the co-stamped req denominator may partially cancel it. Any provisioning-risk
  sentence built on A16 is ONE INFERENTIAL STEP SHORT.
