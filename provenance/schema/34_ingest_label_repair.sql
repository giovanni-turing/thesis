-- =====================================================================
-- 34_ingest_label_repair.sql -- schema `provenance`, PostgreSQL 16
--
-- APPLIED 2026-07-26, during the adversarial-review remediation
-- (Finding 9 adjacency: C207 adjudication refresh).
--
-- C207's 2026-07-20 note characterised its failing population as two
-- disjoint parts: (1) 301 rows / 19 labels that are DEFINITIONAL
-- artifact-group labels (K20 grid, K25 sweeps, K26 costmodel, K27
-- ewma_cal, K28 rerun_b1, K29 eda_rates) whose loaders write aggregate
-- artifacts into dimension tables -- not failed loads, and not
-- repairable without inventing run identities; and (2) 5 rows of the
-- legacy, no-longer-registered kind K35 that ARE a real labelling
-- defect: the loader stamped runid.run_id_of(<the log file>) instead
-- of the run the log describes.
--
-- This migration repairs the mechanically-safe half of (2): the two
-- srcbuild rows, whose true spine runs EXIST and were already named in
-- C207's own note:
--
--   /simulation/results/srcbuild/run_aic.log
--       'srcbuild:run_aic'  -> 'srcbuild:llm_head2k_aic_src'
--   /simulation/results/srcbuild/run_poly.log
--       'srcbuild:run_poly' -> 'srcbuild:llm_head2k_poly_src'
--
-- (run_{aic,poly}.log is the replay log of the run whose report is
-- llm_head2k_{aic,poly}_src.json, the source_path of those spine rows;
-- K35 is unregistered in loader/main.py, so nothing can rewrite the
-- corrected labels.)
--
-- The three m235b rows (run_s1/_s4/_s16.log) are NOT repaired: their
-- family has no spine rows at all -- the three result JSONs
-- simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json were
-- never ingested (the standing, documented coverage gap). Pointing the
-- logs at runs that do not exist is impossible, and inventing the runs
-- from the logs would be a fabricated ingest. They stay orphaned and
-- documented.
--
-- Post-state: C207 fails with 304 of 4,320 rows / 19 labels, all
-- definitional or m235b-gap. The check is NOT weakened or exempted.
-- =====================================================================
SET search_path = provenance, public;

BEGIN;

UPDATE provenance.ingest_log
   SET run_id = 'srcbuild:llm_head2k_aic_src'
 WHERE file_path = '/home/gio/tese/simulation/results/srcbuild/run_aic.log'
   AND run_id = 'srcbuild:run_aic';

UPDATE provenance.ingest_log
   SET run_id = 'srcbuild:llm_head2k_poly_src'
 WHERE file_path = '/home/gio/tese/simulation/results/srcbuild/run_poly.log'
   AND run_id = 'srcbuild:run_poly';

DO $$
DECLARE
  n_orphan int;
  n_fixed  int;
BEGIN
  SELECT count(*) INTO n_fixed FROM provenance.ingest_log
   WHERE file_path IN ('/home/gio/tese/simulation/results/srcbuild/run_aic.log',
                       '/home/gio/tese/simulation/results/srcbuild/run_poly.log')
     AND run_id IN ('srcbuild:llm_head2k_aic_src', 'srcbuild:llm_head2k_poly_src')
     AND EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = ingest_log.run_id);
  IF n_fixed <> 2 THEN
    RAISE EXCEPTION 'srcbuild label repair incomplete: % of 2 rows resolve', n_fixed;
  END IF;

  SELECT count(*) INTO n_orphan FROM provenance.ingest_log x
   WHERE x.run_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id);
  IF n_orphan <> 304 THEN
    RAISE EXCEPTION 'C207 orphan census = % (expected 304 after repairing the 2 srcbuild labels)', n_orphan;
  END IF;
  RAISE NOTICE 'OK: 2 srcbuild ingest labels repointed to their spine runs; 304 orphans remain (301 definitional + 3 m235b gap)';
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- C207 note refreshed: census updated (306/4,148 -> 304/4,320), the
-- srcbuild repair recorded with its old->new mapping, everything else
-- from the 2026-07-20 adjudication retained verbatim in substance.
-- ---------------------------------------------------------------------
UPDATE provenance.check_definition
   SET note = 'KNOWN FAILING: 304 of 4,320 rows, spanning 19 distinct run_id labels (census updated 2026-07-26, schema/34; previously 306 of 4,148). THE 2026-07-19 DIAGNOSIS WAS WRONG and was corrected 2026-07-20; re-adjudicated 2026-07-26. The population is two disjoint things, neither a failed load:\n\n(1) 301 rows / 16 labels that are 100%% orphan by DEFINITION -- K20 grid 257/257, K25 sweeps 31/31, K26 costmodel 6/6, K27 ewma_cal 1/1, K28 rerun_b1 1/1, K29 eda_rates 5/5. These loaders write AGGREGATE/DERIVED artifacts into dimension tables, and their ingest_log.run_id is a logical artifact-group label, not a spine reference. Proof: the single label "grid:grid_summary" is shared by 256 distinct files, which cannot be a run identity because C301 asserts run_id -> source_path is 1:1; and eda_rate_series, the destination of the 5 K29 rows, HAS NO run_id COLUMN AT ALL. 564 ingest_log rows already carry NULL run_id for exactly this reason.\n\n(2) 3 rows of legacy kind K35 (no longer registered in loader/main.py) -- m235b:run_s1/_s4/_s16 -- replay logs of the never-ingested m235b family. REPAIRED 2026-07-26 (schema/34): the other two K35 mislabels, srcbuild:run_aic -> srcbuild:llm_head2k_aic_src and srcbuild:run_poly -> srcbuild:llm_head2k_poly_src, were repointed to their existing spine runs (the mapping C207''s own 2026-07-20 note established); K35 being unregistered, nothing can overwrite the corrected labels. The m235b three CANNOT be repointed: their family has zero spine rows.\n\nNOT WEAKENED. The check keeps failing rather than being taught to exempt kinds, because exempting by kind would narrow the population and would hide any future genuine orphan.\n\nSEPARATE REAL GAP, still open: the three m235b result files simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json exist on disk and have NEVER been ingested -- zero ingest_log rows, zero spine runs, experiment m235b absent from provenance.runs. runid.py maps /235b/ to experiment m235b, so the family is declared but unloaded. This is a coverage gap, NOT a corruption. Closing it needs a loader for that report shape (compare K40); left flagged rather than hastily half-ingested.'
 WHERE check_id = 'C207';
