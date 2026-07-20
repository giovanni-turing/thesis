-- =====================================================================
-- 21_checks.sql -- BUILD 2: correctness functions + consistency constraints
-- =====================================================================
-- Schema: provenance (PostgreSQL 16)
--
-- PART A  provenance.check_definition / check_all() / check_run() /
--         recompute_p99()  -- the audit's one-off identity probes turned
--         into a persistent, re-runnable regression suite.
-- PART B  CHECK constraints + vocabulary domains + UNIQUE constraints,
--         every one of them VERIFIED against the live data before being
--         written here.  Nothing asserted that the data violates.
--
-- SAFE TO RUN DURING INGEST.  Deliberately absent (they would slow the
-- remaining a16 / g2 / g3_32b / g6 loads and live in 99_readonly_optimization.sql):
--   * FOREIGN KEYs on the partitioned raw facts (llm_request,
--     composed_request, encoder_series, forecast, worker_schedule)
--   * triggers of any kind
--   * VALIDATE of the NOT VALID constraints created below
--   * every non-trivial index
--
-- All CHECK constraints on the huge partitioned tables are created
-- NOT VALID: catalog-only, instant, ACCESS EXCLUSIVE for milliseconds,
-- enforced for every NEW row from now on, validated later in 99_.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;

-- =====================================================================
-- PART A -- THE CORRECTNESS TEST SUITE
-- =====================================================================

-- ---------------------------------------------------------------------
-- A.1  The registry.
--
-- CONTRACT for sql_text: it MUST return exactly one row with exactly two
-- columns, in this order:
--     passed  boolean   -- true iff the identity holds
--     detail  text      -- human-readable evidence, pass or fail
-- check_all() enforces the shape; anything else is reported as an error
-- rather than a pass, so a malformed probe can never look green.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.check_definition (
    check_id    text PRIMARY KEY,
    title       text        NOT NULL,
    severity    text        NOT NULL
                            CHECK (severity IN ('error','warn','info')),
    sql_text    text        NOT NULL,
    expected    text        NOT NULL,
    is_enabled  boolean     NOT NULL DEFAULT true,
    est_cost    text        NOT NULL DEFAULT 'cheap'
                            CHECK (est_cost IN ('cheap','moderate','expensive')),
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE provenance.check_definition IS
  'Registry of recomputable correctness identities. Each sql_text returns one row '
  '(passed boolean, detail text). Run them all with provenance.check_all(). '
  'severity: error = a published number is at risk; warn = known bounded discrepancy, '
  'documented in note; info = descriptive census, never fails on its own.';
COMMENT ON COLUMN provenance.check_definition.expected IS
  'Prose statement of the invariant, so the intent survives even if sql_text is rewritten.';
COMMENT ON COLUMN provenance.check_definition.est_cost IS
  'cheap = projection-only; moderate = seconds over a raw fact table; '
  'expensive = full scan of a 15-35M row partitioned table. check_all(p_max_cost) gates on this.';

-- ---------------------------------------------------------------------
-- A.2  check_all() -- execute the whole suite, report honestly.
--
-- A probe that raises is reported passed = false with the SQLERRM in
-- detail. It is never silently skipped.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION provenance.check_all(
    p_severity  text DEFAULT NULL,   -- NULL = all; else 'error' / 'warn' / 'info'
    p_max_cost  text DEFAULT 'expensive',
    p_prefix    text DEFAULT NULL    -- e.g. 'C0' to run one block
)
RETURNS TABLE (check_id text, title text, severity text, passed boolean, detail text)
LANGUAGE plpgsql
STABLE
AS $fn$
DECLARE
    d           provenance.check_definition%ROWTYPE;
    v_passed    boolean;
    v_detail    text;
    v_rank      int;
    v_max_rank  int := CASE p_max_cost WHEN 'cheap' THEN 1 WHEN 'moderate' THEN 2 ELSE 3 END;
BEGIN
    FOR d IN
        SELECT * FROM provenance.check_definition
         WHERE is_enabled
           AND (p_severity IS NULL OR check_definition.severity = p_severity)
           AND (p_prefix   IS NULL OR check_definition.check_id LIKE p_prefix || '%')
         ORDER BY check_definition.check_id
    LOOP
        v_rank := CASE d.est_cost WHEN 'cheap' THEN 1 WHEN 'moderate' THEN 2 ELSE 3 END;
        IF v_rank > v_max_rank THEN
            CONTINUE;
        END IF;

        BEGIN
            EXECUTE d.sql_text INTO STRICT v_passed, v_detail;
            IF v_passed IS NULL THEN
                v_passed := false;
                v_detail := 'probe returned NULL for passed; detail=' || coalesce(v_detail,'<null>');
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_passed := false;
            v_detail := 'PROBE ERROR: ' || SQLERRM;
        END;

        check_id := d.check_id;
        title    := d.title;
        severity := d.severity;
        passed   := v_passed;
        detail   := v_detail;
        RETURN NEXT;
    END LOOP;
END;
$fn$;

COMMENT ON FUNCTION provenance.check_all(text,text,text) IS
  'Run the registered correctness identities. A probe that errors is reported as '
  'passed=false with the SQLERRM, never skipped. p_max_cost caps how much scanning '
  'is allowed (cheap|moderate|expensive).';

-- Convenience: just the failures.
CREATE OR REPLACE FUNCTION provenance.check_failures(p_max_cost text DEFAULT 'expensive')
RETURNS TABLE (check_id text, title text, severity text, detail text)
LANGUAGE sql STABLE AS $fn$
    SELECT c.check_id, c.title, c.severity, c.detail
      FROM provenance.check_all(NULL, p_max_cost) c
     WHERE NOT c.passed;
$fn$;

-- ---------------------------------------------------------------------
-- A.3  check_run(run_id) -- does ONE run's summary recompute from ITS
--      OWN raw rows?  This is the per-run lineage answer: point it at
--      any run_id and it re-derives every summary field that has raw
--      backing and reports the delta.
--
--      Returns one row per recomputed quantity.  A run with no raw rows
--      returns a single explanatory row rather than silently nothing.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION provenance.check_run(p_run_id text)
RETURNS TABLE (
    aspect      text,
    stored      double precision,
    recomputed  double precision,
    abs_diff    double precision,
    rel_diff    double precision,
    tolerance   double precision,
    passed      boolean,
    source      text
)
LANGUAGE plpgsql STABLE AS $fn$
DECLARE
    v_has_llm  boolean;
    v_has_comp boolean;
    v_has_enc  boolean;
    v_has_sch  boolean;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = p_run_id) THEN
        RETURN QUERY SELECT 'run_exists'::text, NULL::double precision, NULL::double precision,
                            NULL::double precision, NULL::double precision, NULL::double precision,
                            false, 'provenance.runs'::text;
        RETURN;
    END IF;

    SELECT EXISTS (SELECT 1 FROM provenance.llm_request      x WHERE x.run_id = p_run_id) INTO v_has_llm;
    SELECT EXISTS (SELECT 1 FROM provenance.composed_request x WHERE x.run_id = p_run_id) INTO v_has_comp;
    SELECT EXISTS (SELECT 1 FROM provenance.encoder_series   x WHERE x.run_id = p_run_id) INTO v_has_enc;
    SELECT EXISTS (SELECT 1 FROM provenance.worker_schedule  x WHERE x.run_id = p_run_id) INTO v_has_sch;

    -- ---- language pool: counts + percentiles from llm_request --------
    IF v_has_llm THEN
        RETURN QUERY
        WITH raw AS (
            SELECT count(*)::double precision AS n,
                   percentile_cont(0.50) WITHIN GROUP (ORDER BY ttft_ms) AS p50,
                   percentile_cont(0.90) WITHIN GROUP (ORDER BY ttft_ms) AS p90,
                   percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS p99,
                   max(ttft_ms)                                          AS mx,
                   avg(ttft_ms)                                          AS mean,
                   percentile_cont(0.99) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e99,
                   percentile_cont(0.99) WITHIN GROUP (ORDER BY itl_ms)         AS itl99
              FROM provenance.llm_request WHERE run_id = p_run_id
        ), s AS (SELECT * FROM provenance.llm_run_summary WHERE run_id = p_run_id)
        SELECT v.aspect, v.stored, v.rec,
               abs(v.stored - v.rec),
               abs(v.stored - v.rec) / greatest(abs(v.rec), 1e-9),
               v.tol,
               abs(v.stored - v.rec) <= v.tol * greatest(abs(v.rec), 1e-9),
               'llm_request'::text
          FROM s, raw,
               LATERAL (VALUES
                 -- tolerances MUST be double precision: a bare 0.0 / 1e-3 literal
                 -- is numeric, and the VALUES list then types the whole `tol`
                 -- column numeric, which fails RETURNS TABLE (... double precision).
                 ('completed_requests', s.completed_requests::double precision, raw.n,     0.0::double precision),
                 ('mean_ttft_ms',       s.mean_ttft_ms,       raw.mean,  1e-3::double precision),
                 ('median_ttft_ms',     s.median_ttft_ms,     raw.p50,   1e-3::double precision),
                 ('p90_ttft_ms',        s.p90_ttft_ms,        raw.p90,   5e-3::double precision),
                 ('p99_ttft_ms',        s.p99_ttft_ms,        raw.p99,   2e-2::double precision),
                 ('max_ttft_ms',        s.max_ttft_ms,        raw.mx,    1e-6::double precision),
                 ('p99_e2e_latency_ms', s.p99_e2e_latency_ms, raw.e2e99, 2e-2::double precision),
                 ('p99_itl_ms',         s.p99_itl_ms,         raw.itl99, 2e-2::double precision)
               ) AS v(aspect, stored, rec, tol)
         WHERE v.stored IS NOT NULL AND v.rec IS NOT NULL;
    END IF;

    -- ---- encoder pool: request count from composed_request ------------
    IF v_has_comp THEN
        RETURN QUERY
        SELECT 'encoder_requests'::text,
               e.requests::double precision, c.n::double precision,
               abs(e.requests - c.n)::double precision, 0::double precision, 0::double precision,
               e.requests = c.n, 'composed_request'::text
          FROM provenance.encoder_run_summary e,
               LATERAL (SELECT count(*) n FROM provenance.composed_request x WHERE x.run_id = p_run_id) c
         WHERE e.run_id = p_run_id;
    END IF;

    -- ---- encoder pool: worker-seconds integral -------------------------
    --  SUM(worker_count * dt), last step extended to the simulation
    --  horizon taken from max(encoder_series.t).
    IF v_has_sch AND v_has_enc THEN
        RETURN QUERY
        WITH h AS (SELECT max(t)::double precision AS horizon
                     FROM provenance.encoder_series WHERE run_id = p_run_id),
             sch AS (SELECT t_s, worker_count,
                            lead(t_s) OVER (ORDER BY step_index) AS t_next
                       FROM provenance.worker_schedule
                      WHERE run_id = p_run_id AND is_valid IS NOT FALSE),
             integ AS (SELECT sum(worker_count * (coalesce(t_next, h.horizon) - t_s)) AS ws
                         FROM sch, h)
        SELECT 'provisioned_worker_seconds'::text,
               e.provisioned_worker_seconds, integ.ws,
               abs(e.provisioned_worker_seconds - integ.ws),
               abs(e.provisioned_worker_seconds - integ.ws) / greatest(e.provisioned_worker_seconds, 1e-9),
               1e-3::double precision,
               abs(e.provisioned_worker_seconds - integ.ws)
                   <= 1e-3 * greatest(e.provisioned_worker_seconds, 1e-9),
               'worker_schedule x encoder_series'::text
          FROM provenance.encoder_run_summary e, integ
         WHERE e.run_id = p_run_id AND e.provisioned_worker_seconds IS NOT NULL;
    END IF;

    -- ---- nothing to recompute -----------------------------------------
    IF NOT (v_has_llm OR v_has_comp OR (v_has_sch AND v_has_enc)) THEN
        RETURN QUERY SELECT 'no_raw_backing'::text, NULL::double precision, NULL::double precision,
                            NULL::double precision, NULL::double precision, NULL::double precision,
                            false,
                            'run exists in provenance.runs but has no rows in llm_request, '
                            'composed_request or worker_schedule+encoder_series'::text;
    END IF;
