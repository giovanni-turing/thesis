# A16 decode — REQUIRES DRIVER FIX + RE-RUN. Do not quote as shipped.

Arithmetic is clean (every shipped number recomputes from the CSVs to the last digit). Every
defect below is in DEFINITION, POPULATION or LABELLING — which is worse, because the numbers
look authoritative.

## D1 — the headline statistic FLIPS SIGN depending on an unobservable choice
Hot bins are selected on TRUTH (gen_a16_decode_spread.py:303 `hot = spread >= pct(spread,99)`),
which no controller can observe. Re-selecting the SAME statistic on the OBSERVABLE
arrival-stamped series:
  truth-selected  top 1%  = -1.30%  (anti-conservative)
  arrival-selected top 1% = +54.38% (strongly CONSERVATIVE)
  arrival-selected top 10% = +19.77%
The two definitions differ by 56 percentage points AND in sign. The shipped -1.30% is a
truth-conditioned regression-to-the-mean artifact, not a statement about what a controller
provisions against.

## D2 — the quoted tier is a CHERRY-PICKED local minimum
top 10% = -3.43%, top 1% = -1.30%, top 0.1% = -1.27%, top 0.01% = -1.57%.
Non-monotone in busyness; the busiest 10% are 2.6x more anti-conservative than the quoted tier.

## D3 — "exact in total volume (1.2e-14)" is NEAR-VACUOUS
1.2e-14 only says the spreading kernel conserves what it was handed — a construction property
engineered by the horizon padding at gen_a16_decode_spread.py:602-603. The mass error that
matters, replay vs trace, is .totals.output_vs_trace_rel_err = 1.67e-05 (186,529,883 replayed
vs 186,532,990 trace tokens) — NINE ORDERS OF MAGNITUDE larger. Quote 1.67e-05, never 1.2e-14.

## D4 — MISLABELLED: no trace comparison was actually made
.trace_join.usable = False (.gen_positional_match_frac = 0.0074), so the driver falls back to
the composed arrival (line 612-614). Every `vs_trace_arrival.*` value is byte-identical to
`vs_composed_arrival.*`, and the CSV columns arr_trace_tokens / arr_composed_tokens are
bit-identical. ANY sentence saying "against the trace's own arrival stamps" would be FALSE.

## D5 — the 3.41x onset figure violates the driver's OWN stated doctrine
It is an UNWEIGHTED median of per-bin ratios, while the same driver's summary instructs "use the
mass-weighted bias" for direction-of-bias claims. Mass-weighted onset ratio = 2.796, not 3.406
— the quoted number overstates onset conservatism by 22%. Onsets are 403 of 40,316 bins;
onset+decay together are 2.0% of bins carrying 5.65% of stamped mass, so neither characterizes
the series.

## D6 — "not a provisioning risk" is contradicted by the same artifact
Within the truth-selected busiest 1% at 15 s: frac_bins_short = 56.7% (a MAJORITY of the busiest
bins are short), shortfall p90 = 249.6 tok/s, max 909.8 tok/s = 71.5% of that bin's own true
rate. And .verdict.res_15s.max_frac_bins_under_provisioned = 12.19% at 200 tok/s/replica.
A -1.30% mass-weighted MEAN nets a majority of shortfalls against a minority of overstatements;
it cannot license a no-risk conclusion about a tail.

## D7 — the 1-s and 30-s numbers are NOT REPRODUCIBLE
Only *_series_15s.csv and *_series_60s.csv are shipped. .by_resolution.1.* and .30.* are
JSON-only assertions. The -16.46% I called "a diagnostic" is unverified, not merely
non-load-bearing.

## D8 — my "controller acts at 15 s" premise was FALSE
planner_forecast_smoke.json:11 sets throughput_adjustment_interval_seconds: 60, and
replay_with_forecast.py:106-119 takes a STRIDE-4 POINT SAMPLE — 3 of every 4 15-s bins are never
read. Bias over the actually-sampled bins, by phase offset: +2.17% / -1.52% / -3.62% / -1.51%.

## D9 — sign-convention contradiction inside one file
timesfm_e2e_a16_summary.txt prints "+ = truth exceeds the stamp = ANTI-conservative" above a
table showing +1.30%, and "[+ = stamp exceeds truth]" in the VERDICT block showing -1.297%, for
the same quantity. A reader transcribing across blocks inverts the headline.

## Required before this can be used
1. Ship the 1-s and 30-s series or delete those JSON blocks.
2. Report BOTH selection conventions (truth-selected and arrival-selected) side by side — the
   sign flip is the actual finding and it is interesting.
3. Use the mass-weighted onset ratio (2.796) and report the tier curve, not one tier.
4. Quote 1.67e-05 for trace fidelity; stop calling the construction identity "exact".
5. Rename vs_trace_arrival -> vs_composed_arrival, or make the trace join work.
6. Fix the sign convention to be identical in both blocks.
7. Report the stride-4 sampled population for any controller-relevant claim.

## The honest headline, if it survives a re-run
On the OBSERVABLE arrival-selected definition the series is strongly conservative in the busiest
bins (+54%), which SUPPORTS the thesis's upper-bound framing; on a truth-selected definition it
is mildly anti-conservative (-1.3% to -3.4%). The defensible sentence is that the stamp is
conservative with respect to what the controller can see, and that its shortfalls concentrate in
bins the controller cannot identify in advance.
