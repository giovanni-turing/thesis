-- =====================================================================
-- 24_group_c_checks.sql -- regression probes for ADJUDICATION §2.4/§2.5/§2.11
--
-- Registered into provenance.check_definition, so they run under check_all()
-- alongside C001-C203. Contract (from 21_checks.sql): sql_text returns exactly
-- one row of (passed boolean, detail text).
--
-- The point of C401-C403 is that provenance.capacity_derivation must add NO
-- information. It is a convenience projection of capacity_belief_sample and
-- capacity_knee_probe; if the stored derivation ever stops being reproducible
-- FROM those two tables, the "derived, not tuned" claim at closedloop.tex:328
-- is no longer backed and these checks must go red rather than be relaxed.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;

-- ---------------------------------------------------------------------
-- C401 -- the belief is the median of the stored ticks
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C401',
 'capacity_derivation.belief_rps = median of non-degenerate belief ticks',
 'error',
 $q$
 WITH m AS (
   SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY engine_rps) AS med,
          count(*) AS n
     FROM provenance.capacity_belief_sample s
     JOIN (SELECT DISTINCT belief_source_log FROM provenance.capacity_derivation) d
       ON d.belief_source_log = s.source_log
    WHERE NOT s.is_degenerate
 ), d AS (
   SELECT DISTINCT belief_rps, belief_n_ticks FROM provenance.capacity_derivation
 )
 , bad AS (
   SELECT string_agg(format('belief %s vs recomputed %s (n stored %s, actual %s)',
                            round(d.belief_rps::numeric,6), round(m.med::numeric,6),
                            d.belief_n_ticks, m.n), '; ') AS msg
     FROM d CROSS JOIN m
    WHERE abs(d.belief_rps - m.med) > 1e-9 OR d.belief_n_ticks <> m.n
 )
 SELECT bad.msg IS NULL AS passed,
        coalesce(bad.msg,
                 format('OK: belief = %s over %s non-degenerate ticks',
                        round(m.med::numeric,4), m.n)) AS detail
   FROM bad CROSS JOIN m
 $q$,
 'passed = true',
 'cheap',
 'Asserts the stored belief is exactly the median of the ticks actually in the store, over '
 'the recorded source log, with the degenerate ticks excluded by the recorded rule. '
 'Tolerance is 1e-9 -- an identity, not a comparison, so there is nothing to loosen.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C402 -- the measured knee is the largest PASSING per-replica rate
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C402',
 'capacity_derivation.r_tail_rps = max passing offered_rps_per_replica, and the next rung fails',
 'error',
 $q$
 WITH k AS (
   SELECT window_name,
          max(offered_rps_per_replica) FILTER (WHERE passes)     AS best_pass,
          min(offered_rps_per_replica) FILTER (WHERE NOT passes) AS first_fail
     FROM provenance.capacity_knee_probe
    WHERE probe_kind = 'arrival_speedup' AND NOT is_superseded
    GROUP BY window_name
 )
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s: stored %s, max-pass %s, first-fail %s',
                                   d.window_name, round(d.r_tail_rps::numeric,6), round(k.best_pass::numeric,6), round(k.first_fail::numeric,6)), '; '),
                 'OK: every measured knee is the largest passing rung and is bracketed above by a failing one')
   FROM provenance.capacity_derivation d
   JOIN k USING (window_name)
  WHERE d.r_tail_method = 'measured'
    AND (abs(d.r_tail_rps - k.best_pass) > 1e-9
         OR k.first_fail IS NULL
         OR k.first_fail <= k.best_pass)
 $q$,
 'passed = true',
 'cheap',
 'Two assertions in one, both necessary for the knee to mean anything. (1) The stored knee is '
 'the largest per-replica rate that PASSED. (2) It is genuinely a knee: some higher rung FAILED. '
 'Without (2) the ladder merely ran out of rungs and the "knee" would be a floor on the knee, '
 'not the knee. burst1 satisfies both (1.6233 passes at 905.86 ms, 2.1643 fails at 1078.61 ms).'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C403 -- scale = belief / r_tail, and the bracket is a real bracket
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C403',
 'capacity_derivation: implied_scale = belief / r_tail and margin = adopted / implied',
 'error',
 $q$
 WITH d AS (
   SELECT derivation_id, belief_rps, adopted_scale, implied_scale, margin_over_knee,
          CASE r_tail_basis
            WHEN 'measured' THEN r_tail_rps
            WHEN 'hi'       THEN r_tail_hi_rps
            WHEN 'lo'       THEN r_tail_lo_rps
          END AS r_used, r_tail_basis,
          r_tail_method, r_tail_lo_rps, r_tail_hi_rps, window_name
     FROM provenance.capacity_derivation
 )
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s: implied %s vs belief/r_tail %s, margin %s vs %s',
                                   derivation_id, round(implied_scale::numeric,6), round((belief_rps / r_used)::numeric,6),
                                   round(margin_over_knee::numeric,6), round((adopted_scale / implied_scale)::numeric,6)), '; '),
                 'OK: every derivation row reproduces from belief and the knee') AS detail
   FROM d
  WHERE r_used IS NULL
     OR abs(implied_scale - belief_rps / r_used) > 1e-6
     OR abs(margin_over_knee - adopted_scale / implied_scale) > 1e-6
     OR (r_tail_method = 'bracketed' AND NOT (r_tail_lo_rps < r_tail_hi_rps))
 $q$,
 'passed = true',
 'cheap',
 'The formula itself: scale = belief / r_tail, margin = adopted / implied. Which r_tail is '
 'divided by differs per row and is read from r_tail_basis: the burst4 row uses the bracket '
 'HIGH end (the minimum scale the SLA demands, 7.0), the fleet row the LOW end (the adopted '
 '8.0). An earlier version of this check hard-coded coalesce(r_tail_rps, r_tail_hi_rps) and '
 'reported the fleet row as a defect -- the CHECK was wrong, not the data, which is why the '
 'basis is now an explicit stored column rather than an inference. Also asserts every '
 'bracketed row is a real interval (lo < hi).'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C404 -- the fabric conditional (§2.11b)
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C404',
 'handoff alone violates the 1 s bound at 6.25 Gbps for every run, and for none at 25 Gbps',
 'error',
 $q$
 WITH g AS (
   SELECT e.handoff_gbps,
          count(*) AS n,
          count(*) FILTER (WHERE e.handoff_p99_ms > 1000.0) AS n_violating
     FROM provenance.encoder_run_summary e
     JOIN provenance.runs r USING (run_id)
    WHERE e.handoff_gbps IS NOT NULL AND e.handoff_p99_ms IS NOT NULL
      -- The g6 family is a post-manuscript DEFENCE resolution sweep whose payload is
      -- 784 post-merge tokens/image (896^2), 4x the thesis's 196 (448^2). Its 25 Gbps
      -- arm therefore carries the same bytes-per-second load as the thesis's 6.25 Gbps
      -- arm and violates for the same physical reason -- it is not a counterexample to
      -- the thesis claim, it is the SAME result at a different operating point. It is
      -- excluded here because intro.tex:514-516 is a claim about the thesis's uniform
      -- 448^2 configuration, and C407 asserts this exclusion hides nothing.
      AND r.experiment <> 'g6'
    GROUP BY e.handoff_gbps
 )
 SELECT bool_and(CASE WHEN handoff_gbps <= 6.25 THEN n_violating = n
                      WHEN handoff_gbps >= 25.0 THEN n_violating = 0
                      ELSE true END) AS passed,
        string_agg(format('%s Gbps: %s/%s runs violate on handoff alone',
                          round(handoff_gbps::numeric,2), n_violating, n), '; ' ORDER BY handoff_gbps) AS detail
   FROM g
 $q$,
 'passed = true',
 'cheap',
 'Backs intro.tex:514-516. At the default 25 Gbps no run''s handoff p99 alone breaches the '
 '1,000 ms bound; at the 4x-downscaled 6.25 Gbps every one does, regardless of policy -- which '
 'is what makes the thesis''s "a fabric requirement, not a policy weakness" a measured '
 'statement rather than an assertion. This check is the reason handoff_gbps was promoted out '
 'of the metrics jsonb: it could not be expressed before. SCOPE: thesis runs only -- the g6 '
 'defence resolution sweep is excluded and audited separately by C407. The exclusion is by '
 'experiment, declared here, and is NOT a tolerance: within its stated scope the assertion is '
 'exactly as strong as it was when first written.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C405 -- the backfill never overwrote a measurement (§2.5)
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C405',
 'every runs_config_backfill row replaced a NULL and matches the current runs value',
 'error',
 $q$
 WITH b AS (
   SELECT b.run_id, b.column_name, b.old_value, b.new_value,
          CASE b.column_name
            WHEN 'lead_s'      THEN r.lead_s::text
            WHEN 'tp'          THEN r.tp::text
            WHEN 'window_name' THEN r.window_name
            ELSE NULL END AS live_value
     FROM provenance.runs_config_backfill b
     JOIN provenance.runs r USING (run_id)
 )
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s.%s: old=%s new=%s live=%s',
                                   run_id, column_name, old_value, new_value, live_value), '; '),
                 format('OK: %s backfills, all NULL->value, all still matching runs',
                        (SELECT count(*) FROM provenance.runs_config_backfill))) AS detail
   FROM b
  WHERE old_value IS NOT NULL OR live_value IS DISTINCT FROM new_value
 $q$,
 'passed = true',
 'cheap',
 'Guards the never-overwrite rule for §2.5/§2.12 configuration backfills. A non-NULL old_value '
 'means an archived dimension was replaced and must be investigated; a live value that has '
 'drifted from new_value means something outside the loader edited runs without recording it. '
 'Either way the honest response is a red check, not a wider predicate.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C406 -- the factoring invariance (§2.11c)
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C406',
 'encoder cost is invariant to the (batch, images-per-request) factoring of a fixed image total',
 'error',
 $q$
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('total_images=%s: %s distinct predicted_ms, max delta %s',
                                   total_images, n_distinct, round(max_delta::numeric,6)), '; '),
                 format('OK: %s factorings across %s image totals, all identical',
                        (SELECT count(*) FROM provenance.encoder_factoring_probe),
                        (SELECT count(DISTINCT total_images)
                           FROM provenance.encoder_factoring_probe))) AS detail
   FROM (
     SELECT total_images,
            count(DISTINCT predicted_ms) AS n_distinct,
            max(abs(delta_vs_ref_ms))    AS max_delta
       FROM provenance.encoder_factoring_probe
      GROUP BY total_images
   ) t
  WHERE n_distinct > 1 OR max_delta > 1e-6
 $q$,
 'passed = true',
 'cheap',
 'Backs twopool.tex:110-123. Every (batch_size, images_per_request) split of the same image '
 'total must price identically -- that invariance is what licenses the simulator to cost each '
 'dispatched batch by its image count alone. If it ever fails, the encoder pool''s batching '
 'model is wrong, not the check.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C407 -- the g6 exclusion from C404 hides nothing