END;
$fn$;

COMMENT ON FUNCTION provenance.check_run(text) IS
  'Per-run lineage: re-derive every summary quantity that has raw backing, from that '
  'run''s own raw rows, and report stored vs recomputed with an explicit tolerance. '
  'Tolerances are empirical: exact for counts and max, 1e-3 relative for mean/median, '
  '2e-2 for tail percentiles (numpy linear-interpolation vs percentile_cont diverge in '
  'the sparse tail), 1e-3 for the worker-seconds integral.';

-- ---------------------------------------------------------------------
-- A.4  recompute_p99(run_id, metric) -- lineage on demand.
--      The single function an analyst calls to re-derive a published
--      tail number straight from the raw rows.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION provenance.recompute_p99(p_run_id text, p_metric text)
RETURNS TABLE (run_id text, metric text, q double precision, n bigint,
               value double precision, stored double precision, source_table text)
LANGUAGE plpgsql STABLE AS $fn$
BEGIN
    RETURN QUERY SELECT * FROM provenance.recompute_quantile(p_run_id, p_metric, 0.99);
END;
$fn$;

CREATE OR REPLACE FUNCTION provenance.recompute_quantile(
    p_run_id text, p_metric text, p_q double precision DEFAULT 0.99)
RETURNS TABLE (run_id text, metric text, q double precision, n bigint,
               value double precision, stored double precision, source_table text)
LANGUAGE plpgsql STABLE AS $fn$
BEGIN
    CASE lower(p_metric)
      -- ---- language pool (llm_request) --------------------------------
      WHEN 'ttft', 'ttft_ms' THEN
        RETURN QUERY
        SELECT p_run_id, 'ttft_ms'::text, p_q, count(*)::bigint,
               percentile_cont(p_q) WITHIN GROUP (ORDER BY x.ttft_ms),
               (SELECT CASE WHEN p_q = 0.99 THEN s.p99_ttft_ms
                            WHEN p_q = 0.95 THEN s.p95_ttft_ms
                            WHEN p_q = 0.90 THEN s.p90_ttft_ms
                            WHEN p_q = 0.50 THEN s.median_ttft_ms END
                  FROM provenance.llm_run_summary s WHERE s.run_id = p_run_id),
               'llm_request'::text
          FROM provenance.llm_request x WHERE x.run_id = p_run_id;

      WHEN 'e2e', 'e2e_latency_ms' THEN
        RETURN QUERY
        SELECT p_run_id, 'e2e_latency_ms'::text, p_q, count(*)::bigint,
               percentile_cont(p_q) WITHIN GROUP (ORDER BY x.e2e_latency_ms),
               (SELECT CASE WHEN p_q = 0.99 THEN s.p99_e2e_latency_ms
                            WHEN p_q = 0.90 THEN s.p90_e2e_latency_ms END
                  FROM provenance.llm_run_summary s WHERE s.run_id = p_run_id),
               'llm_request'::text
          FROM provenance.llm_request x WHERE x.run_id = p_run_id;

      WHEN 'itl', 'itl_ms' THEN
        RETURN QUERY
        SELECT p_run_id, 'itl_ms'::text, p_q, count(*)::bigint,
               percentile_cont(p_q) WITHIN GROUP (ORDER BY x.itl_ms),
               (SELECT CASE WHEN p_q = 0.99 THEN s.p99_itl_ms END
                  FROM provenance.llm_run_summary s WHERE s.run_id = p_run_id),
               'llm_request'::text
          FROM provenance.llm_request x WHERE x.run_id = p_run_id;

      WHEN 'ttst', 'ttst_ms' THEN
        RETURN QUERY
        SELECT p_run_id, 'ttst_ms'::text, p_q, count(*)::bigint,
               percentile_cont(p_q) WITHIN GROUP (ORDER BY x.ttst_ms),
               (SELECT CASE WHEN p_q = 0.99 THEN s.p99_ttst_ms END
                  FROM provenance.llm_run_summary s WHERE s.run_id = p_run_id),
               'llm_request'::text
          FROM provenance.llm_request x WHERE x.run_id = p_run_id;

      -- ---- measured vLLM ETL ------------------------------------------
      WHEN 'vllm_itl', 'token_itl' THEN
        RETURN QUERY
        SELECT p_run_id, 'vllm_token_itl.itl_ms'::text, p_q, count(*)::bigint,
               percentile_cont(p_q) WITHIN GROUP (ORDER BY x.itl_ms),
               NULL::double precision, 'vllm_token_itl'::text
          FROM provenance.vllm_token_itl x WHERE x.run_id = p_run_id;

      ELSE
        RAISE EXCEPTION
          'recompute_quantile: unknown metric %. Known: ttft_ms, e2e_latency_ms, itl_ms, ttst_ms, vllm_itl',
          p_metric;
    END CASE;
END;
$fn$;

COMMENT ON FUNCTION provenance.recompute_p99(text,text) IS
  'Lineage on demand: re-derive a published p99 for one run directly from the raw '
  'per-request rows, alongside the stored value. Thin wrapper over recompute_quantile().';
COMMENT ON FUNCTION provenance.recompute_quantile(text,text,double precision) IS
  'Generalised recompute_p99: any quantile, metrics ttft_ms | e2e_latency_ms | itl_ms | '
  'ttst_ms | vllm_itl. Uses percentile_cont, which interpolates linearly and therefore '
  'may differ from a numpy-computed stored value by up to ~1%% in a sparse tail.';

-- =====================================================================
-- A.5  SEED THE SUITE
--      Every identity from the audit.  Each sql_text was executed against
--      the live store while writing this file; the observed result is
--      recorded in note so a future divergence is legible as a change.
-- =====================================================================
DELETE FROM provenance.check_definition;

INSERT INTO provenance.check_definition (check_id, title, severity, est_cost, expected, note, sql_text) VALUES

-- ---------------------------------------------------------------------
-- C0xx -- PROJECTION vs RAW: does the summary recompute from the facts?
-- ---------------------------------------------------------------------
('C001', 'llm_run_summary.completed_requests = count(llm_request)', 'error', 'moderate',
 'Zero runs where the stored completed_requests disagrees with the raw row count.',
 'Observed 0 mismatches over the runs that have raw backing (audit lens C: 101/101 exact).',
$$SELECT count(*) FILTER (WHERE bad) = 0,
         format('%s runs with completed_requests <> count(llm_request); %s runs compared',
                count(*) FILTER (WHERE bad), count(*))
    FROM (SELECT s.completed_requests <> r.n AS bad
            FROM provenance.llm_run_summary s
            JOIN (SELECT run_id, count(*) n FROM provenance.llm_request GROUP BY 1) r
              USING (run_id)) q$$),

('C002', 'llm_run_summary.median_ttft_ms reproduces percentile_cont(0.5)', 'error', 'moderate',
 'Stored median TTFT matches the raw percentile to 1e-3 relative for every backed run.',
 'Observed 0 failures at 1e-3 relative. 18 runs differ at >1e-6 absolute (max 0.011 ms on a '
 '~26 ms median) -- numpy linear interpolation vs percentile_cont, not a data error.',
$$SELECT count(*) FILTER (WHERE bad) = 0,
         format('%s of %s backed runs exceed 1e-3 relative on median_ttft_ms',
                count(*) FILTER (WHERE bad), count(*))
    FROM (SELECT abs(s.median_ttft_ms - r.m) > 1e-3 * greatest(abs(r.m), 1e-9) AS bad
            FROM provenance.llm_run_summary s
            JOIN (SELECT run_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY ttft_ms) m
                    FROM provenance.llm_request GROUP BY 1) r USING (run_id)
           WHERE s.median_ttft_ms IS NOT NULL) q$$),

('C003', 'llm_run_summary.p99_ttft_ms reproduces percentile_cont(0.99)', 'warn', 'moderate',
 'Stored p99 TTFT matches the raw percentile to 2e-2 relative for every backed run.',
 'Observed 0 failures at 2e-2. 14 runs exceed 1e-3 relative, worst 1.22%% (reactive:iter1). '
 'This is the interpolation convention diverging in a sparse tail, NOT drift -- but the '
 'tolerance is loose enough that this check cannot detect a small real error. Treated as warn.',
$$SELECT count(*) FILTER (WHERE bad) = 0,
         format('%s of %s backed runs exceed 2e-2 relative on p99_ttft_ms (worst %s)',
                count(*) FILTER (WHERE bad), count(*), coalesce(max(rel)::text,'n/a'))
    FROM (SELECT abs(s.p99_ttft_ms - r.m) / greatest(abs(r.m),1e-9) AS rel,
                 abs(s.p99_ttft_ms - r.m) > 2e-2 * greatest(abs(r.m), 1e-9) AS bad
            FROM provenance.llm_run_summary s
            JOIN (SELECT run_id, percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms) m
                    FROM provenance.llm_request GROUP BY 1) r USING (run_id)
           WHERE s.p99_ttft_ms IS NOT NULL) q$$),

('C004', 'encoder_run_summary.requests = count(composed_request)', 'error', 'moderate',
 'Zero runs where the stored encoder request count disagrees with the raw row count.',
 'Observed 0 mismatches (audit lens C: 366/366 exact).',
$$SELECT count(*) FILTER (WHERE bad) = 0,
         format('%s of %s backed runs mismatch on encoder_run_summary.requests',
                count(*) FILTER (WHERE bad), count(*))
    FROM (SELECT s.requests <> r.n AS bad
            FROM provenance.encoder_run_summary s
            JOIN (SELECT run_id, count(*) n FROM provenance.composed_request GROUP BY 1) r
              USING (run_id)) q$$),

