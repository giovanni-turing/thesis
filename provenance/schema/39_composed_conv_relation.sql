-- 39_composed_conv_relation.sql -- D30 (bridge findings 071 + 167, 2026-07-27):
-- persist the producer's FULL-PRECISION, SELF-CONSISTENT sum-vs-composed
-- relation, and correct the classification schema 38's comment promoted.
--
-- WHAT WAS WRONG. Schema 38 classified the 29 arms from the STORED 1-decimal
-- columns, whose naive sum mixes two p99 conventions (the replay report's
-- round((n-1)*99/100) index for TTFT against the join's CONV index for the
-- composed value). That produced 13 coincides / 16 strictly-differs
-- (14 below + 2 above) and named burst3/static_C8 a second above-the-sum case.
-- Both extra classifications are artifacts:
--   * burst3/static_C8: mixed estimators. At full precision under ONE
--     estimator the CONV sum is 1481.159797 ms against E2E 1481.032209 ms --
--     the sum OVERSTATES by 0.127588 ms (1.000086x). The manuscript
--     (tex/closedloop.tex, "the sum is not a bound in either direction")
--     already states this; the old comment contradicted it.
--   * steady24h/static_C8: display rounding. 417.3 + 388.6 = 805.9 vs 805.8
--     read as "differs", but the unrounded values coincide to 4e-9 ms.
-- The estimator-consistent full-precision classification over the 29 arms is
--   14 sum-overstates / 1 genuine sum-understates / 14 numerically coincident,
-- and the ONE genuine understates row is steady24h/fc_chronos
-- (1122.201991 > 1076.385993, -45.815998 ms).
--
-- WHAT THIS MIGRATION DOES.
--   1. Adds producer-persisted evidence columns to composed_e2e: the join
--      artifact now carries, per cell, conv_sum_minus_e2e_ms (full-precision
--      CONV sum minus composed p99, 6 decimals) and conv_sum_relation
--      ('overstates' | 'understates' | 'coincides', |delta| <= 1e-6 ms =
--      coincident). K16 ingests them; the 20 a12-artifact rows carry NULL
--      (their artifact predates the evidence fields).
--   2. Rewrites the v_joint_e2e comment so the classification is DERIVED FROM
--      the persisted evidence (or full-precision recomputation from the
--      artifact named in source_path), never from re-differencing rounded
--      display columns.
--   3. Narrows the coverage prose: the burst2/burst6 prohibition applies to
--      FORECAST arms (calibration split -- a forecast graded there would be
--      graded on its own context data). Forecast-free composed halves for
--      burst2/6 exist (defense/anim/data/g1_runs/) and are permissible; they
--      are outside the frozen fill-campaign arm set, not forbidden.

ALTER TABLE provenance.composed_e2e
  ADD COLUMN IF NOT EXISTS conv_sum_minus_e2e_ms double precision,
  ADD COLUMN IF NOT EXISTS conv_sum_relation text;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'composed_e2e_conv_relation_chk') THEN
    ALTER TABLE provenance.composed_e2e
      ADD CONSTRAINT composed_e2e_conv_relation_chk
      CHECK (conv_sum_relation IS NULL
             OR conv_sum_relation IN ('overstates', 'understates', 'coincides'));
  END IF;
END $$;

COMMENT ON COLUMN provenance.composed_e2e.conv_sum_minus_e2e_ms IS
  'Producer-persisted evidence (D30): full-precision SELF-CONSISTENT (CONV-estimator) naive sum minus composed e2e p99, ms, 6 decimals. NULL on rows whose source artifact predates the field (the 20 a12 rows). Use THIS -- never re-difference the rounded display columns.';

