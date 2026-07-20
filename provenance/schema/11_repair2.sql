-- 11_repair2.sql — Repair 2: verification run_id resolution (a) + worker_schedule
-- C-02 schedule mismatch quarantine (b). Applied 2026-07-19. Idempotent.

-- ============ (a) verification.resolved_run_id ============
BEGIN;

ALTER TABLE provenance.verification
  ADD COLUMN IF NOT EXISTS resolved_run_id text;

-- Pass 1: unambiguous — exactly one runs row whose suffix matches the bare label.
UPDATE provenance.verification v
SET resolved_run_id = (
      SELECT q.run_id FROM provenance.runs q
      WHERE split_part(q.run_id, ':', 2) = v.run_id)
WHERE (SELECT count(*) FROM provenance.runs q
       WHERE split_part(q.run_id, ':', 2) = v.run_id) = 1;

-- Pass 2: ambiguous — disambiguate by the directory of the verification.json that
-- produced the row against the directory of the run's own source artifact.
UPDATE provenance.verification v
SET resolved_run_id = (
      SELECT q.run_id FROM provenance.runs q
      WHERE split_part(q.run_id, ':', 2) = v.run_id
        AND regexp_replace(q.source_path, '/[^/]*$', '')
          = regexp_replace(v.source_path, '/[^/]*$', ''))
WHERE v.resolved_run_id IS NULL
  AND (SELECT count(*) FROM provenance.runs q
       WHERE split_part(q.run_id, ':', 2) = v.run_id
         AND regexp_replace(q.source_path, '/[^/]*$', '')
           = regexp_replace(v.source_path, '/[^/]*$', '')) = 1;

CREATE INDEX IF NOT EXISTS verification_resolved_run_id_idx
  ON provenance.verification (resolved_run_id);

COMMENT ON COLUMN provenance.verification.run_id IS
  'The artifact''s own bare label as written inside verification.json (e.g. "react_L30", '
  '"chronos"). Part of the PK; deliberately NOT rewritten. It is unprefixed and therefore '
  'does NOT join to provenance.runs.run_id — join via resolved_run_id instead.';

COMMENT ON COLUMN provenance.verification.resolved_run_id IS
  'Repair 2(a): the fully-qualified provenance.runs.run_id ("<experiment>:<label>") this row '
  'corroborates. Populated by suffix match on split_part(runs.run_id,'':'',2); the two '
  'ambiguous labels (react_L30, static_C2 -> {a6,misc}) were disambiguated by matching the '
  'directory of this row''s source_path to the directory of runs.source_path. NULL means '
  'genuinely unresolvable, not un-attempted: the a14/a15 "chronos"/"timesfm"/"toto" rows are '
  'per-model aggregates spanning the _enc/_e2e/_composed run trio (no single run to point at), '
  'and g1 "_preflight" is a trace-window/archive coverage check, not a run at all. '
  'No FK is declared: NULLs are expected and the column is an advisory join key.';

COMMENT ON TABLE provenance.verification IS
  'Independent re-derivation of headline metrics from each experiment family''s '
  'verification.json. PK is (source_path, run_id) on the artifact''s own labels; join to '
  'provenance.runs through resolved_run_id, never run_id.';

COMMIT;

BEGIN;

DROP VIEW IF EXISTS provenance.v_corroboration;
CREATE VIEW provenance.v_corroboration AS
WITH v AS (
  SELECT verification.resolved_run_id AS rid,
         verification.run_id          AS artifact_label,
         verification.source_path,
         verification.stage,
         verification.enc_p99,
         verification.ttft_p99
  FROM provenance.verification
)
SELECT v.rid AS run_id,
       v.artifact_label,
       v.source_path,
       v.stage,
       v.ttft_p99 AS verif_ttft,
       COALESCE(l.p99_ttft_ms, le.p99_ttft_ms) AS summary_ttft,
       round((abs(v.ttft_p99 - COALESCE(l.p99_ttft_ms, le.p99_ttft_ms))
              / NULLIF(COALESCE(l.p99_ttft_ms, le.p99_ttft_ms), 0::double precision)
              * 100::double precision)::numeric, 4) AS ttft_pct_diff,
       v.enc_p99 AS verif_enc,
       COALESCE(e.encoder_delay_p99_ms, ec.encoder_delay_p99_ms) AS summary_enc,
       round((abs(v.enc_p99 - COALESCE(e.encoder_delay_p99_ms, ec.encoder_delay_p99_ms))
              / NULLIF(COALESCE(e.encoder_delay_p99_ms, ec.encoder_delay_p99_ms), 0::double precision)
              * 100::double precision)::numeric, 4) AS enc_pct_diff
