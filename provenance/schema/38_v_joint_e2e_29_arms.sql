-- 38_v_joint_e2e_29_arms.sql -- refresh v_joint_e2e's self-description after the
-- composed-coverage fill campaign took composed_e2e from 20 to 29 request-linked arms
-- (K16, simulation/results/composed_fill/composed_fill_joined.json, 2026-07-26).
--
-- The view DEFINITION is unchanged and is deliberately not restated here. What changed is
-- the empirical argument the COMMENT carries, and one clause of it is now false:
--
--   old: "7 rows differ, and ALL 7 have e2e_p99_ms STRICTLY BELOW the sum -- never above"
--
-- Two of the nine new rows sit strictly ABOVE their naive sum, so the naive sum is not a
-- one-sided error after all. That was always the view's stated position ("neither an upper
-- nor a lower bound"); the data now demonstrates it in both directions instead of only one,
-- and a reader who trusted the old parenthetical would draw exactly the wrong conclusion.
--
-- Counts recomputed against the live view, 29 rows:
--   coincides_with_sum        13
--   strictly_differs_from_sum 16  = 14 below the sum + 2 ABOVE it
--     above: steady24h/fc_chronos 1122.2 vs 1076.4 (0.9592x), burst3/static_C8 1481.0 vs
--            1476.1 (0.9967x)

COMMENT ON VIEW provenance.v_joint_e2e IS
$$Composed end-to-end picture per window and arm: encoder delay, language TTFT and
ITL, and the request-linked composed E2E, side by side, in MILLISECONDS.

THE POINT OF THIS VIEW is the distinction it makes explicit. e2e_p99_ms is the 99th
percentile of per-request composed latency, obtained by joining the vision and
language stages ON REQUEST IDENTITY and then taking the percentile. It is NOT
encoder_delay_p99_ms + ttft_p99_ms. Those two percentiles are attained by different
requests, so their sum is neither an upper nor a lower bound on the composed p99 --
it is simply a different number with no interpretation. Because that sum is the
single most natural mistake to make with this table, it is computed here as
naive_sum_of_p99s_ms and differenced against the truth, and every row carries
e2e_p99_is_request_linked = TRUE plus a prose statement in e2e_p99_semantics.

COVERAGE. 29 request-linked arms over 7 window labels, from two join artifacts:
20 from defense/anim/data/a12_data.json (aggregate + burst1/3/4/5, four policy arms
each) and 9 from simulation/results/composed_fill/composed_fill_joined.json (the
2026-07-26 fill campaign: static C=8 on burst1/3/4/5 and steady24h; forecast-p90
and reactive on steady24h; the fulltrace static C=8 / reactive pair). Two cells are
absent BY PROTOCOL, not by omission, and no future ingest should fill them:
burst2/burst6 are the calibration split (replaying them as composed evaluation
cells would grade a result on forecast-context data), and no fulltrace forecast arm
can exist because the forecast archive's first 1.4 days are that forecast's own
context. source_path distinguishes the two artifacts; the key is
(source_path, window_name, arm).

READ THIS BEFORE CONCLUDING THE DATA IS ADDITIVE. 13 of the 29 rows have e2e_p99_ms
equal to enc_p99_ms + ttft_p99_ms, which looks at first glance like the sum was
simply stored. It was not:

  * 16 rows differ from their sum, and they differ in BOTH directions -- 14 below
    the sum and 2 above it. A stored sum can be neither. The largest deviation
    below is burst3/reactive (21868.0 vs 26652.4, 1.2188x); the two above are
    steady24h/fc_chronos (1122.2 vs 1076.4, 0.9592x) and burst3/static_C8
    (1481.0 vs 1476.1, 0.9967x). Every one of these rows independently
    demonstrates the join.
  * The 13 coinciding rows are forecast arms on windows where the encoder is
    never saturated. Their stage p99s are pinned at the service floor (enc
    588.4, ttft 651.1) and are identical across windows of wildly different
    size. When both stage distributions are near-deterministic, the p99 of the
    sum equals the sum of the p99s -- arithmetic coincidence, not additive
    computation. The split is NOT policy-aligned: forecast arms appear on both
    sides (2 on burst1, 1 on steady24h), which is why the evidence is recorded
    per row rather than inferred from the arm.
  * The clincher: on those same forecast rows e2e_max_ms DOES vary by window
    (2185.8 / 2572.5 / 3735.3 / 38188.0). A hardcoded additive placeholder would
    not produce a per-window-varying max off the same distribution.

