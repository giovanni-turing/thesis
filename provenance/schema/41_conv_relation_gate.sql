-- 41_conv_relation_gate.sql -- D61 (bridge 181, 2026-07-27): two provenance
-- repairs on migration 40's work. (1) The LIVE comment on
-- v_joint_e2e.e2e_vs_sum_evidence still described the retired
-- display-precision-only derivation (migration 39's text); it now states the
-- two-path derivation migration 40 actually installed. (2) Migration 40's
-- postconditions derived the evidence label tautologically from
-- conv_sum_relation and never bound the relation to the SIGN/TOLERANCE of
-- conv_sum_minus_e2e_ms -- a fixture with swapped relation strings
-- false-greened. The gate below enforces the biconditional per
-- evidence-bearing row and pins the three discriminating cells.
-- (Migration 40's header prose about "retiring both false labels" was
-- corrected in the same commit: calm/static's binary label flips;
-- burst3/static's rightly remains strictly_differs -- the DIRECTION is what
-- the persisted relation corrects there.)

COMMENT ON COLUMN provenance.v_joint_e2e.e2e_vs_sum_evidence IS
  'Two-path derivation (migrations 40/41). Rows carrying producer-persisted evidence (the 9 composed_fill rows) derive this label from the FULL-PRECISION single-estimator conv_sum_relation: ''coincides'' -> coincides_with_sum, else strictly_differs_from_sum. Only the 20 legacy a12 rows (NULL evidence) classify from the rounded display columns at +/-0.05 ms. For relation claims (overstates / understates / coincides) use conv_sum_relation itself -- this label is binary and does not carry direction.';

DO $$
DECLARE n int;
BEGIN
  -- (2) relation <=> delta biconditional, every evidence-bearing row:
  --     coincides   <=> |delta| <= 1e-6
  --     overstates  <=> delta  >  1e-6
  --     understates <=> delta  < -1e-6
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE conv_sum_relation IS NOT NULL
     AND conv_sum_relation <> CASE
           WHEN abs(conv_sum_minus_e2e_ms) <= 1e-6 THEN 'coincides'
           WHEN conv_sum_minus_e2e_ms > 1e-6       THEN 'overstates'
           ELSE 'understates' END;
  IF n <> 0 THEN
    RAISE EXCEPTION '% evidence rows where conv_sum_relation disagrees with the sign/tolerance of conv_sum_minus_e2e_ms', n;
  END IF;

  -- rows with a relation but no delta (or vice versa) are malformed evidence
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE (conv_sum_relation IS NULL) <> (conv_sum_minus_e2e_ms IS NULL);
  IF n <> 0 THEN
    RAISE EXCEPTION '% rows carry exactly one of relation/delta', n;
  END IF;

  -- the three discriminating cells, pinned by identity AND relation
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE window_name = 'burst3' AND arm = 'static_C8'
     AND conv_sum_relation = 'overstates'
     AND conv_sum_minus_e2e_ms > 0.12 AND conv_sum_minus_e2e_ms < 0.14;
  IF n <> 1 THEN RAISE EXCEPTION 'burst3/static_C8 overstates pin failed'; END IF;
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE window_name = 'steady24h' AND arm = 'static_C8'
     AND conv_sum_relation = 'coincides';
  IF n <> 1 THEN RAISE EXCEPTION 'steady24h/static_C8 coincides pin failed'; END IF;
  SELECT count(*) INTO n FROM provenance.v_joint_e2e
   WHERE window_name = 'steady24h' AND arm = 'fc_chronos'
     AND conv_sum_relation = 'understates'
     AND conv_sum_minus_e2e_ms < -45.8 AND conv_sum_minus_e2e_ms > -45.9;
  IF n <> 1 THEN RAISE EXCEPTION 'steady24h/fc_chronos understates pin failed'; END IF;
END $$;