('C005', 'provisioned_worker_seconds = integral of the worker schedule', 'error', 'moderate',
 'For every run with both a schedule and a series, SUM(worker_count*dt) with the last step '
 'extended to the run''s exact simulated horizon reproduces provisioned_worker_seconds to '
 '1e-3 relative.',
 'PASSES as of 2026-07-20 (444/444 joinable runs at time of writing). Two corrections, neither '
 'of which loosens the assertion. (1) HORIZON: the check used max(encoder_series.t) to close the '
 'last schedule step, but encoder_series.t is an INTEGER second-bin index, so that proxy floors '
 'the true horizon by up to 1 s. Where the final step carries the run''s peak worker count the '
 'truncation is material: a2x:e17_reactive_L165 ends with 32 workers, and the missing 0.773 s '
 'cost 24.7 worker-seconds (stored 20684.3 vs recomputed 20659.57, rel 1.20e-3) -- the sole '
 'prior failure. The exact horizon is carried per run in '
 'encoder_run_summary.metrics->>''sim_horizon_s'' (1619.773 for that run); the check now uses it '
 'and falls back to max(encoder_series.t) only if absent. The DATA was right and the CHECK was '
 'wrong: the stored scalar comes from each run''s own stats.json. Tolerance is UNCHANGED at '
 '1e-3; the fix made the check STRICTER, dropping max relative error over the then-212-run '
 'population from 1.20e-3 to 6.83e-4 (median absolute residual 0.034 worker-seconds, consistent '
 'with the stored scalar being rounded to 0.1). Tolerance was NOT tightened below 1e-3 because a '
 'few runs still carry absolute residuals up to 10.1 worker-seconds not explained by rounding '
 'alone and not yet traced. (2) QUARANTINE: schedule rows are filtered on is_valid IS NOT FALSE. '
 'Six runs -- the misc:react_p90_W{120,240,480}_{burst1,burst3} family -- had a worker_schedule '
 'series copied from a DIFFERENT, ~16x longer simulation; 9,177 rows carry is_valid=false with '
 'invalid_reason set and the artifacts are recorded with sha256 evidence in '
 'provenance.artifact_quarantine. Their stored provisioned_worker_seconds is CORRECT (own '
 'stats.json); only the re-integration of the foreign schedule was wrong, so excluding those '
 'rows is the honest fix rather than pretending the integral matches. Evidence: '
 'provenance.artifact_quarantine.',
$$WITH sch AS (
      SELECT run_id, t_s, worker_count,
             lead(t_s) OVER (PARTITION BY run_id ORDER BY step_index) AS t_next
        FROM provenance.worker_schedule WHERE is_valid IS NOT FALSE),
   hor AS (SELECT run_id,
                  coalesce((metrics->>'sim_horizon_s')::double precision,
                           (SELECT max(t)::double precision
                              FROM provenance.encoder_series s WHERE s.run_id = e.run_id)) AS h
             FROM provenance.encoder_run_summary e),
   integ AS (SELECT s.run_id, sum(s.worker_count * (coalesce(s.t_next, h.h) - s.t_s)) AS ws
               FROM sch s JOIN hor h USING (run_id)
              WHERE h.h IS NOT NULL GROUP BY 1)
   SELECT count(*) FILTER (WHERE bad) = 0,
          format('%s of %s runs exceed 1e-3 relative on the worker-seconds integral: %s',
                 count(*) FILTER (WHERE bad), count(*),
                 coalesce(string_agg(run_id, ', ') FILTER (WHERE bad), 'none'))
     FROM (SELECT e.run_id,
                  abs(e.provisioned_worker_seconds - i.ws)
                      > 1e-3 * greatest(e.provisioned_worker_seconds, 1e-9) AS bad
             FROM provenance.encoder_run_summary e JOIN integ i USING (run_id)
            WHERE e.provisioned_worker_seconds IS NOT NULL) q$$),

('C006', 'forecast_metrics WAPE/MAE/RMSE recompute from raw forecast (headline scope)', 'error', 'expensive',
 'For span=full, candidates point/p50/p90, h in (1,4,12): WAPE, MAE and (where stored) RMSE '
 'recompute from provenance.forecast to 1e-6 relative for all 6 models.',
 'Observed 1080/1080 on WAPE and MAE; RMSE is stored NULL for 1760 of 2080 rows per candidate '
 'by design, so the RMSE arm only asserts over the non-NULL rows and passes there. ~5 s.',
$$WITH un AS (
      SELECT model, coalesce(mode,'~') md, variate, resolution, h, y_true, c.candidate, c.yhat
        FROM provenance.forecast f
        CROSS JOIN LATERAL (VALUES ('point',f.point),('p50',f.p50),('p90',f.p90)) c(candidate,yhat)
       WHERE f.h IN (1,4,12) AND c.yhat IS NOT NULL),
   rc AS (SELECT model, md, variate, resolution, h, candidate,
                 sum(abs(y_true-yhat))/nullif(sum(abs(y_true)),0) AS wape,
                 avg(abs(y_true-yhat))                            AS mae,
                 sqrt(avg((y_true-yhat)^2))                       AS rmse
            FROM un GROUP BY 1,2,3,4,5,6)
   SELECT count(*) FILTER (WHERE bad) = 0,
          format('%s of %s (model,variate,resolution,h,candidate) cells disagree beyond 1e-6 relative',
                 count(*) FILTER (WHERE bad), count(*))
     FROM (SELECT NOT (
                    abs(m.wape - rc.wape) <= 1e-6 * greatest(abs(rc.wape), 1e-9)
                AND abs(m.mae  - rc.mae ) <= 1e-6 * greatest(abs(rc.mae ), 1e-9)
                AND (m.rmse IS NULL OR
                     abs(m.rmse - rc.rmse) <= 1e-6 * greatest(abs(rc.rmse), 1e-9))
                  ) AS bad
             FROM provenance.forecast_metrics m
             JOIN rc ON rc.model = m.model AND rc.md = coalesce(m.mode,'~')
                    AND rc.variate = m.variate AND rc.resolution = m.resolution
                    AND rc.h = m.h AND rc.candidate = m.candidate
            WHERE m.span = 'full') q$$),

('C007', 'forecast_metrics WAPE/MAE recompute -- all 10 candidates, span=full', 'error', 'expensive',
 'The headline identity widened to every stored quantile candidate p10..p90 and every horizon.',
 'Observed 14400/14400 on WAPE and MAE. ~60 s (unpivots 16.7M forecast rows ten ways); '
 'disabled by default -- enable when you want the exhaustive proof.',
$$WITH un AS (
      SELECT model, coalesce(mode,'~') md, variate, resolution, h, y_true, c.candidate, c.yhat
        FROM provenance.forecast f
        CROSS JOIN LATERAL (VALUES ('point',f.point),('p10',f.p10),('p20',f.p20),('p30',f.p30),
                                   ('p40',f.p40),('p50',f.p50),('p60',f.p60),('p70',f.p70),
                                   ('p80',f.p80),('p90',f.p90)) c(candidate,yhat)
       WHERE c.yhat IS NOT NULL),
   rc AS (SELECT model, md, variate, resolution, h, candidate,
                 sum(abs(y_true-yhat))/nullif(sum(abs(y_true)),0) AS wape,
                 avg(abs(y_true-yhat))                            AS mae
            FROM un GROUP BY 1,2,3,4,5,6)
   SELECT count(*) FILTER (WHERE bad) = 0,
          format('%s of %s span=full cells disagree beyond 1e-6 relative on WAPE or MAE',
                 count(*) FILTER (WHERE bad), count(*))
     FROM (SELECT NOT (abs(m.wape - rc.wape) <= 1e-6 * greatest(abs(rc.wape), 1e-9)
                   AND abs(m.mae  - rc.mae ) <= 1e-6 * greatest(abs(rc.mae ), 1e-9)) AS bad
             FROM provenance.forecast_metrics m
             JOIN rc ON rc.model = m.model AND rc.md = coalesce(m.mode,'~')
                    AND rc.variate = m.variate AND rc.resolution = m.resolution
                    AND rc.h = m.h AND rc.candidate = m.candidate
            WHERE m.span = 'full' AND m.h >= 0) q$$),

('C008', 'eda_metric reproduces from eda_rate_series at 1s', 'error', 'moderate',
 'mean / max / p99 / cv2 in q_multires_tails.multi_resolution.1s.* recompute exactly from '
 'the 604,800-point 1 s rate series, for all four signals.',
 'Observed 16/16 exact. cv2 must use the POPULATION variance (var_pop); the sample variance '
 'disagrees in the 7th significant figure.',
$$WITH rc AS (
      SELECT signal, avg(value) AS mean, max(value) AS max,
             percentile_cont(0.99) WITHIN GROUP (ORDER BY value) AS p99,
             var_pop(value)/nullif(avg(value),0)^2 AS cv2
        FROM provenance.eda_rate_series WHERE resolution = '1s' GROUP BY 1)
   SELECT count(*) FILTER (WHERE bad) = 0,
          format('%s of %s eda 1s statistics disagree beyond 1e-6 relative',
                 count(*) FILTER (WHERE bad), count(*))
     FROM (SELECT abs(m.value_num - v.rec) > 1e-6 * greatest(abs(v.rec), 1e-9) AS bad
             FROM provenance.eda_metric m JOIN rc USING (signal)
             CROSS JOIN LATERAL (SELECT CASE m.stat WHEN 'mean' THEN rc.mean
                                                    WHEN 'max'  THEN rc.max
                                                    WHEN 'p99'  THEN rc.p99
                                                    WHEN 'cv2'  THEN rc.cv2 END) v(rec)
            WHERE m.script = 'q_multires_tails' AND m.window_bin = '1s'
              AND m.stat IN ('mean','max','p99','cv2')) q$$),

-- ---------------------------------------------------------------------
-- C1xx -- ARITHMETIC IDENTITIES INSIDE THE PROJECTIONS
-- ---------------------------------------------------------------------
('C101', 'cost_accounting.total_from_order_ws = provisioned_ws + warmup_ws', 'error', 'cheap',
 'The dual cost-accounting decomposition is exact for all 40 rows.',
 'Observed 0 violations (audit lens C: 40/40 exact).',
$$SELECT count(*) = 0,
         format('%s of %s cost_accounting rows break the order/readiness decomposition',
                count(*), (SELECT count(*) FROM provenance.cost_accounting))
    FROM provenance.cost_accounting
   WHERE abs(total_from_order_ws - (provisioned_ws + warmup_ws)) > 1e-6$$),

('C102', 'ewma_ablation_cell.ratio_vs_static = ws / denom_static_c8_ws', 'error', 'cheap',
 'The ablation ratio is the quotient it claims to be, to storage rounding, for all 208 cells.',
 'Observed 0 violations at 1e-3 (audit lens C: 48/48 to storage rounding).',
$$SELECT count(*) = 0,
         format('%s of %s ewma_ablation_cell rows break ratio_vs_static = ws/denom_static_c8_ws',
                count(*), (SELECT count(*) FROM provenance.ewma_ablation_cell))
    FROM provenance.ewma_ablation_cell
   WHERE denom_static_c8_ws IS NOT NULL AND denom_static_c8_ws <> 0
     AND abs(ratio_vs_static - ws / denom_static_c8_ws) > 1e-3$$),