COMMENT ON COLUMN provenance.composed_e2e.conv_sum_relation IS
  'Producer-persisted sign class of conv_sum_minus_e2e_ms: overstates | understates | coincides (|delta| <= 1e-6 ms). Under the self-consistent estimator the fill campaign has exactly ONE genuine understates row: steady24h/fc_chronos (-45.815998 ms). burst3/static_C8 is overstates (+0.127588 ms); its old above-the-sum reading was a mixed-estimator artifact.';

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
and reactive on steady24h; the fulltrace static C=8 / reactive pair). Absent cells:
burst2/burst6 carry no FORECAST arm by protocol (they are the calibration split;
a forecast graded there would be graded on its own context data), and no
fulltrace forecast arm can exist (the archive's first 1.4 days are that
forecast's own context). Forecast-FREE composed halves for burst2/6 exist
(defense/anim/data/g1_runs/) and are permissible; they sit outside the frozen
fill-campaign arm set. source_path distinguishes the two artifacts; the key is
(source_path, window_name, arm).

ESTIMATOR DISCIPLINE (D30). The naive_sum/difference/ratio columns derive from
the STORED 1-decimal stage p99s, and the stored TTFT follows the replay report's
p99 index while the composed value uses the join's CONV index. A sum-vs-composed
RELATION is only meaningful under ONE estimator at FULL precision, so the fill
campaign's producer persists exactly that: conv_sum_minus_e2e_ms and
conv_sum_relation on the 9 composed_fill rows (NULL on the 20 a12 rows -- for
those, recompute from the artifact in source_path). Under the self-consistent
classification the 29 arms split
  14 sum-overstates / 1 genuine sum-understates / 14 numerically coincident.
The one genuine understates row is steady24h/fc_chronos (-45.815998 ms,
0.9592x): on the calm day 57.3% of requests are text-only, the encoder-delay
marginal is a majority atom at zero, its correlation with TTFT is 0.458, and
percentiles are not subadditive -- 998 of 88,260 requests land above the sum.
Two older readings are artifacts, not counterexamples: burst3/static_C8
"above the sum" was mixed estimators (overstates by +0.127588 ms under CONV),
and steady24h/static_C8 "strictly differs" was display rounding (coincides to
4e-9 ms unrounded).

The coincident rows are arms whose stage distributions are pinned at the
service floor (enc 588.4, ttft 651.1 on never-saturated forecast arms) plus the
numerically-coincident static calm-day row; when both stage distributions are
near-deterministic the p99 of the sum equals the sum of the p99s -- arithmetic
coincidence, not additive computation. The clincher that no row stores a sum:
on the floor-pinned forecast rows e2e_max_ms varies by window
(2185.8 / 2572.5 / 3735.3 / 38188.0) off the same stage distributions.

PRECISION. composed_e2e stores stage and composed p99s at 1 decimal place, so
the derived naive_sum / difference / ratio columns inherit that rounding and are
good to about +/-0.1 ms. Never read a 1.0001x ratio as a real deviation; where a
fine distinction matters, use conv_sum_minus_e2e_ms (fill rows) or recompute
from the artifact named in source_path.

Worked example -- the composed picture per window, with the size of the
sum-of-percentiles error made visible:

    SELECT window_name, arm, policy, forecast_model,
           encoder_delay_p99_ms, ttft_p99_ms, e2e_p99_ms,
           naive_sum_of_p99s_ms,
           round(naive_sum_minus_joined_ms::numeric, 1) AS error_ms,
           conv_sum_minus_e2e_ms, conv_sum_relation
      FROM provenance.v_joint_e2e
     ORDER BY window_name, arm;

Worked example -- the ONE genuine understates row under the self-consistent
estimator (the refutation of "the sum is at least conservative"):

    SELECT window_name, arm, e2e_p99_ms, conv_sum_minus_e2e_ms
      FROM provenance.v_joint_e2e
     WHERE conv_sum_relation = 'understates';$$;

COMMENT ON COLUMN provenance.v_joint_e2e.e2e_vs_sum_evidence IS
  'Per-row evidence AT DISPLAY PRECISION for the request-linked claim -- classification of the ROUNDED stored columns, kept for continuity. For the relation itself use conv_sum_relation (persisted, full-precision, single-estimator; fill rows) -- the rounded classification double-counts: burst3/static_C8 "above the sum" is a mixed-estimator artifact and steady24h/static_C8 "differs" is display rounding. See the view comment.';

COMMENT ON COLUMN provenance.v_joint_e2e.naive_sum_minus_joined_ms IS
  'naive_sum_of_p99s_ms - e2e_p99_ms at DISPLAY precision (rounded operands, mixed p99 conventions). Magnitude only; for sign/relation claims use conv_sum_minus_e2e_ms. Under the self-consistent full-precision classification: 14 overstates / 1 understates (steady24h/fc_chronos, -45.815998 ms) / 14 coincide. Never treat the sum as a conservative bound.';

-- Postconditions: structure only (data lands with the K16 reload that follows
-- this migration; the reload gate then verifies the 9-row evidence split).
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'provenance' AND table_name = 'composed_e2e'
     AND column_name IN ('conv_sum_minus_e2e_ms', 'conv_sum_relation');
  IF n <> 2 THEN RAISE EXCEPTION 'composed_e2e evidence columns missing (%)', n; END IF;
  SELECT count(*) INTO n FROM provenance.v_joint_e2e;
  IF n <> 29 THEN RAISE EXCEPTION 'v_joint_e2e expected 29 rows, found %', n; END IF;
END $$;
