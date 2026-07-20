-- Lineage / drift checks: recompute a projected number from the RAW rows of the same run
-- and compare to the stored summary. This is the "is a chapter number still consistent with
-- its artifact?" audit the thesis wanted (stale-number-drift detector). Near-zero pct_diff
-- proves the projection is faithfully derived from raw.
SET search_path = provenance, public;

-- p99 TTFT recomputed from provenance.llm_request (raw) vs provenance.llm_run_summary (projection)
DROP MATERIALIZED VIEW IF EXISTS provenance.mv_llm_p99_check CASCADE;
CREATE MATERIALIZED VIEW provenance.mv_llm_p99_check AS
    SELECT q.run_id,
           s.p99_ttft_ms                            AS summary_p99_ttft_ms,
           q.raw_p99_ttft_ms,
           s.p99_itl_ms                             AS summary_p99_itl_ms,
           q.raw_p99_itl_ms,
           q.n_raw,
           s.completed_requests                     AS summary_completed
    FROM (SELECT run_id,
                 percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS raw_p99_ttft_ms,
                 percentile_cont(0.99) WITHIN GROUP (ORDER BY itl_ms)  AS raw_p99_itl_ms,
                 count(*) AS n_raw
          FROM provenance.llm_request GROUP BY run_id) q
    JOIN provenance.llm_run_summary s USING (run_id);

-- convenience view: percentage disagreement (should be ~0 for every run).
-- TTFT is one value per request in both raw and summary => a clean equality check.
-- ITL p99 is token-pooled in the summary but request-mean in raw llm_request, so it is
-- NOT directly comparable and is intentionally omitted from the drift comparison.
CREATE OR REPLACE VIEW provenance.v_llm_drift AS
    SELECT run_id,
           summary_p99_ttft_ms,
           round(raw_p99_ttft_ms::numeric, 3) AS raw_p99_ttft_ms,
           round((abs(summary_p99_ttft_ms - raw_p99_ttft_ms)
                  / nullif(summary_p99_ttft_ms, 0) * 100)::numeric, 4) AS ttft_pct_diff,
           n_raw, summary_completed,
           (n_raw = summary_completed) AS rowcount_matches
    FROM provenance.mv_llm_p99_check
    ORDER BY ttft_pct_diff DESC NULLS LAST;

COMMENT ON VIEW provenance.v_llm_drift IS
  'Lineage audit: p99 TTFT recomputed from raw llm_request vs stored llm_run_summary. ttft_pct_diff ~0 (percentile-interpolation noise) and rowcount_matches=true prove the projection is faithfully derived from raw. ITL omitted (summary=token-pooled vs raw=request-mean, not comparable).';

-- REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;  -- rerun after (re)loading K1/K2