('C103', 'coverage_meta: the trace splits exactly into forecast span + context days', 'error', 'cheap',
 'forecast_span_requests + context_days_requests = trace_requests = 1,000,000.',
 'Observed exact: 749601 + 250399 = 1000000, complete = true.',
$$SELECT count(*) FILTER (WHERE bad) = 0 AND count(*) > 0,
         format('%s of %s coverage_meta manifests break the split; totals: %s',
                count(*) FILTER (WHERE bad), count(*),
                coalesce(string_agg(format('%s=%s+%s', trace_requests, fsr, cdr), '; '), 'none'))
    FROM (SELECT trace_requests, forecast_span_requests AS fsr, context_days_requests AS cdr,
                 forecast_span_requests + context_days_requests <> trace_requests
                 OR trace_requests <> 1000000 AS bad
            FROM provenance.coverage_meta) q$$),

('C104', 'coverage.ok is the flag it claims to be', 'error', 'cheap',
 'coverage.ok is true exactly when requests >= expect, for all 80 rows.',
 'Observed 0 violations; all 80 rows have requests = expect and ok = true. '
 'NOTE: is_full is NULL on 75 of 80 rows and is deliberately NOT asserted here.',
$$SELECT count(*) = 0,
         format('%s of %s coverage rows where ok <> (requests >= expect)',
                count(*), (SELECT count(*) FROM provenance.coverage))
    FROM provenance.coverage WHERE ok IS DISTINCT FROM (requests >= expect)$$),

('C105', 'vLLM ETL reconciles to the token', 'error', 'cheap',
 'count(vllm_token_itl) equals the server-side generated-token total energy.tot_gen_tokens.',
 'Observed 1,354,025 = 1,354,025, exact.',
$$SELECT a.n = b.v,
         format('vllm_token_itl rows = %s ; energy.tot_gen_tokens = %s', a.n, b.v)
    FROM (SELECT count(*) n FROM provenance.vllm_token_itl) a,
         (SELECT max(value_num)::bigint v FROM provenance.vllm_stat
           WHERE metric_path = 'energy.tot_gen_tokens') b$$),

('C106', 'vLLM hard reconciliation checks all pass', 'error', 'cheap',
 'Every vllm_reconcile_check row at level=hard has passed = true.',
 'Observed 6/6 hard checks passing.',
$$SELECT count(*) FILTER (WHERE NOT passed) = 0,
         format('%s of %s hard reconciliation checks failing: %s',
                count(*) FILTER (WHERE NOT passed), count(*),
                coalesce(string_agg(check_name, ', ') FILTER (WHERE NOT passed), 'none'))
    FROM provenance.vllm_reconcile_check WHERE level = 'hard'$$),

('C107', 'vLLM soft reconciliation checks all pass', 'warn', 'cheap',
 'Every vllm_reconcile_check row at level=soft has passed = true.',
 'KNOWN FAILING: 1 of 7 -- measured:vllm_h100_trace / client_gen_tokens_eq_gen, '
 '"mismatch=24 (known logprob edge; server truth used)". Recorded as an accepted, '
 'documented discrepancy, hence severity warn rather than error.',
$$SELECT count(*) FILTER (WHERE NOT passed) = 0,
         format('%s of %s soft reconciliation checks failing: %s',
                count(*) FILTER (WHERE NOT passed), count(*),
                coalesce(string_agg(run_id||'/'||check_name||' -- '||coalesce(detail,''), '; ')
                         FILTER (WHERE NOT passed), 'none'))
    FROM provenance.vllm_reconcile_check WHERE level = 'soft'$$),

-- ---------------------------------------------------------------------
-- C2xx -- ORPHAN SWEEPS (the spine actually being a spine)
-- ---------------------------------------------------------------------
('C201', 'llm_request has no orphan run_ids', 'error', 'moderate',
 'Every llm_request row joins to provenance.runs.',
 'Observed 0 orphans. This is the precondition for the FK in 99_readonly_optimization.sql.',
$$SELECT count(*) = 0, format('%s orphan llm_request rows', count(*))
    FROM provenance.llm_request x
   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)$$),

('C202', 'composed_request has no orphan run_ids', 'error', 'moderate',
 'Every composed_request row joins to provenance.runs.', 'Observed 0 orphans.',
$$SELECT count(*) = 0, format('%s orphan composed_request rows', count(*))
    FROM provenance.composed_request x
   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)$$),

('C203', 'encoder_series has no orphan run_ids', 'error', 'moderate',
 'Every encoder_series row joins to provenance.runs.', 'Observed 0 orphans.',
$$SELECT count(*) = 0, format('%s orphan encoder_series rows', count(*))
    FROM provenance.encoder_series x
   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)$$),

('C204', 'worker_schedule has no orphan run_ids', 'error', 'cheap',
 'Every worker_schedule row joins to provenance.runs.',
 'Observed 0 orphans -- DEF-1 (118,861 unjoinable rows, 55%%) is REPAIRED. This check is the '
 'regression guard that keeps it repaired.',
$$SELECT count(*) = 0, format('%s orphan worker_schedule rows (of %s)', count(*),
                              (SELECT count(*) FROM provenance.worker_schedule))
    FROM provenance.worker_schedule x
   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)$$),

('C205', 'verification.resolved_run_id resolves to the spine', 'error', 'cheap',
 'Every non-null verification.resolved_run_id joins to provenance.runs.',
 'Observed 0 orphans -- DEF-2 (320/320 unjoinable) is REPAIRED via the resolved_run_id column. '
 'The bare verification.run_id remains unprefixed by design; see C206.',
$$SELECT count(*) = 0, format('%s verification rows whose resolved_run_id is not in runs', count(*))
    FROM provenance.verification x
   WHERE x.resolved_run_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.resolved_run_id)$$),

('C206', 'verification.run_id (raw, unprefixed) coverage census', 'info', 'cheap',
 'Descriptive: how many verification rows carry a bare run_id that does not itself join.',
 'Observed 321 -- EXPECTED. verification.run_id holds the unprefixed simulator id; the join '
 'key is resolved_run_id (C205). Kept as info so the number is tracked, never as a failure.',
$$SELECT true,
         format('%s of %s verification rows have a bare run_id absent from runs (expected: the '
                'join key is resolved_run_id)', count(*) FILTER (WHERE orphan), count(*))
    FROM (SELECT x.run_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id) AS orphan
            FROM provenance.verification x) q$$),

('C207', 'ingest_log.run_id points at a real spine row', 'warn', 'cheap',
 'Every non-null ingest_log.run_id joins to provenance.runs.',
 'KNOWN FAILING: 301 of 2,754 rows (was 525 at audit time -- partially repaired). These are '
 'files whose load created no spine row. Self-perpetuating: the loader skips already-logged '
 'files, so the spine row is never created on a re-run. See DEF-6.',
$$SELECT count(*) = 0,
         format('%s of %s ingest_log rows reference a run_id absent from runs',
                count(*), (SELECT count(*) FROM provenance.ingest_log))
    FROM provenance.ingest_log x
   WHERE x.run_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)$$),

('C208', 'every summary/cell projection joins to the spine', 'error', 'cheap',
 'llm_run_summary, encoder_run_summary and factorial_cell are fully joinable to runs.',
 'Observed 0/0/0 orphans (all three are already FK-enforced in 01_schema.sql; this check is '
 'the cheap end-to-end confirmation).',
$$SELECT (a+b+c) = 0, format('orphans -- llm_run_summary=%s encoder_run_summary=%s factorial_cell=%s', a,b,c)
    FROM (SELECT (SELECT count(*) FROM provenance.llm_run_summary x
                   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)) a,
                 (SELECT count(*) FROM provenance.encoder_run_summary x
                   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)) b,
                 (SELECT count(*) FROM provenance.factorial_cell x
                   WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)) c) q$$),

('C209', 'runs.window_name is drawn from the windows dimension', 'warn', 'cheap',
 'Every non-null runs.window_name exists in provenance.windows.',
 'KNOWN FAILING: 129 runs (all spelled week). DEF-12 -- the window vocabulary was never canonicalised '
 '(steady vs steady24h is a typo-class split). Blocks the runs_window_fk in 99_. See DEC-7.',
$$SELECT count(*) = 0,
         format('%s runs whose window_name is not in the windows dimension: %s',
                count(*), coalesce((SELECT string_agg(DISTINCT w, ', ')
                   FROM (SELECT r.window_name w FROM provenance.runs r
                          WHERE r.window_name IS NOT NULL
                            AND NOT EXISTS (SELECT 1 FROM provenance.windows x
                                             WHERE x.window_name = r.window_name)
                          LIMIT 200) s), 'none'))
    FROM provenance.runs r
   WHERE r.window_name IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.windows w WHERE w.window_name = r.window_name)$$),

-- ---------------------------------------------------------------------
-- C210 / C211 -- THE WINDOW-ALIAS GUARD.  See provenance/audit/WINDOW_ALIAS.md.
--
-- v_dim folds week->aggregate and steady->steady24h; the BASE TABLES DO NOT.
-- A base-table filter on the canonical name therefore answers a window-scoped
-- question from a fraction of the evidence AND RAISES NO ERROR.  C210 is the
-- alarm for exactly that condition; it is RED today by design and goes green
-- only when the base tables are normalised (remediation DDL in WINDOW_ALIAS.md
-- section 3.2).  C211 is the same defect one level up, inside windows itself.
-- ---------------------------------------------------------------------
('C210', 'Window-name alias fold: no base table may carry a non-canonical window spelling', 'error', 'cheap',
 'Zero base tables carry an alias-spelled window_name. Equivalently: for every base table, '
 'WHERE window_name = <canonical> returns the same population as the alias-aware filter '
 'through provenance.v_dim.',
 'THE WINDOW-ALIAS TRAP (see provenance/audit/WINDOW_ALIAS.md). KNOWN FAILING: runs holds '
 '129 week + 6 aggregate (intra-table split, the worst case), composed_e2e 4 week, '
 'rerun_b1_window/curve_point steady. Until it is green: filter through provenance.v_dim, '
 'never the base table. The relation list is derived from pg_attribute, so tables added '
 'later are covered automatically.',
$$WITH rels AS (
    SELECT c.oid::regclass AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_attribute a ON a.attrelid = c.oid
                       AND a.attname = 'window_name'
                       AND a.attnum > 0 AND NOT a.attisdropped
    WHERE n.nspname = 'provenance'
      AND c.relkind IN ('r','p')
      AND c.relispartition IS FALSE
      AND c.relname <> 'windows'
), al AS (
    SELECT alias, canonical_window
    FROM provenance.v_window_alias
    WHERE canonical_window IS NOT NULL
), probe AS (
    SELECT rels.rel::text AS rel, al.alias, al.canonical_window,
           (xpath('/row/c/text()', query_to_xml(
               format('SELECT count(*) AS c FROM %s WHERE window_name = %L',
                      rels.rel, al.alias), false, true, '')))[1]::text::bigint AS n_alias,
           (xpath('/row/c/text()', query_to_xml(
               format('SELECT count(*) AS c FROM %s WHERE window_name = %L',
                      rels.rel, al.canonical_window), false, true, '')))[1]::text::bigint AS n_canon
    FROM rels CROSS JOIN al
), bad AS (
    SELECT * FROM probe WHERE n_alias > 0
)
SELECT (SELECT count(*) FROM bad) = 0,
       CASE WHEN (SELECT count(*) FROM bad) = 0
            THEN 'No base table carries a non-canonical window spelling; every base-table window filter sees the full alias-aware population.'
            ELSE 'ALIAS SPLIT: ' || (SELECT string_agg(
                     format('%s: %s=%s vs canonical %s=%s%s', rel, alias, n_alias,
                            canonical_window, n_canon,
                            CASE WHEN n_canon > 0 THEN ' [INTRA-TABLE SPLIT]' ELSE ' [canonical filter returns a fraction/none]' END),
                     '; ' ORDER BY rel, alias) FROM bad)
       END$$),