-- ---------------------------------------------------------------------
-- C404 scopes itself to the thesis's uniform-448 configuration. That scoping is only
-- honest if the excluded population is exactly the one described and no larger. C407
-- pins it: every 25 Gbps run that violates the bound on handoff alone must be a g6
-- u896 run, and there must be exactly 12 of them. If a THESIS run ever starts
-- violating, C407 goes red even though C404 stays green -- which is the whole point.
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C407',
 'the only 25 Gbps handoff-alone violations are the 12 known g6 u896 defence runs',
 'error',
 $q$
 WITH v AS (
   SELECT e.run_id, r.experiment,
          e.run_id LIKE 'g6:u896%' AS is_known_g6
     FROM provenance.encoder_run_summary e
     JOIN provenance.runs r USING (run_id)
    WHERE e.handoff_gbps = 25.0 AND e.handoff_p99_ms > 1000.0
 )
 SELECT (count(*) FILTER (WHERE NOT is_known_g6) = 0 AND count(*) = 12) AS passed,
        format('%s violating runs at 25 Gbps; %s are g6 u896; unexpected: %s',
               count(*), count(*) FILTER (WHERE is_known_g6),
               coalesce(string_agg(run_id, ', ') FILTER (WHERE NOT is_known_g6), 'none')) AS detail
   FROM v
 $q$,
 'passed = true',
 'cheap',
 'Companion to C404 and the reason C404''s scoping is not a quiet narrowing. The 12 g6 u896 '
 'runs violate at 25 Gbps because their post-merge payload is 784 tokens/image (896^2) rather '
 'than the thesis''s 196 (448^2) -- 4x the bytes, hence the SAME handoff p99 of 1087.406 ms as '
 'the thesis''s 6.25 Gbps arm. Confirming the physics, not contradicting it. '
 'KNOWN DATA DEFECT, recorded rather than fixed here because it is outside ADJUDICATION §2.11: '
 'encoder_run_summary.image_px reads 448 on all 12 rows even though the mixture is 896^2. The '
 'stats.json emits image_px as a simulator default and the real payload lives in the sidecar '
 '<stem>.jsonl.g6mix.json (mixture {"896": 1.0}, post_merge_per_image 784), which is not '
 'ingested. Consequence: image_px MUST NOT be used to reason about g6 payload, and the exact '
 'bandwidth-per-payload law cannot yet be asserted in SQL. Ingesting the g6mix sidecars would '
 'let C404 be restated as a single physical law over all runs with no exclusion at all.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;