WHY A ROW CAN SIT ABOVE ITS SUM. Percentiles are not subadditive. On steady24h
57.3% of requests are text-only, so the encoder-delay marginal is a majority atom
at zero with a thin tail; its correlation with TTFT is 0.458; and 1.13% of
requests (998 of 88,260) land above the naive sum. Nothing is wrong with that row.
Anyone using naive_sum_of_p99s_ms as a conservative bound is wrong in both
directions, which is the entire reason this view exists.

PRECISION. composed_e2e stores stage and composed p99s at 1 decimal place, so the
derived naive_sum / difference / ratio columns here inherit that rounding and are
good to about +/-0.1 ms. Do not read a ratio of 1.0001 as a real deviation:
steady24h/static_C8 reads 1.0001x here and is exactly 1.00000x on the unrounded
join. Where a fine distinction matters, recompute from the join artifact named in
source_path.

So the join is real throughout; e2e_vs_sum_evidence records, per row, whether that
row independently demonstrates it ('strictly_differs_from_sum') or is merely
consistent with it ('coincides_with_sum'). Do not read 'coincides_with_sum' as a
defect, and do not read it as confirmation either.

Worked example -- the composed picture per window, with the size of the
sum-of-percentiles error made visible:

    SELECT window_name, arm, policy, forecast_model,
           encoder_delay_p99_ms, ttft_p99_ms, e2e_p99_ms,
           naive_sum_of_p99s_ms,
           round(naive_sum_minus_joined_ms::numeric, 1) AS error_ms,
           round(naive_sum_over_joined_ratio::numeric, 4) AS error_x
      FROM provenance.v_joint_e2e
     ORDER BY window_name, arm;

Worked example -- the rows where the naive sum UNDERSTATES the measured tail
(these are the ones that refute "the sum is at least conservative"):

    SELECT window_name, arm, e2e_p99_ms, naive_sum_of_p99s_ms,
           round(naive_sum_over_joined_ratio::numeric, 4) AS sum_over_true
      FROM provenance.v_joint_e2e
     WHERE naive_sum_over_joined_ratio < 1
     ORDER BY naive_sum_over_joined_ratio;

Worked example -- how wrong the additive assumption gets, worst case:

    SELECT window_name, arm,
           round(naive_sum_over_joined_ratio::numeric, 3) AS sum_over_true
      FROM provenance.v_joint_e2e
     WHERE naive_sum_over_joined_ratio IS NOT NULL
     ORDER BY abs(naive_sum_over_joined_ratio - 1) DESC
     LIMIT 10;$$;

COMMENT ON COLUMN provenance.v_joint_e2e.e2e_vs_sum_evidence IS
  'Per-row evidence for the request-linked claim. ''strictly_differs_from_sum'': e2e_p99_ms differs from enc+ttft, which a stored sum could not do -- this row independently demonstrates the join (16 of 29 rows: 14 below the sum, 2 above it). ''coincides_with_sum'': the two agree because both stages are pinned at their service floor, so the row is consistent with the join but does not by itself prove it (13 forecast rows). NOT a data-quality flag -- see the view comment for the full argument.';

COMMENT ON COLUMN provenance.v_joint_e2e.naive_sum_minus_joined_ms IS
  'naive_sum_of_p99s_ms - e2e_p99_ms, MILLISECONDS. Magnitude of the error made by adding percentiles. Sign is NOT fixed and this is observed, not merely conceded: 14 of the 29 arms are positive (sum overstates) and 2 are negative (sum understates, worst steady24h/fc_chronos at -45.8 ms). Never treat the sum as a conservative bound.';

COMMENT ON COLUMN provenance.v_joint_e2e.policy IS
  'static | reactive | forecast. ''static'' is the deployable fixed C=8 fleet; ''forecast'' is a foundation-model quantile forecast (see forecast_model). The 9 fill-campaign rows use this same vocabulary even though their source artifact spells the forecast policy ''forecast_p90''.';