('C211', 'provenance.windows: no unregistered duplicate span', 'warn', 'cheap',
 'No two provenance.windows rows share (trace_offset, requests, span_s) unless the pair is '
 'registered in provenance.v_window_alias.',
 'Companion to C210. Two byte-identical spans under different names is the same defect one level '
 'up: a query keyed on one name silently misses evidence filed under the other. KNOWN FAILING: '
 'aggregate and span_chronos are byte-identical (trace_offset=250399, requests=749601, '
 'span_s=483659.8), i.e. the 5.60-day chronos-covered span has THREE names (week / aggregate / '
 'span_chronos) and v_window_alias documents only one of the two folds.',
$$WITH dup AS (
    SELECT trace_offset, requests, span_s,
           array_agg(window_name ORDER BY window_name) AS names, count(*) AS n
    FROM provenance.windows
    GROUP BY trace_offset, requests, span_s
    HAVING count(*) > 1
), unreg AS (
    SELECT d.* FROM dup d
    WHERE NOT EXISTS (SELECT 1 FROM provenance.v_window_alias a
                      WHERE a.alias = ANY (d.names) AND a.canonical_window = ANY (d.names))
)
SELECT (SELECT count(*) FROM unreg) = 0,
       CASE WHEN (SELECT count(*) FROM unreg) = 0
            THEN 'Every provenance.windows row denotes a distinct span, or its duplicate spelling is registered in v_window_alias.'
            ELSE 'UNREGISTERED DUPLICATE SPAN(S): ' || (SELECT string_agg(
                     format('%s (trace_offset=%s, requests=%s, span_s=%s)',
                            array_to_string(names, ' == '), trace_offset, requests, span_s),
                     '; ' ORDER BY trace_offset) FROM unreg)
       END$$),

-- ---------------------------------------------------------------------
-- C3xx -- run_id INJECTIVITY AND PARTITION PLACEMENT
-- ---------------------------------------------------------------------
('C301', 'run_id is injective over source files', 'error', 'cheap',
 'No run_id in provenance.runs maps to more than one source_path -- i.e. no two artifacts '
 'were silently collapsed onto one identity by the loader.',
 'Observed 0. This is the exact failure mode of DEF-3 (a16 run_ids dropping the sweep config, '
 '47,043 rows destroyed by delete-then-insert). Run after EVERY load.',
$$SELECT count(*) = 0,
         format('%s run_ids map to more than one source_path: %s', count(*),
                coalesce(string_agg(run_id, ', '), 'none'))
    FROM (SELECT run_id FROM provenance.runs
           GROUP BY run_id HAVING count(DISTINCT source_path) > 1) q$$),

('C302', 'run_id prefix agrees with runs.experiment', 'warn', 'cheap',
 'Every run_id is <experiment>:<local-id>, so the identity carries its own family.',
 'KNOWN FAILING: 2 rows -- measured:vllm_h100_trace and measured:vllm_per_request are filed '
 'under experiment = eda. Deliberate (the measured vLLM ETL is read by the EDA chapter) but it '
 'breaks the prefix rule, so it is surfaced rather than special-cased away.',
$$SELECT count(*) = 0,
         format('%s runs whose run_id prefix <> experiment: %s', count(*),
                coalesce(string_agg(format('%s (experiment=%s)', run_id, experiment), ', '), 'none'))
    FROM provenance.runs WHERE split_part(run_id, ':', 1) <> experiment$$),

('C303', 'every run_id is namespaced', 'error', 'cheap',
 'Every run_id contains a colon, so bare simulator ids can never collide across families.',
 'Observed 0 bare ids.',
$$SELECT count(*) = 0, format('%s run_ids contain no colon', count(*))
    FROM provenance.runs WHERE position(':' in run_id) = 0$$),

('C304', 'partition key never disagrees with runs.experiment (logical)', 'error', 'moderate',
 'For all three partitioned raw fact tables, the row-level experiment column equals the '
 'experiment recorded on the spine for that run.',
 'Observed 0/0/0 mismatches.',
$$SELECT (a+b+c) = 0, format('logical partition-key mismatches -- llm=%s composed=%s encoder=%s', a,b,c)
    FROM (SELECT (SELECT count(*) FROM provenance.llm_request x JOIN provenance.runs r USING (run_id)
                   WHERE x.experiment <> r.experiment) a,
                 (SELECT count(*) FROM provenance.composed_request x JOIN provenance.runs r USING (run_id)
                   WHERE x.experiment <> r.experiment) b,
                 (SELECT count(*) FROM provenance.encoder_series x JOIN provenance.runs r USING (run_id)
                   WHERE x.experiment <> r.experiment) c) q$$),

('C305', 'no row is misfiled in a physical partition', 'error', 'moderate',
 'For every non-default partition, the physical relation name matches the row experiment -- '
 'i.e. nothing landed in the wrong partition or was left stranded by a repartition.',
 'Observed 0/0/0. Checked via tableoid, so it catches misfiling that the logical check '
 '(C304) cannot see.',
$$SELECT (a+b+c) = 0, format('physical misfiles -- llm=%s composed=%s encoder=%s', a,b,c)
    FROM (SELECT (SELECT count(*) FROM provenance.llm_request x
                   WHERE x.tableoid::regclass::text NOT LIKE '%\_default'
                     AND x.experiment <> replace(x.tableoid::regclass::text,
                                                 'provenance.llm_request_','')) a,
                 (SELECT count(*) FROM provenance.composed_request x
                   WHERE x.tableoid::regclass::text NOT LIKE '%\_default'
                     AND x.experiment <> replace(x.tableoid::regclass::text,
                                                 'provenance.composed_request_','')) b,
                 (SELECT count(*) FROM provenance.encoder_series x
                   WHERE x.tableoid::regclass::text NOT LIKE '%\_default'
                     AND x.experiment <> replace(x.tableoid::regclass::text,
                                                 'provenance.encoder_series_','')) c) q$$),

('C306', 'the misc default partition is not growing', 'warn', 'cheap',
 'No run should be filed under experiment = misc; misc is the loader''s unmapped-directory '
 'fallback and it is what caused the DEF-3 run_id collisions.',
 'KNOWN FAILING: 369 runs still under misc. DEC-3 -- extend the dir->experiment map and '
 'reload. Blocking-adjacent for a16/g2/g3_32b/g6: an unmapped new directory lands here.',
$$SELECT count(*) = 0, format('%s runs filed under experiment = misc', count(*))
    FROM provenance.runs WHERE experiment = 'misc'$$),

-- ---------------------------------------------------------------------
-- C4xx -- SUPERSESSION / FRESHNESS / SELF-DESCRIPTION
-- ---------------------------------------------------------------------
('C401', 'supersession pointers are not dangling', 'error', 'cheap',
 'Every non-null runs.superseded_by and runs.supersedes names an existing run.',
 'Observed 0 dangling (both columns are in fact empty everywhere -- see C402).',
$$SELECT (a+b) = 0, format('dangling superseded_by=%s supersedes=%s', a, b)
    FROM (SELECT (SELECT count(*) FROM provenance.runs r WHERE r.superseded_by IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM provenance.runs x WHERE x.run_id=r.superseded_by)) a,
                 (SELECT count(*) FROM provenance.runs r WHERE r.supersedes IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM provenance.runs x WHERE x.run_id=r.supersedes)) b) q$$),

('C402', 'retraction machinery census', 'info', 'cheap',
 'Descriptive: how many runs are marked not-current, and how many carry supersession pointers. '
 'If these are all zero the current_* views filter nothing while reading as the clean set.',
 'Observed at audit time: is_current true for all 2,206 rows, supersedes/superseded_by empty. '
 'Retraction is happening through grid_window.is_superseded + grid_correction instead (DEF-11, '
 'DEC-6). Info, not a failure -- but if this still reads 0/0 the views are decorative.',
$$SELECT true,
         format('runs=%s not_current=%s with_supersedes=%s with_superseded_by=%s; '
                'grid_window.is_superseded=%s grid_correction rows=%s',
                count(*), count(*) FILTER (WHERE NOT is_current),
                count(*) FILTER (WHERE supersedes IS NOT NULL),
                count(*) FILTER (WHERE superseded_by IS NOT NULL),
                (SELECT count(*) FROM provenance.grid_window WHERE is_superseded),
                (SELECT count(*) FROM provenance.grid_correction))
    FROM provenance.runs$$),

('C403', 'llm_run_summary.has_raw_records tells the truth', 'error', 'moderate',
 'The has_raw_records flag equals EXISTS(raw llm_request rows for that run).',
 'PASSES as of 2026-07-20. The DATA was wrong, not the check: all 25 disagreeing rows had '
 'has_raw_records IS NULL (not a wrong boolean), all in the g1: family, ingested after the '
 '12_repair3.sql one-time classification and never re-classified -- exactly the "ingest ran '
 'without re-classifying" case v_llm_raw_backing calls UNCHECKED. Backfilled from the raw layer, '
 'which is the authority for this derived convenience column. Census before: TRUE 101 / FALSE '
 '394 / NULL 25 (24 of the NULLs did have raw rows, 1 did not). Census immediately after: TRUE '
 '125 / FALSE 395 / NULL 0. The single row set to FALSE (g1:burst2_lang_repro_gridC8) was not '
 'asserted by inference: FALSE in this schema means "verified not recomputable", so disk was '
 're-scanned under /home/gio/tese/{simulation/results,defense/anim/data} -- only '
 'burst2_lang_repro_gridC8.{report.json,log} exist, no *.requests.jsonl anywhere, so the FALSE '
 'verdict is evidence-based. A concurrent K2 reload then took the table 520 -> 284 rows; '
 're-verified after it settled, census is TRUE 108 / FALSE 176 / NULL 0 and TRUE exactly equals '
 'the 108 distinct run_ids in llm_request. NOTE the failure mode is STRUCTURAL, not one-off: '
 'has_raw_records has no default and no trigger, so any future ingest re-introduces NULLs and '
 're-fails this check -- re-run the backfill in 12_repair3.sql after every K2 ingest. This check '
 'only asserts the flag is truthful; the runs with no raw backing remain unauditable and are '
 'tracked separately by C404.',
$$SELECT count(*) = 0,
         format('%s of %s llm_run_summary rows have has_raw_records disagreeing with reality',
                count(*), (SELECT count(*) FROM provenance.llm_run_summary))
    FROM provenance.llm_run_summary s
   WHERE s.has_raw_records IS DISTINCT FROM
         EXISTS (SELECT 1 FROM provenance.llm_request x WHERE x.run_id = s.run_id)$$),

