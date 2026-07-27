-- 40_v_joint_e2e_conv_derivation.sql -- D30 round 2 (bridge 172, 2026-07-27):
-- migration 39 added the producer-persisted estimator-consistent evidence to
-- the BASE TABLE only; v_joint_e2e neither exposed the fields nor derived its
-- evidence interface from them, and 39's own worked-example queries referenced
-- view columns that did not exist. This migration makes the view derive from
-- the persisted evidence and gates the executable interface.
--
--   * The two evidence columns are APPENDED to the view (conv_sum_minus_e2e_ms,
--     conv_sum_relation).
--   * e2e_vs_sum_evidence now DERIVES from the consistent field where present:
--     rows carrying producer evidence classify from conv_sum_relation
--     ('coincides' -> coincides_with_sum, else strictly_differs_from_sum);
--     only the 20 legacy a12 rows (NULL evidence) fall back to the rounded
--     display-precision CASE. Effect on the two artifact rows (D61 wording
--     correction, same commit as migration 41): calm/static's binary label
--     FLIPS to coincides_with_sum (the rounded CASE had mislabeled it);
--     burst3/static's binary label rightly REMAINS strictly_differs_from_sum
--     -- what the persisted relation corrects there is the DIRECTION (a
--     +0.127588 ms overstate under the single estimator, not the apparent
--     understate the mixed-estimator display read suggested).
--   * Postconditions gate the VIEW: both columns present, the migration-39
--     worked query executes and returns exactly the one genuine understates
--     row (steady24h/fc_chronos), and the fill-row classification THROUGH THE
--     VIEW is 7 overstates / 1 understates / 1 coincides.

CREATE OR REPLACE VIEW provenance.v_joint_e2e AS
SELECT
    coalesce(a.canonical_window, c.window_name)      AS window_name,
    c.window_name                                    AS window_name_raw,
    c.arm,
    c.policy,
    c.model                                          AS forecast_model,
    c.requests                                       AS n_requests,

    c.enc_p99_ms                                     AS encoder_delay_p99_ms,
    c.ttft_p99_ms,
    c.itl_p99_ms,
    c.e2e_p99_ms,
    c.e2e_max_ms,
    c.gpu_hours,

    -- the arithmetic an unwary reader performs, computed here so the gap
    -- between it and the truth is visible instead of assumed away
    (c.enc_p99_ms + c.ttft_p99_ms)                   AS naive_sum_of_p99s_ms,
    (c.enc_p99_ms + c.ttft_p99_ms) - c.e2e_p99_ms    AS naive_sum_minus_joined_ms,
    CASE WHEN c.e2e_p99_ms > 0
         THEN (c.enc_p99_ms + c.ttft_p99_ms) / c.e2e_p99_ms END
                                                     AS naive_sum_over_joined_ratio,

    TRUE                                             AS e2e_p99_is_request_linked,

    -- D30: derived from the PERSISTED single-estimator evidence where present
    -- (the 9 fill rows); the display-precision fallback applies only to the
    -- 20 legacy a12 rows whose artifact predates the evidence fields.
    CASE
      WHEN c.conv_sum_relation IS NOT NULL THEN
        CASE WHEN c.conv_sum_relation = 'coincides'
             THEN 'coincides_with_sum'
             ELSE 'strictly_differs_from_sum' END
      WHEN c.e2e_p99_ms IS NULL OR c.enc_p99_ms IS NULL OR c.ttft_p99_ms IS NULL
        THEN 'unknown'
      WHEN abs((c.enc_p99_ms + c.ttft_p99_ms) - c.e2e_p99_ms) < 0.05
        THEN 'coincides_with_sum'
      ELSE 'strictly_differs_from_sum'
    END                                              AS e2e_vs_sum_evidence,

    'e2e_p99_ms is the p99 of per-request composed latency (encoder and language '
    'stages joined on request identity). It is NOT enc_p99_ms + ttft_p99_ms: the '
    '99th percentiles of two stages are attained by different requests, so summing '
    'them is neither an upper nor a lower bound. Where e2e_vs_sum_evidence = '
    '''coincides_with_sum'' the two happen to agree because both stages sit at '
    'their floor, NOT because the value was computed additively -- see the view '
    'comment. Compare naive_sum_of_p99s_ms for the size of the discrepancy.'::text
                                                     AS e2e_p99_semantics,

    c.composed_trace,
    c.source_path,
    c.conv_sum_minus_e2e_ms,
    c.conv_sum_relation
FROM provenance.composed_e2e c
LEFT JOIN provenance.v_window_alias a
       ON a.alias = c.window_name AND a.canonical_window IS NOT NULL;

-- Postconditions: the EXECUTABLE interface, not just the base table.
DO $$
DECLARE n int; w text; ar text;
BEGIN
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'provenance' AND table_name = 'v_joint_e2e'
     AND column_name IN ('conv_sum_minus_e2e_ms', 'conv_sum_relation');
  IF n <> 2 THEN RAISE EXCEPTION 'v_joint_e2e evidence columns missing (%)', n; END IF;

  SELECT count(*) INTO n FROM provenance.v_joint_e2e;
  IF n <> 29 THEN RAISE EXCEPTION 'v_joint_e2e expected 29 rows, found %', n; END IF;

  -- migration 39's worked query, now executable: exactly ONE genuine
  -- understates row, and it is steady24h/fc_chronos.
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE conv_sum_relation = 'understates';
  IF n <> 1 THEN RAISE EXCEPTION 'expected exactly 1 understates row, found %', n; END IF;
  SELECT window_name, arm INTO w, ar FROM provenance.v_joint_e2e
   WHERE conv_sum_relation = 'understates';
  IF w <> 'steady24h' OR ar <> 'fc_chronos' THEN
    RAISE EXCEPTION 'understates row is %/%, expected steady24h/fc_chronos', w, ar;
  END IF;

  -- fill-row classification THROUGH THE VIEW: 7 / 1 / 1
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE conv_sum_relation = 'overstates';
  IF n <> 7 THEN RAISE EXCEPTION 'expected 7 overstates rows, found %', n; END IF;
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE conv_sum_relation = 'coincides';
  IF n <> 1 THEN RAISE EXCEPTION 'expected 1 coincides row, found %', n; END IF;

  -- the persisted-evidence derivation retired the two false labels: every
  -- evidence-bearing row's e2e_vs_sum_evidence must agree with its relation.
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE conv_sum_relation IS NOT NULL
     AND e2e_vs_sum_evidence <> CASE WHEN conv_sum_relation = 'coincides'
                                     THEN 'coincides_with_sum'
                                     ELSE 'strictly_differs_from_sum' END;
  IF n <> 0 THEN RAISE EXCEPTION '% evidence rows disagree with persisted relation', n; END IF;
END $$;