FROM v
LEFT JOIN provenance.llm_run_summary     l  ON l.run_id  = v.rid
LEFT JOIN provenance.llm_run_summary     le ON le.run_id = (v.rid || '_e2e')
LEFT JOIN provenance.encoder_run_summary e  ON e.run_id  = v.rid
LEFT JOIN provenance.encoder_run_summary ec ON ec.run_id = (v.rid || '_composed');

COMMENT ON VIEW provenance.v_corroboration IS
  'Cross-checks each verification.json metric against the independently-loaded run summaries. '
  'Joins on verification.resolved_run_id (Repair 2a) rather than re-deriving the prefix from '
  'source_path with a regexp — the old derivation only matched an a<N>_runs/ path pattern and '
  'silently produced non-joining ids for g-family rows. Rows with resolved_run_id NULL (7: the '
  'a14/a15 per-model aggregates and g1 _preflight) carry NULL run_id here by design and '
  'corroborate nothing.';

COMMIT;

-- ============ (b) C-02 worker_schedule quarantine ============
BEGIN;

ALTER TABLE provenance.worker_schedule
  ADD COLUMN IF NOT EXISTS is_valid       boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS invalid_reason text;

UPDATE provenance.worker_schedule
SET is_valid = false,
    invalid_reason =
      'C-02: source artifact corrupt at generation time. The *.sched.json file named for this '
      'burst1 run is byte-identical (sha256) to the same-W/L aggregate run''s schedule, and the '
      'sibling *.sched.log self-labels "aggregate". The schedule generator was invoked with the '
      'aggregate window while writing the burst1-named output, so the true burst1 schedule was '
      'never produced and cannot be recovered from disk. Span is 483660s vs this run''s own '
      'sim_horizon_s of 29939.313s (16.2x). Do NOT integrate these rows for provisioned cost.'
WHERE run_id IN (
  'misc:react_p90_W120_burst1_L30',  'misc:react_p90_W120_burst1_L300',
  'misc:react_p90_W240_burst1_L30',  'misc:react_p90_W240_burst1_L300',
  'misc:react_p90_W480_burst1_L30',  'misc:react_p90_W480_burst1_L300'
);

CREATE INDEX IF NOT EXISTS worker_schedule_is_valid_idx
  ON provenance.worker_schedule (is_valid) WHERE NOT is_valid;

COMMENT ON COLUMN provenance.worker_schedule.is_valid IS
  'FALSE marks schedule rows known to belong to a different simulation than their run_id. '
  'Repair 2b / finding C-02. Consumers integrating worker_count over t_s for provisioned cost '
  'MUST filter is_valid. Verified NOT an ingest defect: ingest_log sha256 shows the loader read '
  'exactly the file named for the run; the artifact on disk is itself wrong.';

COMMENT ON COLUMN provenance.worker_schedule.invalid_reason IS
  'Human-readable provenance of why is_valid is false; NULL when is_valid.';

COMMIT;

BEGIN;