('C404', 'unbacked llm_run_summary census', 'warn', 'moderate',
 'Summaries with zero backing raw rows cannot be audited against evidence.',
 'KNOWN FAILING: 395 of 495 rows (9.3M requests) have no raw rows, and all are is_current. '
 'DEF-8. Not a corruption -- the raw records were never exported for those runs -- but any '
 'number sourced from them is unverifiable. Kept as warn so the count is tracked, not hidden.',
$$SELECT count(*) FILTER (WHERE unbacked) = 0,
         format('%s of %s llm_run_summary rows have no backing llm_request rows',
                count(*) FILTER (WHERE unbacked), count(*))
    FROM (SELECT NOT EXISTS (SELECT 1 FROM provenance.llm_request x WHERE x.run_id = s.run_id) AS unbacked
            FROM provenance.llm_run_summary s) q$$),

('C405', 'mv_llm_p99_check is not stale', 'error', 'moderate',
 'The materialized correctness guard covers every run that currently has raw rows; if it is '
 'stale, v_llm_drift silently checks a subset while reading as a full check.',
 'DEF-10: at audit time 80 materialized rows vs 101 live -- 79%% coverage. REFRESH '
 'MATERIALIZED VIEW provenance.mv_llm_p99_check fixes it.',
$$SELECT a = b, format('mv_llm_p99_check has %s rows; %s runs currently have raw llm_request rows', a, b)
    FROM (SELECT (SELECT count(*) FROM provenance.mv_llm_p99_check) a,
                 (SELECT count(DISTINCT run_id) FROM provenance.llm_request) b) q$$),

-- ---------------------------------------------------------------------
-- C5xx -- VOCABULARY DRIFT (the mirror of the PART B domains)
--         These catch a NEW spelling appearing during the remaining
--         ingests, which the NOT VALID CHECK constraints would also
--         reject -- but these report it instead of aborting the load.
-- ---------------------------------------------------------------------
('C501', 'runs.pool vocabulary is closed', 'error', 'cheap',
 'runs.pool is one of language, encoder, both (or NULL).',
 'Observed language=522 encoder=1421 both=399 NULL=7.',
$$SELECT count(*) = 0,
         format('%s runs with an unknown pool: %s', count(*),
                coalesce(string_agg(DISTINCT pool, ', '), 'none'))
    FROM provenance.runs WHERE pool IS NOT NULL AND pool NOT IN ('language','encoder','both')$$),

('C502', 'runs.policy vocabulary is closed', 'error', 'cheap',
 'runs.policy is one of forecast, reactive, static (or NULL).',
 'Observed forecast=1506 reactive=259 static=36 NULL=548.',
$$SELECT count(*) = 0,
         format('%s runs with an unknown policy: %s', count(*),
                coalesce(string_agg(DISTINCT policy, ', '), 'none'))
    FROM provenance.runs WHERE policy IS NOT NULL AND policy NOT IN ('forecast','reactive','static')$$),

('C503', 'quantile vocabulary is closed across runs and cells', 'error', 'cheap',
 'quantile is one of p50, p90, obs (or NULL), in runs, factorial_cell and ewma_ablation_cell.',
 'Observed runs: p90=841 p50=427 obs=5; factorial_cell: p90=725 p50=362 obs=5; '
 'ewma_ablation_cell: p90=204 p50=4.',
$$SELECT (a+b+c) = 0, format('unknown quantile values -- runs=%s factorial_cell=%s ewma_ablation_cell=%s', a,b,c)
    FROM (SELECT (SELECT count(*) FROM provenance.runs
                   WHERE quantile IS NOT NULL AND quantile NOT IN ('p50','p90','obs')) a,
                 (SELECT count(*) FROM provenance.factorial_cell
                   WHERE quantile IS NOT NULL AND quantile NOT IN ('p50','p90','obs')) b,
                 (SELECT count(*) FROM provenance.ewma_ablation_cell
                   WHERE quantile IS NOT NULL AND quantile NOT IN ('p50','p90','obs')) c) q$$),

('C504', 'readiness vocabulary is closed', 'error', 'cheap',
 'readiness is one of strict, warm (or NULL) in factorial_cell and ewma_ablation_cell.',
 'Observed factorial_cell: strict=300 warm=300 NULL=572; ewma: strict=96 warm=112.',
$$SELECT (a+b) = 0, format('unknown readiness values -- factorial_cell=%s ewma_ablation_cell=%s', a, b)
    FROM (SELECT (SELECT count(*) FROM provenance.factorial_cell
                   WHERE readiness IS NOT NULL AND readiness NOT IN ('strict','warm')) a,
                 (SELECT count(*) FROM provenance.ewma_ablation_cell
                   WHERE readiness IS NOT NULL AND readiness NOT IN ('strict','warm')) b) q$$),

('C505', 'actuation vocabulary is closed', 'error', 'cheap',
 'actuation is issue-time or target-time (or NULL) in runs and factorial_cell.',
 'Widened 2026-07-20 (ADJUDICATION §2.7). Observed: issue-time 600 rows (the '
 'factorial_issuetime rebuild), target-time 572 rows (results_44.jsonl 560 + '
 'pilot_results.jsonl 12), NULL elsewhere. The two actuations are NOT comparable '
 'cell-for-cell -- target-time makes the worker READY AT the target bin, issue-time '
 'ISSUES the decision at t for readiness at t+lead -- so anything that aggregates '
 'factorial_cell without filtering actuation is wrong. A THIRD value still fires.',
$$SELECT (a+b) = 0, format('unknown actuation values -- runs=%s factorial_cell=%s', a, b)
    FROM (SELECT (SELECT count(*) FROM provenance.runs
                   WHERE actuation IS NOT NULL AND actuation NOT IN ('issue-time','target-time')) a,
                 (SELECT count(*) FROM provenance.factorial_cell
                   WHERE actuation IS NOT NULL AND actuation NOT IN ('issue-time','target-time')) b) q$$),

('C506', 'runs.engine vocabulary is closed', 'error', 'cheap',
 'runs.engine is vLLM (or NULL).',
 'Observed vLLM=2, NULL=2347. Engine identity is otherwise implied by runs.experiment or '
 'recoverable from the collector_* tables (see DEF/lens B note).',
$$SELECT count(*) = 0,
         format('%s runs with an unknown engine: %s', count(*),
                coalesce(string_agg(DISTINCT engine, ', '), 'none'))
    FROM provenance.runs WHERE engine IS NOT NULL AND engine NOT IN ('vLLM')$$),

('C507', 'coverage.pool vocabulary is closed', 'error', 'cheap',
 'coverage.pool is one of language, encoder, both (E2E).',
 'Observed language=74 encoder=3 "both (E2E)"=3. NOTE the spelling differs from runs.pool '
 '(both vs "both (E2E)") -- both spellings legitimately exist and both are allowed.',
$$SELECT count(*) = 0,
         format('%s coverage rows with an unknown pool: %s', count(*),
                coalesce(string_agg(DISTINCT pool, ', '), 'none'))
    FROM provenance.coverage WHERE pool NOT IN ('language','encoder','both (E2E)','both')$$),

-- ---------------------------------------------------------------------
-- C6xx -- INGEST HYGIENE (run these after every load)
-- ---------------------------------------------------------------------
('C601', 'no rows are landing in a default partition', 'warn', 'cheap',
 'The *_default partitions should be empty: a non-empty default means a family was loaded '
 'without its partition being created first, which defeats pruning and hides the family.',
 'KNOWN FAILING at audit time: composed_request_default held 15,238,525 rows (43.6%% of the '
 'table), llm_request_default 94,731, encoder_series_default 1,793. §6.2 of the plan creates '
 'the a16/g2/g3_32b/g6 partitions BEFORE the load precisely so this does not grow.',
$$SELECT (a+b+c) = 0, format('default-partition rows -- composed=%s llm=%s encoder_series=%s', a,b,c)
    FROM (SELECT (SELECT count(*) FROM provenance.composed_request_default) a,
                 (SELECT count(*) FROM provenance.llm_request_default) b,
                 (SELECT count(*) FROM provenance.encoder_series_default) c) q$$),

('C602', 'ingest_log sha256 values are well formed', 'error', 'cheap',
 'Every ingest_log.sha256 is 64 lowercase hex characters -- the idempotency of the whole '
 'loader rests on this column.',
 'Observed 0 malformed. NOTE: 165 sha256 values are duplicated across different file_paths '
 '(the same artifact copied to two locations), so sha256 is deliberately NOT unique.',
$$SELECT count(*) = 0, format('%s ingest_log rows with a malformed sha256', count(*))
    FROM provenance.ingest_log WHERE sha256 !~ '^[0-9a-f]{64}$'$$),

('C603', 'every registered experiment family has a partition', 'error', 'cheap',
 'Every distinct runs.experiment that has raw rows resolves to a real, non-default partition '
 'of composed_request -- the pre-ingest gate from §6.2.',
 'Failure here means the next COPY for that family will land in composed_request_default.',
$$SELECT count(*) FILTER (WHERE missing) = 0,
         format('%s experiment families have raw rows but no dedicated composed_request partition: %s',
                count(*) FILTER (WHERE missing),
                coalesce(string_agg(experiment, ', ') FILTER (WHERE missing), 'none'))
    FROM (SELECT x.experiment,
                 NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                              WHERE n.nspname='provenance'
                                AND c.relname = 'composed_request_'||x.experiment) AS missing
            FROM (SELECT DISTINCT experiment FROM provenance.composed_request
                   WHERE experiment <> 'misc') x) q$$);
-- 'misc' is excluded deliberately: it IS the default-partition fallback, so it
-- can never have a dedicated partition. Its population is tracked by C306, and
-- the rows it strands in the default partition by C601.

-- C007 is the exhaustive form of C006 and costs ~60 s. Off by default;
-- enable it deliberately when you want the full proof:
--   UPDATE provenance.check_definition SET is_enabled = true WHERE check_id = 'C007';
UPDATE provenance.check_definition SET is_enabled = false WHERE check_id = 'C007';


-- =====================================================================
-- PART B -- CONSISTENCY CONSTRAINTS
-- =====================================================================
-- METHOD: every predicate below was run as a COUNT against the live store
-- FIRST and returned 0 violations.  Predicates that the data violates are
-- listed in B.5 as REJECTED, with the violation count, rather than being
-- asserted and breaking the ingest.
--
-- NOT VALID is used on every partitioned raw fact table and on any table
-- whose validation scan would be measured in minutes.  NOT VALID still
-- enforces the constraint for all INSERTs and UPDATEs from this moment on;
-- it only skips the one-time backfill scan.  The VALIDATE statements are
-- staged in 99_readonly_optimization.sql.
-- =====================================================================

-- ---------------------------------------------------------------------
-- B.1  Vocabulary domains.
--      Written ONLY after enumerating the live distinct values (see the
--      note on each C5xx check above); every spelling that legitimately
--      exists is included, including coverage's 'both (E2E)' which
--      differs from runs' 'both'.
--      NULL always passes a CHECK, so these constrain the vocabulary
--      without requiring the column to be populated.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_pool_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_pool_vocab
  CHECK (pool IS NULL OR pool IN ('language','encoder','both')) NOT VALID;

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_policy_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_policy_vocab
  CHECK (policy IS NULL OR policy IN ('forecast','reactive','static')) NOT VALID;

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_quantile_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_quantile_vocab
  CHECK (quantile IS NULL OR quantile IN ('p50','p90','obs')) NOT VALID;

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_actuation_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_actuation_vocab
  CHECK (actuation IS NULL OR actuation IN ('issue-time')) NOT VALID;

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_engine_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_engine_vocab
  CHECK (engine IS NULL OR engine IN ('vLLM')) NOT VALID;

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_mode_vocab;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_mode_vocab
  CHECK (mode IS NULL OR mode IN ('uni','cov')) NOT VALID;

-- run_id must be namespaced (C303 = 0 violations). This is the structural
-- guard against the DEF-3 collision class: a bare simulator id can never
-- again be inserted as a spine key.
ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_run_id_namespaced;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_run_id_namespaced
  CHECK (position(':' in run_id) > 0) NOT VALID;

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_policy_vocab;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_policy_vocab
  CHECK (policy IS NULL OR policy IN ('forecast','reactive','static'));

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_quantile_vocab;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_quantile_vocab
  CHECK (quantile IS NULL OR quantile IN ('p50','p90','obs'));

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_readiness_vocab;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_readiness_vocab
  CHECK (readiness IS NULL OR readiness IN ('strict','warm'));

-- Widened 2026-07-20 to admit 'target-time' (ADJUDICATION §2.7): the archived
-- 560-cell exploratory grid + the 12-cell pilot really are a second actuation
-- mode. An EXTENSION of the domain, not a relaxation -- a third value still
-- fails. Kept in sync with 23_runtime_build_and_actuation.sql so re-running
-- this file cannot revert the correction.
ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_actuation_vocab;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_actuation_vocab
  CHECK (actuation IS NULL OR actuation IN ('issue-time','target-time'));

ALTER TABLE provenance.ewma_ablation_cell DROP CONSTRAINT IF EXISTS ewma_ablation_cell_quantile_vocab;
ALTER TABLE provenance.ewma_ablation_cell ADD CONSTRAINT ewma_ablation_cell_quantile_vocab
  CHECK (quantile IS NULL OR quantile IN ('p50','p90','obs'));

ALTER TABLE provenance.ewma_ablation_cell DROP CONSTRAINT IF EXISTS ewma_ablation_cell_readiness_vocab;
ALTER TABLE provenance.ewma_ablation_cell ADD CONSTRAINT ewma_ablation_cell_readiness_vocab
  CHECK (readiness IS NULL OR readiness IN ('strict','warm'));

ALTER TABLE provenance.cost_accounting DROP CONSTRAINT IF EXISTS cost_accounting_policy_vocab;
ALTER TABLE provenance.cost_accounting ADD CONSTRAINT cost_accounting_policy_vocab
  CHECK (policy IN ('forecast','reactive','static'));

-- coverage.pool carries its own spelling; both are legitimate.
ALTER TABLE provenance.coverage DROP CONSTRAINT IF EXISTS coverage_pool_vocab;
ALTER TABLE provenance.coverage ADD CONSTRAINT coverage_pool_vocab
  CHECK (pool IN ('language','encoder','both','both (E2E)'));

ALTER TABLE provenance.vllm_reconcile_check DROP CONSTRAINT IF EXISTS vllm_reconcile_check_level_vocab;
ALTER TABLE provenance.vllm_reconcile_check ADD CONSTRAINT vllm_reconcile_check_level_vocab
  CHECK (level IN ('hard','soft'));

-- ---------------------------------------------------------------------
-- B.2  Range / sign / ordering CHECKs on the PROJECTIONS.
--      These tables are small; the constraints are created VALID (the
--      scan is milliseconds) so they are enforced retroactively too.
-- ---------------------------------------------------------------------

-- llm_run_summary: percentiles must be monotone and counts sane.
--   verified: 0 rows break the TTFT ladder, 0 break the E2E ladder,
--             0 have completed_requests > num_requests.
ALTER TABLE provenance.llm_run_summary DROP CONSTRAINT IF EXISTS llm_run_summary_ttft_monotone;
ALTER TABLE provenance.llm_run_summary ADD CONSTRAINT llm_run_summary_ttft_monotone
  CHECK (median_ttft_ms <= p90_ttft_ms AND p90_ttft_ms <= p95_ttft_ms
     AND p95_ttft_ms   <= p99_ttft_ms AND p99_ttft_ms <= max_ttft_ms);

ALTER TABLE provenance.llm_run_summary DROP CONSTRAINT IF EXISTS llm_run_summary_e2e_monotone;
ALTER TABLE provenance.llm_run_summary ADD CONSTRAINT llm_run_summary_e2e_monotone
  CHECK (p90_e2e_latency_ms <= p99_e2e_latency_ms
     AND p99_e2e_latency_ms <= max_e2e_latency_ms);

ALTER TABLE provenance.llm_run_summary DROP CONSTRAINT IF EXISTS llm_run_summary_counts;
ALTER TABLE provenance.llm_run_summary ADD CONSTRAINT llm_run_summary_counts
  CHECK (completed_requests >= 0 AND num_requests >= 0
     AND completed_requests <= num_requests);

-- encoder_run_summary: delay ladder, and busy <= provisioned worker-seconds.
--   verified: 0 rows break the delay ladder; 0 have busy > provisioned;
--             0 have utilization or text_only_fraction outside [0,1].
ALTER TABLE provenance.encoder_run_summary DROP CONSTRAINT IF EXISTS encoder_run_summary_delay_monotone;
ALTER TABLE provenance.encoder_run_summary ADD CONSTRAINT encoder_run_summary_delay_monotone
  CHECK (encoder_delay_p50_ms <= encoder_delay_p90_ms
     AND encoder_delay_p90_ms <= encoder_delay_p99_ms
     AND encoder_delay_p99_ms <= encoder_delay_max_ms);

ALTER TABLE provenance.encoder_run_summary DROP CONSTRAINT IF EXISTS encoder_run_summary_ws_bounded;
ALTER TABLE provenance.encoder_run_summary ADD CONSTRAINT encoder_run_summary_ws_bounded
  CHECK (provisioned_worker_seconds >= 0 AND busy_worker_seconds >= 0
     AND busy_worker_seconds <= provisioned_worker_seconds);

ALTER TABLE provenance.encoder_run_summary DROP CONSTRAINT IF EXISTS encoder_run_summary_fractions;
ALTER TABLE provenance.encoder_run_summary ADD CONSTRAINT encoder_run_summary_fractions
  CHECK ((encoder_utilization  IS NULL OR encoder_utilization  BETWEEN 0 AND 1)
     AND (text_only_fraction   IS NULL OR text_only_fraction   BETWEEN 0 AND 1));

-- factorial_cell: p99 <= max, busy <= provisioned, rho in the sampled band.
--   verified: 0 violations each. rho is stored SCALED (integers 10..25,
--             i.e. tenths), NOT as a fraction -- the bound reflects that.
ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_latency_order;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_latency_order
  CHECK (p99_ms >= 0 AND max_ms >= 0 AND p99_ms <= max_ms);

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_ws_bounded;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_ws_bounded
  CHECK (provisioned_ws >= 0 AND busy_ws >= 0 AND busy_ws <= provisioned_ws);

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_rho_band;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_rho_band
  CHECK (rho IS NULL OR rho BETWEEN 1 AND 100);

ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_sched_order;
ALTER TABLE provenance.factorial_cell ADD CONSTRAINT factorial_cell_sched_order
  CHECK (sched_min_workers IS NULL OR sched_max_workers IS NULL
      OR sched_min_workers <= sched_max_workers);

ALTER TABLE provenance.runs DROP CONSTRAINT IF EXISTS runs_rho_band;
ALTER TABLE provenance.runs ADD CONSTRAINT runs_rho_band
  CHECK (rho IS NULL OR rho BETWEEN 1 AND 100) NOT VALID;

-- cost_accounting: the decomposition C101 asserts, promoted to a constraint.
--   verified: 0 violations, and 0 negative components, and warmup_frac in [0,1].
ALTER TABLE provenance.cost_accounting DROP CONSTRAINT IF EXISTS cost_accounting_decomposition;
ALTER TABLE provenance.cost_accounting ADD CONSTRAINT cost_accounting_decomposition
  CHECK (abs(total_from_order_ws - (provisioned_ws + warmup_ws)) <= 1e-6);

ALTER TABLE provenance.cost_accounting DROP CONSTRAINT IF EXISTS cost_accounting_nonneg;
ALTER TABLE provenance.cost_accounting ADD CONSTRAINT cost_accounting_nonneg
  CHECK (provisioned_ws >= 0 AND warmup_ws >= 0 AND total_from_order_ws >= 0 AND p99_ms >= 0
     AND (warmup_frac IS NULL OR warmup_frac BETWEEN 0 AND 1));

-- coverage: counts non-negative and ok is the flag it claims to be (C104).
ALTER TABLE provenance.coverage DROP CONSTRAINT IF EXISTS coverage_counts_nonneg;
ALTER TABLE provenance.coverage ADD CONSTRAINT coverage_counts_nonneg
  CHECK (requests >= 0 AND expect >= 0);

ALTER TABLE provenance.coverage DROP CONSTRAINT IF EXISTS coverage_ok_definition;
ALTER TABLE provenance.coverage ADD CONSTRAINT coverage_ok_definition
  CHECK (ok IS NULL OR ok = (requests >= expect));

ALTER TABLE provenance.coverage_meta DROP CONSTRAINT IF EXISTS coverage_meta_split;
ALTER TABLE provenance.coverage_meta ADD CONSTRAINT coverage_meta_split
  CHECK (forecast_span_requests + context_days_requests = trace_requests);

-- forecast_metrics: error metrics are non-negative and RMSE >= MAE
--   (Jensen: sqrt(E[x^2]) >= E[|x|]).  verified: 0 violations of both.
ALTER TABLE provenance.forecast_metrics DROP CONSTRAINT IF EXISTS forecast_metrics_nonneg;
ALTER TABLE provenance.forecast_metrics ADD CONSTRAINT forecast_metrics_nonneg
  CHECK (wape >= 0 AND mae >= 0 AND (rmse IS NULL OR rmse >= 0));

ALTER TABLE provenance.forecast_metrics DROP CONSTRAINT IF EXISTS forecast_metrics_rmse_ge_mae;
ALTER TABLE provenance.forecast_metrics ADD CONSTRAINT forecast_metrics_rmse_ge_mae
  CHECK (rmse IS NULL OR rmse >= mae);

ALTER TABLE provenance.forecast_metrics DROP CONSTRAINT IF EXISTS forecast_metrics_span_vocab;
ALTER TABLE provenance.forecast_metrics ADD CONSTRAINT forecast_metrics_span_vocab
  CHECK (span IN ('full','common'));

ALTER TABLE provenance.forecast_metrics DROP CONSTRAINT IF EXISTS forecast_metrics_candidate_vocab;
ALTER TABLE provenance.forecast_metrics ADD CONSTRAINT forecast_metrics_candidate_vocab
  CHECK (candidate IN ('point','p10','p20','p30','p40','p50','p60','p70','p80','p90'));