CREATE TABLE IF NOT EXISTS provenance.artifact_quarantine (
  source_path   text PRIMARY KEY,
  kind          text,
  finding       text,
  observed_sha  text,
  reason        text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE provenance.artifact_quarantine IS
  'Registry of artifacts on disk that are known-wrong at GENERATION time (not ingest time). '
  'Keyed by source_path because the defect is a wrong file->run association: the bytes '
  'themselves are a legitimate artifact of some OTHER run, so sha256 alone cannot identify '
  'the bad row. Loaders wipe per-row validity flags on re-ingest (load_worker_schedule '
  'deletes by source_path and re-COPYs), so run provenance.apply_artifact_quarantine() after '
  'any ingest to re-assert these flags. observed_sha records the bytes seen when quarantined: '
  'if the artifact is ever regenerated correctly its sha will differ, which is the signal to '
  'retire the entry.';

INSERT INTO provenance.artifact_quarantine (source_path, kind, finding, observed_sha, reason)
SELECT il.file_path, 'K4', 'C-02', il.sha256,
       'Schedule belongs to the same-W/L *aggregate* run, not this burst1 run. The file is '
       'byte-identical (sha256) to react_p90_W<W>_aggregate_L<L>.sched.json and the sibling '
       '*.sched.log self-labels "aggregate [...]". Schedule span 483660s vs this run''s own '
       'sim_horizon_s 29939.313s (16.15x). The true burst1 schedule was never generated and '
       'is unrecoverable from disk; regenerate the simulation to fix. NOTE: this run''s stored '
       'provisioned_worker_seconds is CORRECT (it comes from *.jsonl.stats.json); only the '
       'worker_schedule time series is foreign.'
FROM provenance.ingest_log il
WHERE il.run_id IN (
  'misc:react_p90_W120_burst1_L30',  'misc:react_p90_W120_burst1_L300',
  'misc:react_p90_W240_burst1_L30',  'misc:react_p90_W240_burst1_L300',
  'misc:react_p90_W480_burst1_L30',  'misc:react_p90_W480_burst1_L300')
  AND il.kind = 'K4'
ON CONFLICT (source_path) DO NOTHING;

CREATE OR REPLACE FUNCTION provenance.apply_artifact_quarantine()
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE n integer;
BEGIN
  UPDATE provenance.worker_schedule w
  SET is_valid = false, invalid_reason = q.finding || ': ' || q.reason
  FROM provenance.artifact_quarantine q
  WHERE q.source_path = w.source_path AND q.kind = 'K4'
    AND (w.is_valid OR w.invalid_reason IS DISTINCT FROM q.finding || ': ' || q.reason);
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

COMMENT ON FUNCTION provenance.apply_artifact_quarantine() IS
  'Re-asserts provenance.artifact_quarantine onto per-row validity flags. Idempotent. MUST be '
  'called after any loader run that could have re-ingested a quarantined source_path, because '
  'the loaders COPY without the flag columns and thus reset them to the default.';

COMMIT;

BEGIN;

DROP VIEW IF EXISTS provenance.v_worker_schedule_integrity;
CREATE VIEW provenance.v_worker_schedule_integrity AS
WITH e AS (
  SELECT run_id,
         provisioned_worker_seconds AS pws,
         (metrics ->> 'sim_horizon_s')::double precision AS sim_horizon_s
  FROM provenance.encoder_run_summary
  WHERE provisioned_worker_seconds IS NOT NULL
), s AS (
  SELECT w.run_id, w.t_s, w.worker_count, w.is_valid,
         COALESCE(lead(w.t_s) OVER (PARTITION BY w.run_id ORDER BY w.step_index),
                  e_1.sim_horizon_s) AS t_next
  FROM provenance.worker_schedule w
  JOIN e e_1 ON e_1.run_id = w.run_id
), i AS (
  SELECT s.run_id,
         sum(s.worker_count::double precision
             * GREATEST(s.t_next - s.t_s, 0::double precision)) AS integrated_ws,
         count(*) AS n_schedule_rows,
         bool_and(s.is_valid) AS schedule_valid,
         max(s.t_next) AS schedule_span_s
  FROM s GROUP BY s.run_id
)
SELECT i.run_id,
       i.n_schedule_rows,
       i.schedule_valid,
       e.sim_horizon_s,
       i.schedule_span_s,
       i.integrated_ws,
       e.pws AS stored_provisioned_ws,
       i.integrated_ws / NULLIF(e.pws, 0::double precision) AS ratio,
       (abs(i.integrated_ws - e.pws) / NULLIF(e.pws, 0::double precision)) > 0.01::double precision
         AS schedule_mismatch,
       (abs(i.integrated_ws - e.pws) / NULLIF(e.pws, 0::double precision)) > 0.01::double precision
         AND i.schedule_valid AS unexplained_mismatch
FROM i JOIN e USING (run_id);

COMMENT ON VIEW provenance.v_worker_schedule_integrity IS
  'Reconciles the worker_schedule step function against each run''s stored '
  'provisioned_worker_seconds. schedule_mismatch is the raw >1%% numeric test and is left '
  'intact (nothing is hidden); unexplained_mismatch additionally requires schedule_valid, so '
  'the six known-corrupt misc:react_p90_W*_burst1_L* schedules (finding C-02, see '
  'worker_schedule.invalid_reason) drop out and any NEW divergence still surfaces. Note the '
  'stored_provisioned_ws for those six is itself CORRECT — it comes from the run''s own '
  '*.jsonl.stats.json, not from the schedule; only the schedule time series is foreign.';

COMMIT;