-- ingest_log: the idempotency ledger.
ALTER TABLE provenance.ingest_log DROP CONSTRAINT IF EXISTS ingest_log_sha256_format;
ALTER TABLE provenance.ingest_log ADD CONSTRAINT ingest_log_sha256_format
  CHECK (sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE provenance.ingest_log DROP CONSTRAINT IF EXISTS ingest_log_counts_nonneg;
ALTER TABLE provenance.ingest_log ADD CONSTRAINT ingest_log_counts_nonneg
  CHECK (n_rows >= 0 AND bytes >= 0);

-- eda_rate_series: rates cannot be negative.  verified: 0 violations.
ALTER TABLE provenance.eda_rate_series DROP CONSTRAINT IF EXISTS eda_rate_series_nonneg;
ALTER TABLE provenance.eda_rate_series ADD CONSTRAINT eda_rate_series_nonneg
  CHECK (value >= 0) NOT VALID;   -- 2.76M rows; NOT VALID keeps this instant

-- ---------------------------------------------------------------------
-- B.3  CHECKs on the LARGE / PARTITIONED raw facts.
--      ALL NOT VALID.  Each predicate was verified at 0 violations, but
--      validating would scan 15-35M rows and is deferred to 99_.
--      Adding a constraint to a partitioned parent recurses to every
--      partition; NOT VALID makes that catalog-only.
-- ---------------------------------------------------------------------

-- llm_request: latencies and token counts are non-negative.
--   verified: 0 rows with ttft_ms < 0, e2e_latency_ms < 0,
--             input_length < 0 or output_length < 0.
ALTER TABLE provenance.llm_request DROP CONSTRAINT IF EXISTS llm_request_latency_nonneg;
ALTER TABLE provenance.llm_request ADD CONSTRAINT llm_request_latency_nonneg
  CHECK (ttft_ms IS NULL OR ttft_ms >= 0) NOT VALID;

ALTER TABLE provenance.llm_request DROP CONSTRAINT IF EXISTS llm_request_e2e_nonneg;
ALTER TABLE provenance.llm_request ADD CONSTRAINT llm_request_e2e_nonneg
  CHECK (e2e_latency_ms IS NULL OR e2e_latency_ms >= 0) NOT VALID;

ALTER TABLE provenance.llm_request DROP CONSTRAINT IF EXISTS llm_request_tokens_nonneg;
ALTER TABLE provenance.llm_request ADD CONSTRAINT llm_request_tokens_nonneg
  CHECK ((input_length  IS NULL OR input_length  >= 0)
     AND (output_length IS NULL OR output_length >= 0)) NOT VALID;

-- composed_request: token counts non-negative.
ALTER TABLE provenance.composed_request DROP CONSTRAINT IF EXISTS composed_request_tokens_nonneg;
ALTER TABLE provenance.composed_request ADD CONSTRAINT composed_request_tokens_nonneg
  CHECK ((input_length  IS NULL OR input_length  >= 0)
     AND (output_length IS NULL OR output_length >= 0)) NOT VALID;

-- encoder_series: queue depths and worker counts are non-negative counters.
ALTER TABLE provenance.encoder_series DROP CONSTRAINT IF EXISTS encoder_series_counters_nonneg;
ALTER TABLE provenance.encoder_series ADD CONSTRAINT encoder_series_counters_nonneg
  CHECK (t >= 0
     AND (img_arrived      IS NULL OR img_arrived      >= 0)
     AND (img_completed    IS NULL OR img_completed    >= 0)
     AND (queue_imgs_end   IS NULL OR queue_imgs_end   >= 0)
     AND (busy_workers_end IS NULL OR busy_workers_end >= 0)) NOT VALID;

-- worker_schedule: a schedule step has a non-negative index, time and count.
ALTER TABLE provenance.worker_schedule DROP CONSTRAINT IF EXISTS worker_schedule_nonneg;
ALTER TABLE provenance.worker_schedule ADD CONSTRAINT worker_schedule_nonneg
  CHECK (step_index >= 0 AND t_s >= 0 AND worker_count >= 0) NOT VALID;

-- forecast: horizon and step are non-negative.
--   DELIBERATELY NOT ASSERTED: quantile monotonicity (p10<=...<=p90).
--   414,484 rows have crossing quantiles and 41 have p10 > p90; quantile
--   crossing is a real, expected property of these forecasters.
ALTER TABLE provenance.forecast DROP CONSTRAINT IF EXISTS forecast_horizon_nonneg;
ALTER TABLE provenance.forecast ADD CONSTRAINT forecast_horizon_nonneg
  CHECK (h >= 0 AND step >= 0) NOT VALID;

ALTER TABLE provenance.forecast DROP CONSTRAINT IF EXISTS forecast_model_vocab;
ALTER TABLE provenance.forecast ADD CONSTRAINT forecast_model_vocab
  CHECK (model IN ('chronos','ewma','holt_winters','naive','timesfm','toto',
                   'arima','moirai')) NOT VALID;
  -- arima and moirai have partitions but no rows today; included so a load
  -- into those partitions is not rejected by a domain that forgot them.

-- ---------------------------------------------------------------------
-- B.4  UNIQUE constraints where a natural key genuinely holds.
--      Most natural keys are ALREADY primary keys (see 01_schema.sql):
--      runs, llm_run_summary, encoder_run_summary, factorial_cell,
--      cost_accounting, coverage, coverage_meta, forecast_metrics,
--      ewma_ablation_cell, eda_rate_series, eda_metric, ingest_log,
--      windows, vllm_stat, vllm_reconcile_check, composed_e2e and the
--      whole collector_* family.  Only the PK-less vLLM raw tables need
--      one, and each was verified duplicate-free.
--
--      RATIONALE: without these, re-ingesting an already-loaded vLLM file
--      silently DOUBLES rows; idempotency currently rests entirely on the
--      ingest_log sha256 bookkeeping rather than on the schema.
--
--      These are ordinary (non-CONCURRENT) unique indexes because the
--      vllm_* tables are complete and small relative to the raw facts;
--      they are NOT part of the a16/g2/g3_32b/g6 ingest path.
-- ---------------------------------------------------------------------
--   verified duplicate-free: 0 groups with count(*) > 1 in every case.
CREATE UNIQUE INDEX IF NOT EXISTS vllm_token_itl_uq
  ON provenance.vllm_token_itl (run_id, request_id, token_idx);
CREATE UNIQUE INDEX IF NOT EXISTS vllm_engine_step_uq
  ON provenance.vllm_engine_step (run_id, ts_local);
CREATE UNIQUE INDEX IF NOT EXISTS vllm_bucket_1s_uq
  ON provenance.vllm_bucket_1s (run_id, t);
CREATE UNIQUE INDEX IF NOT EXISTS vllm_detok_uq
  ON provenance.vllm_detok (run_id, ts);
CREATE UNIQUE INDEX IF NOT EXISTS vllm_vision_encode_uq
  ON provenance.vllm_vision_encode (run_id, ts);
CREATE UNIQUE INDEX IF NOT EXISTS vllm_sys_sample_uq
  ON provenance.vllm_sys_sample (run_id, ts);
-- labels is NULLABLE; NULLS NOT DISTINCT (PG15+) so a NULL label cannot
-- slip past the constraint by being "distinct from" every other NULL.
CREATE UNIQUE INDEX IF NOT EXISTS vllm_prom_sample_uq
  ON provenance.vllm_prom_sample (run_id, metric, labels, ts) NULLS NOT DISTINCT;

-- ---------------------------------------------------------------------
-- B.5  REJECTED constraints -- verified as VIOLATED by the live data.
--      Recorded here so nobody re-proposes them without the evidence.
--
--  * worker_schedule UNIQUE (run_id, step_index)
--        17 duplicate groups.  step_index is not unique within a run --
--        the loader emits repeated indices for at least some artifacts.
--        Investigate before assuming schedule replay is deterministic.
--  * ingest_log UNIQUE (sha256)
--        165 duplicated digests: the same artifact copied to two paths.
--        file_path is the PK and that is correct.
--  * forecast CHECK (p10<=p20<=...<=p90)
--        414,484 violating rows.  Quantile crossing is real forecaster
--        behaviour, not corruption.
--  * forecast CHECK (p10 <= p90)
--        41 violating rows -- same cause.
--  * runs CHECK (split_part(run_id,':',1) = experiment)
--        2 violating rows (measured:vllm_h100_trace, measured:vllm_per_request
--        under experiment='eda').  Surfaced as check C302 instead.
--  * runs FK (window_name) REFERENCES windows
--        130 violating rows (DEF-12 / DEC-7).  Staged in 99_ behind the gate.
--  * coverage CHECK on is_full
--        is_full is NULL on 75 of 80 rows; only 'ok' is a real flag.
--  * FKs on llm_request / composed_request / encoder_series / forecast /
--        worker_schedule -- verified orphan-free today (C201-C204) but
--        DELIBERATELY OMITTED here: each FK adds a per-row index probe to
--        every COPY for the remaining a16/g2/g3_32b/g6 ingests.  Staged
--        NOT VALID + VALIDATE in 99_readonly_optimization.sql.
--  * TRIGGERS of any kind -- same reason; nothing in this file adds one.
-- ---------------------------------------------------------------------

COMMENT ON CONSTRAINT runs_run_id_namespaced ON provenance.runs IS
  'Structural guard against the DEF-3 collision class: every spine key must be '
  '<experiment>:<local-id>, so a bare simulator id can never be inserted and '
  'silently overwrite another family''s run via delete-then-insert.';
COMMENT ON CONSTRAINT factorial_cell_rho_band ON provenance.factorial_cell IS
  'rho is stored SCALED as integers (observed 10..25 = tenths), not as a fraction. '
  'The 1..100 band admits the scaled encoding and rejects a fractional one.';
COMMENT ON CONSTRAINT coverage_pool_vocab ON provenance.coverage IS
  'coverage spells the joint pool "both (E2E)" whereas runs spells it "both". Both '
  'spellings legitimately exist in the store and both are admitted deliberately.';

-- =====================================================================
-- HOW TO USE
-- =====================================================================
--   SELECT * FROM provenance.check_all();                       -- everything
--   SELECT * FROM provenance.check_all(NULL, 'cheap');          -- fast subset
--   SELECT * FROM provenance.check_all('error');                -- only the ones that matter
--   SELECT * FROM provenance.check_failures('moderate');        -- just what is broken
--   SELECT * FROM provenance.check_run('a11:burst1_fc_timesfm_L60');
--   SELECT * FROM provenance.recompute_p99('a13:ft_llm_static', 'ttft_ms');
--   SELECT * FROM provenance.recompute_quantile('a13:ft_llm_static','e2e_latency_ms',0.90);
--
-- After every load, at minimum:
--   SELECT * FROM provenance.check_failures('cheap');
-- C301 (run_id injectivity), C601 (default partitions) and C603 (partition
-- exists) are the three that catch a destructive load while it is still cheap
-- to fix.
-- =====================================================================
