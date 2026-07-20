-- =====================================================================
-- 20_semantic.sql  --  SEMANTIC VIEW LAYER + PROJECTIONS
-- =====================================================================
--
-- Purpose
--   The base tables in `provenance` are deliberately byte-faithful to the
--   artifacts that produced them: a column is named whatever the JSON key
--   was called, in whatever unit the producer emitted. That is the right
--   property for a provenance store (an ingested row can always be diffed
--   against its source file) but it is the wrong property for an analyst,
--   because the same concept arrives under many names and occasionally in
--   two different units in the same table.
--
--   This file adds a NORMALIZING VIEW LAYER on top. Nothing here renames a
--   base column, adds a constraint, or writes a row. Renaming in place
--   would break the loaders in provenance/loader/, which address columns by
--   their artifact-native names; normalizing in views costs nothing and is
--   reversible.
--
-- What the audit (lens B) found, and what is normalized here
--   * encoder worker count appears under 7 spellings:
--       encoder_workers, config_c, c_star, c_star_corrected, c_star_effective,
--       cstar, n_workers, worker_count, static_encoder_workers,
--       optimal_encoder_workers
--     -> canonical: encoder_workers (integer, count of encoder workers)
--   * provisioned worker-seconds appears under 6 spellings, one of them the
--     bare `ws`:
--       provisioned_worker_seconds, provisioned_ws, ws, static_worker_s,
--       fc_worker_s, static_ws
--     -> canonical: provisioned_worker_seconds (double, unit: worker-seconds)
--   * `verification`'s four latency columns (enc_p99, enc_max, ttft_p99,
--     itl_p99) carry NO unit in the name and had zero column comments. They
--     are MILLISECONDS (empirically confirmed: mean enc_p99 = 855.7,
--     mean ttft_p99 = 2693.9, mean itl_p99 = 46.1 -- ms-scale, not s-scale).
--     -> exposed here only as *_ms.
--   * `measured_request` stores TTFT TWICE: `ttft_server` in SECONDS and
--     `ttft_server_ms` in MILLISECONDS, and the seconds column is unlabelled.
--     (Confirmed: avg ttft_server = 0.4746 s, avg ttft_server_ms = 474.55 ms,
--     over the same 7,817 rows.) -> only the ms form is exposed.
--   * vocabulary drift: engine 'vLLM' vs 'vllm'; resolution '1min' vs '60s';
--     pool 'both (E2E)' vs 'both'; window alias 'week' vs 'aggregate'.
--     -> folded to one spelling per concept.
--
-- Conventions adopted by every view in this file
--   * Every latency/duration column ends in _ms and IS milliseconds.
--   * Every cost column ends in _worker_seconds or _gpu_hours and IS that unit.
--   * Every ratio column ends in _ratio and is dimensionless.
--   * Any column whose value is a *proxy* or a *joined* quantity rather than
--     a directly measured one says so in its COMMENT and, where it could be
--     misread as arithmetic, in a sibling boolean/text column.
--
-- Safe to run repeatedly: every statement is CREATE OR REPLACE.
-- Depends on: 01_schema.sql, 02_views.sql (v_window_alias,
--             v_grid_c_star_effective, v_grid_static_effective).
-- =====================================================================


-- ---------------------------------------------------------------------
-- 0. SUPPORT: the synonym dictionary, as data
-- ---------------------------------------------------------------------
-- Machine-readable record of the drift. This exists so that "which column
-- do I actually want?" is a query rather than a grep, and so that a future
-- schema cut can be driven from it.

CREATE OR REPLACE VIEW provenance.v_dim_synonym AS
SELECT * FROM (VALUES
  ('encoder_workers','count',        'encoder_run_summary','encoder_workers',            'per-run nominal worker count (static runs)'),
  ('encoder_workers','count',        'runs',               'config_c',                   'planned C for the run; NULL when autoscaled'),
  ('encoder_workers','count',        'grid_window',        'c_star',                     'SLA-minimal C for the window, as ingested'),
  ('encoder_workers','count',        'grid_window',        'c_star_corrected',           'post-hoc corrected C*; prefer v_grid_c_star_effective'),
  ('encoder_workers','count',        'grid_run_summary',   'static_encoder_workers',     'one static C covering all windows (max over C*)'),
  ('encoder_workers','count',        'worker_schedule',    'worker_count',               'time-varying C(t); integrate for cost'),
  ('encoder_workers','count',        'sweep_point',        'encoder_workers',            'swept C'),
  ('encoder_workers','count',        'grid_vision_point',  'encoder_workers',            'swept C inside the grid'),
  ('encoder_workers','count',        'collector_closedloop_window','static_c',           'silicon-anchored static C'),
  ('encoder_workers','count',        'collector_anchor_window_engine','cstar',           'bare spelling'),
  ('encoder_workers','count',        'collector_multiworker_p99','n_workers',            'bare spelling'),
  ('provisioned_worker_seconds','worker-seconds','encoder_run_summary','provisioned_worker_seconds','canonical spelling'),
  ('provisioned_worker_seconds','worker-seconds','factorial_cell',     'provisioned_ws', 'abbreviated'),
  ('provisioned_worker_seconds','worker-seconds','cost_accounting',    'provisioned_ws', 'abbreviated; excludes warm-up (see warmup_ws)'),
  ('provisioned_worker_seconds','worker-seconds','verification',       'provisioned_ws', 'abbreviated'),
  ('provisioned_worker_seconds','worker-seconds','ewma_ablation_cell', 'ws',             'BARE -- no unit, no concept, in the name'),
  ('provisioned_worker_seconds','worker-seconds','collector_closedloop_window','fc_worker_s','forecast arm; _s suffix means seconds-of-worker not seconds'),
  ('provisioned_worker_seconds','worker-seconds','collector_closedloop_window','static_worker_s','static arm; same caveat'),
  ('encoder_delay_p99_ms','ms',      'encoder_run_summary','encoder_delay_p99_ms',       'canonical'),
  ('encoder_delay_p99_ms','ms',      'verification',       'enc_p99',                    'UNLABELLED unit; is ms'),
  ('encoder_delay_p99_ms','ms',      'sweep_point',        'enc_delay_p99_ms',           'abbreviated stem'),
  ('encoder_delay_p99_ms','ms',      'grid_vision_point',  'delay_p99_ms',               'abbreviated stem'),
  ('ttft_p99_ms','ms',               'llm_run_summary',    'p99_ttft_ms',                'stat-first word order'),
  ('ttft_p99_ms','ms',               'sweep_point',        'ttft_p99_ms',                'metric-first word order (canonical)'),
  ('ttft_p99_ms','ms',               'verification',       'ttft_p99',                   'UNLABELLED unit; is ms'),
  ('ttft_p99_ms','ms',               'cost_model_variant', 'p99_ttft_ms',                'stat-first word order'),
  ('ttft_ms','ms',                   'measured_request',   'ttft_server_ms',             'canonical of the duplicated pair'),
  ('ttft_ms','ms',                   'measured_request',   'ttft_server',                'SAME QUANTITY IN SECONDS; unlabelled; do not mix'),
  ('itl_p99_ms','ms',                'llm_run_summary',    'p99_itl_ms',                 'stat-first word order'),
  ('itl_p99_ms','ms',                'verification',       'itl_p99',                    'UNLABELLED unit; is ms'),
  ('queue_divergent','bool',         'encoder_run_summary','queue_divergent',            'canonical'),
  ('queue_divergent','bool',         'ewma_ablation_cell', 'divergent',                  'stem dropped')
) AS t(concept, canonical_unit, source_table, source_column, note);

COMMENT ON VIEW provenance.v_dim_synonym IS
$$Dictionary of naming/unit drift across the provenance base tables: one row per
(concept, physical column) pair, with the canonical unit for the concept.

This is documentation-as-data. The base tables stay byte-faithful to their source
artifacts, so the same concept genuinely does appear under many column names; this
view is how you find them all without grepping the DDL. It is hand-maintained --
add a row when a new family lands with yet another spelling.

Worked example -- every physical column that holds provisioned worker-seconds,
which is the concept with the worst drift (6 spellings, one of them the bare `ws`):

    SELECT source_table, source_column, note
      FROM provenance.v_dim_synonym
     WHERE concept = 'provisioned_worker_seconds'
     ORDER BY source_table;

Worked example -- find every concept that is stored under more than one unit or
name, i.e. the places where a naive join across families will silently disagree:

    SELECT concept, canonical_unit, count(*) AS n_spellings
      FROM provenance.v_dim_synonym
     GROUP BY 1,2 HAVING count(*) > 1
     ORDER BY n_spellings DESC;$$;

COMMENT ON COLUMN provenance.v_dim_synonym.concept IS
  'Canonical concept name. Use this name in new views and in prose.';
COMMENT ON COLUMN provenance.v_dim_synonym.canonical_unit IS
  'The ONE unit the concept is expressed in throughout this semantic layer. Where a base column uses a different unit (measured_request.ttft_server, seconds) the note says so.';
COMMENT ON COLUMN provenance.v_dim_synonym.note IS
  'Why this spelling differs, and any trap attached to it.';


-- ---------------------------------------------------------------------
-- 1. CANONICAL DIMENSION VIEW
-- ---------------------------------------------------------------------
-- One row per run_id. One name and one unit per dimension, with the
-- vocabulary drift folded away. This is the spine every other view in this
-- file joins to, and the thing to GROUP BY.

CREATE OR REPLACE VIEW provenance.v_dim AS
SELECT
    r.run_id,
    r.experiment,

    -- pool: fold 'both (E2E)' (the spelling used in `coverage`) onto 'both'
    CASE lower(coalesce(r.pool,''))
      WHEN 'both (e2e)' THEN 'both'
      WHEN ''           THEN NULL
      ELSE lower(r.pool)
    END                                                    AS pool,

    r.window_name                                          AS window_name_raw,
    -- canonical window: 'week' is an alias of 'aggregate' (confirmed by
    -- windows.aggregate.requests = 749601 matching every composed_e2e week row)
    coalesce(a.canonical_window, r.window_name)            AS window_name,
    w.span_s                                               AS window_span_s,
    w.requests                                             AS window_requests,

    r.policy,
    r.model                                                AS forecast_model,
    r.quantile,
    r.lead_s,
    r.cold_start_s,
    r.hysteresis_min,
    r.rho,
    r.actuation,

    -- resolution: '1min' and '60s' are the same thing
    CASE r.resolution WHEN '1min' THEN '60s' ELSE r.resolution END AS resolution,

    -- engine: 'vLLM' vs 'vllm' -- a case-sensitive filter on the former
    -- silently returns nothing for half the corpus
    lower(r.engine)                                        AS engine,
    r.gpu,
    r.tp,
    r.n_replicas,

    -- CANONICAL encoder worker count. Static runs carry it on the summary;
    -- planned runs carry it as runs.config_c. NULL means the run autoscaled
    -- and has no single worker count -- use worker_schedule / v_pool_cost.
    coalesce(es.encoder_workers, r.config_c)               AS encoder_workers,
    (coalesce(es.encoder_workers, r.config_c) IS NULL)     AS encoder_workers_is_timevarying,

    r.is_current,
    r.kind,
    r.source_path,
    r.superseded_by
FROM provenance.runs r
LEFT JOIN provenance.v_window_alias a
       ON a.alias = r.window_name AND a.canonical_window IS NOT NULL
LEFT JOIN provenance.windows w
       ON w.window_name = coalesce(a.canonical_window, r.window_name)
LEFT JOIN provenance.encoder_run_summary es
       ON es.run_id = r.run_id;

COMMENT ON VIEW provenance.v_dim IS
$$Canonical dimension spine: one row per run_id, one name and one unit per concept.

Folds away the vocabulary drift catalogued in v_dim_synonym:
  * pool     -- 'both (E2E)' -> 'both', lowercased
  * engine   -- 'vLLM' -> 'vllm' (a case-sensitive = 'vllm' filter on the base
                table silently drops every run ingested with the capitalised form)
  * resolution -- '1min' -> '60s'
  * window_name -- the alias 'week' resolves to 'aggregate'; window_name_raw
                keeps the as-ingested value so the fold is auditable
  * encoder_workers -- ONE column for a concept the store spells 7 ways

Join every other semantic view to this one rather than to `runs` directly.

Worked example -- the runs that make up the forecast-vs-reactive comparison on
the aggregate window, with their canonical dimensions:

    SELECT run_id, policy, forecast_model, lead_s, quantile, encoder_workers
      FROM provenance.v_dim
     WHERE window_name = 'aggregate' AND pool = 'encoder' AND is_current
     ORDER BY policy, forecast_model, lead_s;

Worked example -- prove the engine fold matters (the second count is the one
a naive query would get):

    SELECT count(*) FILTER (WHERE engine = 'vllm') AS canonical_hits
      FROM provenance.v_dim;
    SELECT count(*) FILTER (WHERE engine = 'vllm') AS naive_hits
      FROM provenance.runs;$$;

COMMENT ON COLUMN provenance.v_dim.pool IS
  'Which serving pool the run measures: encoder | language | both. Lowercased, and the coverage-table spelling ''both (E2E)'' is folded to ''both''.';
COMMENT ON COLUMN provenance.v_dim.window_name IS
  'Canonical trace window. The alias ''week'' is resolved to ''aggregate''; see v_window_alias for the evidence and for aliases that do NOT resolve (head2k).';
COMMENT ON COLUMN provenance.v_dim.window_name_raw IS
  'As-ingested window name, kept so the alias fold can be audited. Differs from window_name only for aliases.';
COMMENT ON COLUMN provenance.v_dim.window_span_s IS
  'Wall-clock span of the window in SECONDS, from windows.span_s. This is the multiplier that turns a worker count into worker-seconds; NULL for windows never registered in windows() (e.g. head2k).';
COMMENT ON COLUMN provenance.v_dim.encoder_workers IS
  'CANONICAL encoder worker count (unit: workers). coalesce(encoder_run_summary.encoder_workers, runs.config_c). NULL means the run autoscaled and has no single worker count -- read the integral from v_pool_cost.provisioned_worker_seconds instead, never assume a constant.';
COMMENT ON COLUMN provenance.v_dim.encoder_workers_is_timevarying IS
  'TRUE when encoder_workers is NULL because C varied over the run. Makes the NULL explicit rather than ambiguous with "not recorded".';
COMMENT ON COLUMN provenance.v_dim.engine IS
  'Lowercased engine name. The base column carries both ''vLLM'' and ''vllm''.';
COMMENT ON COLUMN provenance.v_dim.resolution IS
  'Control-loop resolution. ''1min'' is folded to ''60s''.';
COMMENT ON COLUMN provenance.v_dim.is_current IS
  'FALSE when the run has been superseded by a later re-run; see superseded_by. Filter on this for any published number.';


-- ---------------------------------------------------------------------
-- 2. v_pool_latency
-- ---------------------------------------------------------------------
-- Per run and per (pool, window, policy, model, lead): the quantiles of the
-- pool's OWN SLA metric. Long-form: one row per (run_id, sla_metric), so
-- the encoder's delay and the language pool's TTFT and ITL never end up in
-- the same column and never have to share a unit assumption.

CREATE OR REPLACE VIEW provenance.v_pool_latency AS
-- encoder pool: the SLA metric is queueing delay before encode
SELECT
    d.run_id, d.experiment, d.pool, d.window_name, d.policy,
    d.forecast_model, d.lead_s, d.quantile, d.encoder_workers, d.is_current,
    'encoder_delay'::text                AS sla_metric,
    s.encoder_delay_p50_ms               AS p50_ms,
    s.encoder_delay_p90_ms               AS p90_ms,
    s.encoder_delay_p99_ms               AS p99_ms,
    s.encoder_delay_max_ms               AS max_ms,
    s.requests                           AS n_requests,
    s.queue_divergent,
    'encoder_run_summary'::text          AS source_relation
FROM provenance.encoder_run_summary s
JOIN provenance.v_dim d ON d.run_id = s.run_id

UNION ALL

-- language pool, metric 1: time to first token
SELECT
    d.run_id, d.experiment, d.pool, d.window_name, d.policy,
    d.forecast_model, d.lead_s, d.quantile, d.encoder_workers, d.is_current,
    'ttft'::text                         AS sla_metric,
    l.median_ttft_ms                     AS p50_ms,
    l.p90_ttft_ms                        AS p90_ms,
    l.p99_ttft_ms                        AS p99_ms,
    l.max_ttft_ms                        AS max_ms,
    l.completed_requests                 AS n_requests,
    NULL::boolean                        AS queue_divergent,
    'llm_run_summary'::text              AS source_relation
FROM provenance.llm_run_summary l
JOIN provenance.v_dim d ON d.run_id = l.run_id

UNION ALL

-- language pool, metric 2: inter-token latency.
-- NOTE the asymmetry: llm_run_summary stores only mean and p99 for ITL, so
-- p50/p90/max are genuinely absent, not zero.
SELECT
    d.run_id, d.experiment, d.pool, d.window_name, d.policy,
    d.forecast_model, d.lead_s, d.quantile, d.encoder_workers, d.is_current,
    'itl'::text                          AS sla_metric,
    NULL::double precision               AS p50_ms,
    NULL::double precision               AS p90_ms,
    l.p99_itl_ms                         AS p99_ms,
    NULL::double precision               AS max_ms,
    l.completed_requests                 AS n_requests,
    NULL::boolean                        AS queue_divergent,
    'llm_run_summary'::text              AS source_relation
FROM provenance.llm_run_summary l
JOIN provenance.v_dim d ON d.run_id = l.run_id
WHERE l.p99_itl_ms IS NOT NULL;

COMMENT ON VIEW provenance.v_pool_latency IS
$$Latency quantiles for each pool's OWN SLA metric, in MILLISECONDS, long-form.

One row per (run_id, sla_metric). sla_metric is:
  'encoder_delay' -- vision pool: queueing delay before encode (encoder_run_summary)
  'ttft'          -- language pool: time to first token (llm_run_summary)
  'itl'           -- language pool: inter-token latency (llm_run_summary)

Long form rather than a wide row is deliberate: the two pools do not share an SLA
metric, and putting encoder delay and TTFT in one row invites averaging them.

Unit is in every column name and is ms throughout. The base tables disagree on
word order (p99_ttft_ms vs ttft_p99_ms) and `verification` omits the unit entirely;
here there is one spelling.

CAVEAT -- ITL rows carry only p99_ms. llm_run_summary stores mean and p99 for ITL
and nothing else, so p50/p90/max are NULL because they were never computed, NOT
because they are zero.

Worked example -- did the encoder pool hold its 1000 ms p99 SLA on each window,
for the current forecast runs:

    SELECT window_name, forecast_model, lead_s, p99_ms, max_ms
      FROM provenance.v_pool_latency
     WHERE sla_metric = 'encoder_delay' AND policy = 'forecast' AND is_current
     ORDER BY p99_ms DESC
     LIMIT 20;

Worked example -- both language metrics side by side for one run:

    SELECT sla_metric, p50_ms, p90_ms, p99_ms, max_ms, n_requests
      FROM provenance.v_pool_latency
     WHERE run_id = (SELECT run_id FROM provenance.v_dim
                      WHERE pool = 'language' AND is_current LIMIT 1)
       AND sla_metric IN ('ttft','itl');$$;

COMMENT ON COLUMN provenance.v_pool_latency.sla_metric IS
  'Which SLA metric this row reports: encoder_delay (vision pool) | ttft | itl (language pool). Always filter on it -- rows for different metrics are not comparable.';
COMMENT ON COLUMN provenance.v_pool_latency.p99_ms IS
  '99th percentile of sla_metric, MILLISECONDS. The headline SLA quantity for all three metrics.';
COMMENT ON COLUMN provenance.v_pool_latency.max_ms IS
  'Worst observed value, MILLISECONDS. NULL for sla_metric=''itl'' (never computed by the producer).';
COMMENT ON COLUMN provenance.v_pool_latency.p50_ms IS
  'Median of sla_metric, MILLISECONDS. NULL for sla_metric=''itl''. For ttft this is llm_run_summary.median_ttft_ms.';
COMMENT ON COLUMN provenance.v_pool_latency.queue_divergent IS
  'Encoder rows only: TRUE when the encode queue never drained, i.e. the run is unstable and its percentiles are lower bounds on an unbounded quantity. NULL for language rows (concept does not apply).';
COMMENT ON COLUMN provenance.v_pool_latency.n_requests IS
  'Requests underpinning the quantiles: encoder_run_summary.requests, or llm_run_summary.completed_requests. Small n makes a p99 unreliable -- check it before quoting.';
COMMENT ON COLUMN provenance.v_pool_latency.source_relation IS
  'Base table the row came from, so any number here can be traced back without reading this DDL.';


-- ---------------------------------------------------------------------
-- 3. v_pool_cost
-- ---------------------------------------------------------------------
-- Provisioned and busy worker-seconds, utilization, GPU-hours, and -- where
-- cost_accounting has it -- the cold-start / warm-up component that
-- provisioned_worker_seconds alone does NOT include.

CREATE OR REPLACE VIEW provenance.v_pool_cost AS
-- encoder pool
SELECT
    d.run_id, d.experiment, d.pool, d.window_name, d.policy,
    d.forecast_model, d.lead_s, d.quantile, d.cold_start_s,
    d.encoder_workers, d.encoder_workers_is_timevarying,
    d.window_span_s, d.is_current,

    s.provisioned_worker_seconds,
    s.busy_worker_seconds,
    coalesce(s.encoder_utilization,
             nullif(s.busy_worker_seconds,0) / nullif(s.provisioned_worker_seconds,0))
                                                     AS utilization_ratio,
    NULL::double precision                           AS gpu_hours,

    ca.warmup_ws                                     AS warmup_worker_seconds,
    ca.total_from_order_ws                           AS total_from_order_worker_seconds,
    ca.warmup_frac                                   AS warmup_fraction,
    (ca.window_name IS NOT NULL)                     AS has_cold_start_accounting,

    'encoder_run_summary'::text                      AS source_relation
FROM provenance.encoder_run_summary s
JOIN provenance.v_dim d ON d.run_id = s.run_id
LEFT JOIN provenance.cost_accounting ca
       ON ca.window_name = d.window_name
      AND ca.policy      = d.policy
      AND ca.lead_s IS NOT DISTINCT FROM d.lead_s

UNION ALL

-- language pool: cost is GPU-hours plus the prefill/decode worker-second split
SELECT
    d.run_id, d.experiment, d.pool, d.window_name, d.policy,
    d.forecast_model, d.lead_s, d.quantile, d.cold_start_s,
    d.encoder_workers, d.encoder_workers_is_timevarying,
    d.window_span_s, d.is_current,

    (coalesce(l.prefill_worker_seconds,0) + coalesce(l.decode_worker_seconds,0))
        AS provisioned_worker_seconds,
    NULL::double precision                           AS busy_worker_seconds,
    NULL::double precision                           AS utilization_ratio,
    l.gpu_hours,

    NULL::double precision                           AS warmup_worker_seconds,
    NULL::double precision                           AS total_from_order_worker_seconds,
    NULL::double precision                           AS warmup_fraction,
    FALSE                                            AS has_cold_start_accounting,

    'llm_run_summary'::text                          AS source_relation
FROM provenance.llm_run_summary l
JOIN provenance.v_dim d ON d.run_id = l.run_id
WHERE l.prefill_worker_seconds IS NOT NULL
   OR l.decode_worker_seconds  IS NOT NULL
   OR l.gpu_hours              IS NOT NULL;

COMMENT ON VIEW provenance.v_pool_cost IS
$$Cost of each run, per pool, in ONE unit per concept: worker-seconds and GPU-hours.

Canonicalises the 6 spellings of provisioned worker-seconds (provisioned_ws, ws,
static_worker_s, fc_worker_s, ...) onto provisioned_worker_seconds.

WHAT provisioned_worker_seconds DOES NOT INCLUDE: it is the integral of the served
worker count over the run. It excludes workers paid for during cold start / warm-up
before they could serve. Where cost_accounting covers the (window, policy, lead_s)
cell, that component is exposed separately as warmup_worker_seconds, and
total_from_order_worker_seconds is the from-order-to-release total. Check
has_cold_start_accounting before concluding warm-up was zero -- it is NULL/absent
for most runs (cost_accounting has 40 rows), which means unmeasured, not free.

ENCODER vs LANGUAGE asymmetry is real, not an oversight:
  encoder  -- provisioned/busy worker-seconds and utilization; no GPU-hours
  language -- gpu_hours and prefill+decode worker-seconds; no busy time, so
              utilization_ratio is NULL

Worked example -- cost and utilization of the current encoder runs on burst1,
cheapest first:

    SELECT run_id, policy, forecast_model, lead_s,
           provisioned_worker_seconds, busy_worker_seconds,
           round(utilization_ratio::numeric, 3) AS util
      FROM provenance.v_pool_cost
     WHERE window_name = 'burst1' AND pool = 'encoder' AND is_current
     ORDER BY provisioned_worker_seconds;

Worked example -- how much of the true bill the headline cost omits, wherever
cold-start accounting exists:

    SELECT window_name, policy, lead_s,
           provisioned_worker_seconds, warmup_worker_seconds,
           round(warmup_fraction::numeric, 4) AS warmup_frac
      FROM provenance.v_pool_cost
     WHERE has_cold_start_accounting
     ORDER BY warmup_fraction DESC NULLS LAST;$$;

COMMENT ON COLUMN provenance.v_pool_cost.provisioned_worker_seconds IS
  'CANONICAL provisioned cost, unit WORKER-SECONDS: integral of served worker count over the run. Encoder: encoder_run_summary.provisioned_worker_seconds. Language: prefill_worker_seconds + decode_worker_seconds. EXCLUDES cold-start/warm-up -- see warmup_worker_seconds.';
COMMENT ON COLUMN provenance.v_pool_cost.busy_worker_seconds IS
  'Worker-seconds actually spent executing, unit WORKER-SECONDS. Always <= provisioned_worker_seconds. NULL for the language pool (not measured).';
COMMENT ON COLUMN provenance.v_pool_cost.utilization_ratio IS
  'busy / provisioned, dimensionless in [0,1]. Taken from encoder_utilization when present, otherwise recomputed. NULL for the language pool because busy time is not measured there.';
COMMENT ON COLUMN provenance.v_pool_cost.gpu_hours IS
  'GPU-hours, language pool only. Not derivable from encoder worker-seconds without a workers-per-GPU assumption, so it is deliberately NULL for encoder rows rather than guessed.';
COMMENT ON COLUMN provenance.v_pool_cost.warmup_worker_seconds IS
  'Worker-seconds paid during cold start before the worker could serve, unit WORKER-SECONDS, from cost_accounting.warmup_ws. NULL means UNMEASURED, not zero -- gate on has_cold_start_accounting.';
COMMENT ON COLUMN provenance.v_pool_cost.total_from_order_worker_seconds IS
  'From-order-to-release total, unit WORKER-SECONDS (cost_accounting.total_from_order_ws). This is the honest bill: roughly provisioned + warmup.';
COMMENT ON COLUMN provenance.v_pool_cost.has_cold_start_accounting IS
  'TRUE when a cost_accounting row matched this run''s (window, policy, lead_s). When FALSE the warm-up columns are NULL because nothing measured them.';
COMMENT ON COLUMN provenance.v_pool_cost.warmup_fraction IS
  'warmup_ws / total_from_order_ws, dimensionless: share of the true bill spent on workers that were not yet serving. NULL unless has_cold_start_accounting.';
COMMENT ON COLUMN provenance.v_pool_cost.source_relation IS
  'Base table the cost came from: encoder_run_summary or llm_run_summary. THIS, not pool, is the correct predicate for selecting encoder costs -- 372 runs carry encoder_run_summary rows while being labelled pool = ''both'', and filtering on pool would drop them.';
COMMENT ON COLUMN provenance.v_pool_cost.window_span_s IS
  'Window wall-clock span in SECONDS. The multiplier that converts a static worker count into comparable worker-seconds; NULL windows cannot be cost-ratioed.';
COMMENT ON COLUMN provenance.v_pool_cost.encoder_workers_is_timevarying IS
  'TRUE when the run autoscaled, so there is no single worker count and provisioned_worker_seconds is the only meaningful cost figure.';


-- ---------------------------------------------------------------------
-- 4. v_infraction  --  SLA INTENSITY, not a boolean
-- ---------------------------------------------------------------------
-- The store currently answers "did this run fail its SLA". It does not
-- answer "by how much" or "for how long". A run that exceeds a 1000 ms p99
-- by 3 ms for two seconds and a run that exceeds it by 24000 ms for twenty
-- minutes are both `feasible = false`. This view separates them.
--
-- Where per-request raw data exists (llm_request) the duration and worst
-- excursion are computed from it. Where it does not, those columns are NULL
-- and raw_backing says so.

CREATE OR REPLACE VIEW provenance.v_sla_bound AS
SELECT * FROM (VALUES
  ('encoder_delay', 1000.0::double precision, 'p99', 'grid_run_summary.sla_vision_p99_ms'),
  ('ttft',          1000.0::double precision, 'p99', 'grid_run_summary.sla_llm_ttft_p99_ms'),
  ('itl',            100.0::double precision, 'p99', 'grid_run_summary.sla_llm_itl_p99_ms')
) AS t(sla_metric, bound_ms, bound_stat, bound_source);

COMMENT ON VIEW provenance.v_sla_bound IS
$$The three SLA bounds the thesis is written against, in MILLISECONDS, in one place.

Values mirror the single grid_run_summary row (grid:grid_summary):
  encoder_delay p99 <= 1000 ms
  ttft          p99 <= 1000 ms
  itl           p99 <=  100 ms

Held as a VALUES list rather than selected from grid_run_summary so that the
bounds a run is judged against cannot silently change if the grid is re-ingested.
Cross-check them at any time:

    SELECT sla_vision_p99_ms, sla_llm_ttft_p99_ms, sla_llm_itl_p99_ms
      FROM provenance.grid_run_summary;$$;

COMMENT ON COLUMN provenance.v_sla_bound.bound_ms IS
  'SLA threshold, MILLISECONDS. A run is compliant when the bound_stat quantile of sla_metric is <= this.';
COMMENT ON COLUMN provenance.v_sla_bound.bound_stat IS
  'Which statistic the bound applies to -- p99 for all three. The bound is NOT on the mean or the max.';


CREATE OR REPLACE VIEW provenance.v_infraction AS
SELECT
    pl.run_id, pl.experiment, pl.pool, pl.window_name, pl.policy,
    pl.forecast_model, pl.lead_s, pl.quantile, pl.encoder_workers, pl.is_current,
    pl.sla_metric,

    b.bound_ms,
    b.bound_stat,
    pl.p99_ms                                   AS achieved_p99_ms,
    pl.max_ms                                   AS achieved_max_ms,

    (pl.p99_ms > b.bound_ms)                    AS is_violation,

    -- INTENSITY: how far past the line, absolutely and relatively
    greatest(pl.p99_ms - b.bound_ms, 0)         AS overage_abs_ms,
    CASE WHEN b.bound_ms > 0
         THEN greatest(pl.p99_ms - b.bound_ms, 0) / b.bound_ms END
                                                AS overage_ratio,
    CASE WHEN b.bound_ms > 0 AND pl.max_ms IS NOT NULL
         THEN greatest(pl.max_ms - b.bound_ms, 0) / b.bound_ms END
                                                AS worst_excursion_ratio,

    -- DURATION and worst excursion from per-request raw data, language pool only
    raw.n_requests_raw,
    raw.n_requests_over_bound,
    CASE WHEN raw.n_requests_raw > 0
         THEN raw.n_requests_over_bound::double precision / raw.n_requests_raw END
                                                AS fraction_requests_over_bound,
    raw.violation_seconds,
    raw.observed_span_s,
    CASE WHEN raw.observed_span_s > 0
         THEN raw.violation_seconds::double precision / raw.observed_span_s END
                                                AS fraction_time_in_violation,
    raw.worst_request_ms,
    CASE WHEN raw.worst_request_ms IS NOT NULL
         THEN raw.worst_request_ms - b.bound_ms END
                                                AS worst_request_overage_ms,

    (raw.n_requests_raw IS NOT NULL)            AS has_raw_backing,
    pl.queue_divergent,
    pl.n_requests
FROM provenance.v_pool_latency pl
JOIN provenance.v_sla_bound b USING (sla_metric)
LEFT JOIN LATERAL (
    SELECT
        count(*)                                              AS n_requests_raw,
        count(*) FILTER (WHERE l.ttft_ms > b.bound_ms)         AS n_requests_over_bound,
        count(DISTINCT floor(l.arrival_time_ms / 1000.0))
            FILTER (WHERE l.ttft_ms > b.bound_ms)              AS violation_seconds,
        (max(l.arrival_time_ms) - min(l.arrival_time_ms)) / 1000.0 AS observed_span_s,
        max(l.ttft_ms)                                        AS worst_request_ms
    FROM provenance.llm_request l
    WHERE l.run_id = pl.run_id
) raw ON pl.sla_metric = 'ttft';

COMMENT ON VIEW provenance.v_infraction IS
$$SLA INTENSITY per run and metric: not just whether the bound was missed, but by
how much, for what fraction of requests, and for how long.

The gap this fills: the store's existing feasibility flags (factorial_cell.feasible,
grid_vision_point.feasible, sweep_point.over_threshold) are booleans. They cannot
distinguish a run that overshot a 1000 ms p99 by 3 ms from one that overshot it by
24 seconds, and they say nothing about duration. Both matter for an SLA argument.

Columns come in three tiers:
  1. ALWAYS PRESENT -- bound_ms, achieved_p99_ms, is_violation, overage_abs_ms,
     overage_ratio. Derived from summary quantiles alone.
  2. PRESENT WHEN max WAS RECORDED -- worst_excursion_ratio.
  3. PRESENT ONLY WITH PER-REQUEST RAW DATA -- violation_seconds,
     fraction_time_in_violation, fraction_requests_over_bound, worst_request_ms.
     These come from provenance.llm_request and therefore exist ONLY for
     sla_metric = 'ttft'. has_raw_backing tells you which rows have them.

WHY NOT FOR THE ENCODER: encoder_series is per-second occupancy (queue depth,
busy workers), not per-request delay. There is no stored per-request encoder delay,
so a true time-in-violation cannot be computed for the vision pool. Queue depth is
NOT substituted as a proxy -- a deep queue is a cause of delay, not a measurement
of it, and dressing it up as one would be the exact error this view exists to
prevent. Those rows carry has_raw_backing = FALSE.

PERFORMANCE: the raw tier is a LATERAL over llm_request (15.6M rows) keyed on the
run_id index. Filter by run_id / window_name / experiment. An unfiltered
SELECT * walks the whole table.

Worked example -- rank the encoder-pool SLA misses by severity rather than
listing them as equally "infeasible":

    SELECT window_name, policy, forecast_model, lead_s,
           achieved_p99_ms, bound_ms,
           round(overage_abs_ms::numeric, 1) AS over_ms,
           round((100 * overage_ratio)::numeric, 1) AS over_pct
      FROM provenance.v_infraction
     WHERE sla_metric = 'encoder_delay' AND is_violation AND is_current
     ORDER BY overage_ratio DESC
     LIMIT 20;

Worked example -- for one language run, how bad and for how long:

    SELECT run_id, achieved_p99_ms, bound_ms,
           n_requests_over_bound, fraction_requests_over_bound,
           violation_seconds, observed_span_s,
           round((100 * fraction_time_in_violation)::numeric, 2) AS pct_time_bad,
           worst_request_ms, worst_request_overage_ms
      FROM provenance.v_infraction
     WHERE sla_metric = 'ttft' AND run_id = 'factorial:...'   -- always filter
       AND has_raw_backing;

Worked example -- marginal vs catastrophic misses (the distinction the boolean
flags destroy):

    SELECT CASE WHEN overage_ratio <= 0.05 THEN 'marginal (<=5%)'
                WHEN overage_ratio <= 0.50 THEN 'moderate'
                ELSE 'catastrophic (>50%)' END AS severity,
           count(*)
      FROM provenance.v_infraction
     WHERE is_violation AND is_current
     GROUP BY 1 ORDER BY 2 DESC;$$;

COMMENT ON COLUMN provenance.v_infraction.bound_ms IS
  'The SLA threshold this row is judged against, MILLISECONDS, from v_sla_bound.';
COMMENT ON COLUMN provenance.v_infraction.achieved_p99_ms IS
  'The run''s achieved p99 of sla_metric, MILLISECONDS. Compared against bound_ms to give is_violation.';
COMMENT ON COLUMN provenance.v_infraction.is_violation IS
  'TRUE when achieved_p99_ms > bound_ms. This is the boolean the store already had; every other column here exists because this one is not enough.';
COMMENT ON COLUMN provenance.v_infraction.overage_abs_ms IS
  'achieved_p99_ms - bound_ms, floored at 0, MILLISECONDS. How far past the line, in absolute time.';
COMMENT ON COLUMN provenance.v_infraction.overage_ratio IS
  'overage_abs_ms / bound_ms, dimensionless. 0 = compliant, 0.05 = missed by 5%, 2.0 = three times the bound. Use this to rank severity across metrics with different bounds (encoder 1000 ms vs itl 100 ms).';
COMMENT ON COLUMN provenance.v_infraction.worst_excursion_ratio IS
  'Worst single observation relative to the bound: (max_ms - bound_ms) / bound_ms. Summary-level worst case; NULL when max was not recorded (all itl rows).';
COMMENT ON COLUMN provenance.v_infraction.violation_seconds IS
  'Number of distinct wall-clock SECONDS in which at least one request arrived that went on to breach the bound. Counted by request ARRIVAL second from llm_request.arrival_time_ms. This is a duration, not a count of requests. NULL unless has_raw_backing.';
COMMENT ON COLUMN provenance.v_infraction.observed_span_s IS
  'Span in SECONDS between first and last request arrival in the raw data, i.e. the denominator for fraction_time_in_violation. NULL unless has_raw_backing.';
COMMENT ON COLUMN provenance.v_infraction.fraction_time_in_violation IS
  'violation_seconds / observed_span_s, dimensionless. THE duration answer: 0.01 means the SLA was breached during 1% of the run''s wall clock. Distinguishes a brief spike from sustained failure.';
COMMENT ON COLUMN provenance.v_infraction.fraction_requests_over_bound IS
  'Share of individual requests exceeding bound_ms, dimensionless. Note this can exceed 0.01 while the p99 still passes, and vice versa -- they are different questions.';
COMMENT ON COLUMN provenance.v_infraction.worst_request_ms IS
  'Slowest single request in the raw data, MILLISECONDS (max of llm_request.ttft_ms). The true worst excursion, as opposed to the summary max.';
COMMENT ON COLUMN provenance.v_infraction.has_raw_backing IS
  'TRUE when per-request rows existed in llm_request and the duration/excursion columns are populated. FALSE for every encoder_delay and itl row -- see the view comment for why the encoder case is genuinely uncomputable rather than merely missing.';
COMMENT ON COLUMN provenance.v_infraction.sla_metric IS
  'Which SLA this row judges: encoder_delay | ttft | itl. Determines bound_ms, and determines whether the raw tier is populated (ttft only).';
COMMENT ON COLUMN provenance.v_infraction.bound_stat IS
  'The statistic the bound applies to -- p99 throughout. is_violation compares achieved_p99_ms, NOT the mean or max, against bound_ms.';
COMMENT ON COLUMN provenance.v_infraction.achieved_max_ms IS
  'Summary-level worst observation, MILLISECONDS. NULL for itl. For the raw-backed truth prefer worst_request_ms.';
COMMENT ON COLUMN provenance.v_infraction.n_requests_raw IS
  'Per-request rows found in llm_request for this run. The denominator of fraction_requests_over_bound. NULL unless has_raw_backing.';
COMMENT ON COLUMN provenance.v_infraction.n_requests_over_bound IS
  'Count of individual requests whose ttft_ms exceeded bound_ms. NULL unless has_raw_backing.';
COMMENT ON COLUMN provenance.v_infraction.worst_request_overage_ms IS
  'worst_request_ms - bound_ms, MILLISECONDS: how far the single worst request overshot. Can be large even when the p99 passes, since one request does not move a p99.';
COMMENT ON COLUMN provenance.v_infraction.n_requests IS
  'Requests underpinning the SUMMARY quantiles (from v_pool_latency). May differ from n_requests_raw, which counts rows actually present in llm_request -- a gap between them means the summary was computed over data not fully ingested.';
COMMENT ON COLUMN provenance.v_infraction.queue_divergent IS
  'Encoder rows: TRUE means the queue never drained, so achieved_p99_ms is a lower bound on an unbounded quantity and overage_ratio understates the failure.';


-- ---------------------------------------------------------------------
-- 5. v_joint_e2e
-- ---------------------------------------------------------------------
-- The composed picture per window: encoder delay and language TTFT beside
-- the request-linked composed end-to-end latency -- with an explicit column
-- stating that the E2E p99 is a JOIN over requests and NOT the sum of the
-- two per-pool p99s.

-- Dropped rather than replaced: CREATE OR REPLACE cannot insert a column into
-- the middle of an existing view's column list, and e2e_vs_sum_evidence sits
-- beside the column it qualifies. No other object depends on this view.
DROP VIEW IF EXISTS provenance.v_joint_e2e;
CREATE VIEW provenance.v_joint_e2e AS
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

    -- Does THIS row independently demonstrate the join, or does it merely
    -- coincide with the additive sum? Percentiles of two stages cannot in
    -- general be added, so a strict inequality is positive evidence of a real
    -- request-level join; equality is consistent with a join over two
    -- floor-pinned (near-deterministic) stage distributions, and is therefore
    -- uninformative rather than contradictory.
    CASE
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
    c.source_path
FROM provenance.composed_e2e c
LEFT JOIN provenance.v_window_alias a
       ON a.alias = c.window_name AND a.canonical_window IS NOT NULL;

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

READ THIS BEFORE CONCLUDING THE DATA IS ADDITIVE. 13 of the 20 composed_e2e rows
have e2e_p99_ms exactly equal to enc_p99_ms + ttft_p99_ms, which looks at first
glance like the sum was simply stored. It was not. The evidence, from the source
artifact defense/anim/data/a12_data.json:

  * 7 rows differ, and ALL 7 have e2e_p99_ms STRICTLY BELOW the sum -- never
    above (5 reactive arms: week 1695.9 vs 1780.0; burst1 2069.2 vs 2253.1;
    burst4 3064.0 vs 3395.4; burst3 21868.0 vs 26652.4; plus 2 forecast arms on
    burst1: timesfm 1258.4 vs 1259.7, toto 1259.2 vs 1260.0). A stored sum
    cannot be less than itself, and one-sided deviation is exactly what a real
    percentile-of-joined-latency produces. These rows are genuine joins.
  * The 13 coinciding rows are forecast arms on windows where the encoder is
    never saturated. Their stage p99s are pinned at the service floor (enc
    588.4, ttft 651.1) and are identical across windows of wildly different
    size. When both stage distributions are near-deterministic, the p99 of the
    sum equals the sum of the p99s -- arithmetic coincidence, not additive
    computation. Note the split is NOT policy-aligned: 2 forecast rows fall on
    the strictly-differing side, which is why the evidence is recorded per row
    rather than inferred from the arm.
  * The clincher: on those same forecast rows e2e_max_ms DOES vary by window
    (2185.8 / 2572.5 / 3735.3 / 38188.0). A hardcoded additive placeholder would
    not produce a per-window-varying max off the same distribution.

So the join is real throughout; e2e_vs_sum_evidence records, per row, whether that
row independently demonstrates it ('strictly_differs_from_sum') or is merely
consistent with it ('coincides_with_sum'). Do not read 'coincides_with_sum' as a
defect, and do not read it as confirmation either.

Worked example -- the composed picture per window, with the size of the
sum-of-percentiles error made visible:

    SELECT window_name, arm, forecast_model,
           encoder_delay_p99_ms, ttft_p99_ms, e2e_p99_ms,
           naive_sum_of_p99s_ms,
           round(naive_sum_minus_joined_ms::numeric, 1) AS error_ms,
           round(naive_sum_over_joined_ratio::numeric, 3) AS error_x
      FROM provenance.v_joint_e2e
     ORDER BY window_name, arm;

Worked example -- how wrong the additive assumption gets, worst case:

    SELECT window_name, arm,
           round(naive_sum_over_joined_ratio::numeric, 3) AS sum_over_true
      FROM provenance.v_joint_e2e
     WHERE naive_sum_over_joined_ratio IS NOT NULL
     ORDER BY abs(naive_sum_over_joined_ratio - 1) DESC
     LIMIT 10;$$;

COMMENT ON COLUMN provenance.v_joint_e2e.e2e_p99_ms IS
  'p99 of per-request composed end-to-end latency, MILLISECONDS. REQUEST-LINKED: the stages are joined on request identity before the percentile is taken. NOT the sum of the per-pool p99s.';
COMMENT ON COLUMN provenance.v_joint_e2e.e2e_p99_is_request_linked IS
  'Constant TRUE, present so the provenance of e2e_p99_ms travels with the row into any export, notebook or slide. If you ever see this column FALSE, the view has been altered.';
COMMENT ON COLUMN provenance.v_joint_e2e.e2e_vs_sum_evidence IS
  'Per-row evidence for the request-linked claim. ''strictly_differs_from_sum'': e2e_p99_ms differs from enc+ttft, which a stored sum could not do -- this row independently demonstrates the join (all 7 reactive rows, each strictly BELOW the sum). ''coincides_with_sum'': the two agree because both stages are pinned at their service floor, so the row is consistent with the join but does not by itself prove it (the 13 forecast rows). NOT a data-quality flag -- see the view comment for the full argument.';
COMMENT ON COLUMN provenance.v_joint_e2e.e2e_p99_semantics IS
  'Prose statement of what e2e_p99_ms is and is not, carried per row so it survives a CSV dump that loses these COMMENTs.';
COMMENT ON COLUMN provenance.v_joint_e2e.naive_sum_of_p99s_ms IS
  'encoder_delay_p99_ms + ttft_p99_ms, MILLISECONDS. THIS IS NOT A VALID E2E ESTIMATE. Computed only so the error of assuming it is can be quantified. Never quote it as a latency.';
COMMENT ON COLUMN provenance.v_joint_e2e.naive_sum_minus_joined_ms IS
  'naive_sum_of_p99s_ms - e2e_p99_ms, MILLISECONDS. Magnitude of the error made by adding percentiles. Sign is not fixed: additive can land either side of the truth.';
COMMENT ON COLUMN provenance.v_joint_e2e.naive_sum_over_joined_ratio IS
  'naive_sum_of_p99s_ms / e2e_p99_ms, dimensionless. 1.0 would mean the additive assumption happened to hold; distance from 1.0 measures how badly it fails.';
COMMENT ON COLUMN provenance.v_joint_e2e.arm IS
  'Experiment arm: reactive, or fc_<model> for a forecast arm. Pairs with policy/forecast_model.';
COMMENT ON COLUMN provenance.v_joint_e2e.window_name IS
  'Canonical window ("week" resolved to "aggregate"). window_name_raw preserves the as-ingested spelling.';


-- ---------------------------------------------------------------------
-- 6. v_cost_ratio  --  the denominator is a column, never an assumption
-- ---------------------------------------------------------------------
-- A cost ratio is meaningless without saying what it is against, yet "X%
-- cheaper" is exactly the kind of number that gets quoted bare. This view
-- makes that impossible: every row carries denominator_kind, denominator_run
-- and denominator_worker_seconds alongside the ratio, and every defensible
-- denominator appears as its OWN ROW rather than one being chosen here.
--
-- Three denominators, all defensible, all different:
--   deployable_static_c8   -- the C=8 fleet you could actually deploy today
--   grid_sla_minimal_static -- one static C, the smallest that meets SLA on
--                              every window (max over per-window C*)
--   per_window_optimum     -- the per-window SLA-minimal C*, an oracle that
--                              requires knowing the window in advance
-- The per-window optimum is the hardest denominator and flatters autoscaling
-- least; the C=8 fleet is the most operationally honest. Report all three.

CREATE OR REPLACE VIEW provenance.v_cost_ratio AS
WITH num AS (
    SELECT
        c.run_id, c.experiment, c.pool, c.window_name, c.policy,
        c.forecast_model, c.lead_s, c.quantile, c.cold_start_s,
        c.window_span_s, c.is_current,
        c.provisioned_worker_seconds AS numerator_worker_seconds
    FROM provenance.v_pool_cost c
    -- Select on SOURCE RELATION, not on pool. The quantity being ratioed is
    -- encoder provisioned worker-seconds, and that is defined by where the
    -- number came from. Filtering `pool = 'encoder'` instead would silently
    -- drop the 273 eligible runs labelled pool = 'both' -- which carry
    -- encoder_run_summary rows just as much as the 169 labelled 'encoder' --
    -- and would compute every cost ratio over 38% of the population.
    WHERE c.source_relation = 'encoder_run_summary'
      AND c.provisioned_worker_seconds IS NOT NULL
      AND c.window_span_s IS NOT NULL
),
den AS (
    -- (a) deployable static fleet: C = 8 held for the whole window
    SELECT w.window_name,
           'deployable_static_c8'::text                       AS denominator_kind,
           'static:C=8'::text                                 AS denominator_run,
           8::double precision * w.span_s                     AS denominator_worker_seconds,
           8                                                  AS denominator_workers,
           w.window_name                                      AS denominator_window,
           'C=8 held for the full window span. The fleet that can be provisioned '
           'without foreknowledge of the trace. Most operationally honest baseline.'::text
                                                              AS denominator_basis
    FROM provenance.windows w
    WHERE w.span_s IS NOT NULL

    UNION ALL

    -- (b) one static C for all windows: the smallest meeting SLA everywhere
    SELECT w.window_name,
           'grid_sla_minimal_static'::text,
           'grid:grid_summary'::text,
           s.static_encoder_workers_effective::double precision * w.span_s,
           s.static_encoder_workers_effective,
           w.window_name,
           'max over per-window C* (v_grid_static_effective), held for the full '
           'window span. Smallest single static fleet that meets SLA on every '
           'window; needs the whole trace known in advance.'::text
    FROM provenance.windows w
    CROSS JOIN provenance.v_grid_static_effective s
    WHERE w.span_s IS NOT NULL

    UNION ALL

    -- (c) per-window oracle: the SLA-minimal C* for this window alone
    SELECT g.window_name,
           'per_window_optimum'::text,
           g.grid_run_id,
           g.c_star_effective::double precision * w.span_s,
           g.c_star_effective,
           g.window_name,
           'per-window SLA-minimal C* (v_grid_c_star_effective) held for the full '
           'window span. An ORACLE: assumes the window is known ahead of time. '
           'The strictest denominator -- flatters autoscaling least.'::text
    FROM provenance.v_grid_c_star_effective g
    JOIN provenance.windows w ON w.window_name = g.window_name
    WHERE w.span_s IS NOT NULL AND g.c_star_effective IS NOT NULL
)
SELECT
    n.run_id, n.experiment, n.pool, n.window_name, n.policy,
    n.forecast_model, n.lead_s, n.quantile, n.cold_start_s, n.is_current,
    n.window_span_s,

    n.numerator_worker_seconds,
    d.denominator_kind,
    d.denominator_run,
    d.denominator_worker_seconds,
    d.denominator_workers,
    d.denominator_window,
    d.denominator_basis,

    CASE WHEN d.denominator_worker_seconds > 0
         THEN n.numerator_worker_seconds / d.denominator_worker_seconds END
                                                              AS cost_ratio,
    CASE WHEN d.denominator_worker_seconds > 0
         THEN 1 - n.numerator_worker_seconds / d.denominator_worker_seconds END
                                                              AS savings_ratio,
    (d.denominator_window IS DISTINCT FROM n.window_name)      AS denominator_window_mismatch
FROM num n
JOIN den d ON d.window_name = n.window_name;

COMMENT ON VIEW provenance.v_cost_ratio IS
$$Cost ratios with the DENOMINATOR AS AN EXPLICIT COLUMN, so a ratio can never be
quoted without stating what it is against.

Every row is one (run, denominator) pair. All three defensible denominators appear
as SEPARATE ROWS -- this view deliberately does not pick one, because the choice is
an argument the author has to make and defend, not a default a view should bury:

  deployable_static_c8    C=8 held for the window span. The fleet you could
                          actually provision with no foreknowledge. Most
                          operationally honest.
  grid_sla_minimal_static max over per-window C*, held for the window span. The
                          smallest single static fleet meeting SLA everywhere;
                          assumes the whole trace is known in advance.
  per_window_optimum      per-window SLA-minimal C* (oracle). Strictest
                          denominator; flatters autoscaling least. If a saving
                          survives THIS one, it is real.

cost_ratio < 1 means the run is cheaper than the baseline; savings_ratio is
1 - cost_ratio, so 0.38 reads as "38% cheaper than <denominator_kind>".

TWO THINGS TO KNOW BEFORE QUOTING FROM THIS VIEW.

(1) deployable_static_c8 and grid_sla_minimal_static currently COINCIDE. The
    effective SLA-minimal static fleet is C=8 (v_grid_static_effective, binding
    window burst2; note the as-ingested value was 16 and was corrected down).
    So those two denominators are the same number today and agreeing across them
    is NOT independent corroboration. They are kept separate because they are
    different arguments that could diverge on re-ingest. per_window_optimum is
    the only genuinely distinct baseline at present.

(2) cost_ratio > 1 IS COMMON AND IS NOT A BUG. On the burst windows the
    autoscaling arms cost substantially MORE than a static fleet -- e.g. burst1
    forecast runs at ~409k-419k worker-seconds against a C=8 baseline of ~240k,
    a ratio of ~1.71, rising to ~2.28 against the per-window optimum. Short
    bursty windows do not give an autoscaler enough runway to amortise
    spin-up. Any summary that filters to cost_ratio < 1 is selecting on the
    dependent variable.

WHY THIS VIEW EXISTS -- a live trap in the base data: ewma_ablation_cell.
denom_static_c8_ws is the CONSTANT 3,869,278.4 on all 208 rows, which is the C=8
cost of the *aggregate* window (8 x 483,659.8 s). On the 160 non-aggregate rows
that denominator belongs to a different window -- for burst3 (span 1,619.7 s, true
C=8 cost 12,957.6) it is ~299x too large. The loader was right to leave
ratio_vs_static NULL on those rows, but the denominator column is still populated
and anyone computing ws / denom_static_c8_ws gets a meaningless number. Here every
denominator states its own window and denominator_window_mismatch flags any
crossing. Verify the trap:

    SELECT window_name, count(*), min(denom_static_c8_ws), max(denom_static_c8_ws)
      FROM provenance.ewma_ablation_cell GROUP BY 1 ORDER BY 1;

Worked example -- the headline saving, stated against all three baselines at once
so the claim cannot be denominator-shopped:

    SELECT denominator_kind, denominator_workers, denominator_worker_seconds,
           round(numerator_worker_seconds::numeric, 0) AS run_ws,
           round(cost_ratio::numeric, 4)   AS ratio,
           round((100 * savings_ratio)::numeric, 1) AS pct_cheaper
      FROM provenance.v_cost_ratio
     WHERE window_name = 'aggregate' AND policy = 'forecast' AND is_current
     ORDER BY denominator_kind, cost_ratio
     LIMIT 30;

Worked example -- best forecast run per window against the STRICTEST denominator,
which is the only comparison that supports an unqualified "cheaper" claim:

    SELECT DISTINCT ON (window_name)
           window_name, run_id, forecast_model, lead_s,
           denominator_kind, denominator_workers,
           round(cost_ratio::numeric, 4) AS ratio
      FROM provenance.v_cost_ratio
     WHERE denominator_kind = 'per_window_optimum'
       AND policy = 'forecast' AND is_current
     ORDER BY window_name, cost_ratio;

Worked example -- where autoscaling LOSES (ratio > 1); these exist and should be
reported, not filtered out:

    SELECT window_name, denominator_kind, count(*) AS n_runs_more_expensive
      FROM provenance.v_cost_ratio
     WHERE cost_ratio > 1 AND is_current
     GROUP BY 1,2 ORDER BY 1,2;$$;

COMMENT ON COLUMN provenance.v_cost_ratio.numerator_worker_seconds IS
  'The run''s own provisioned cost, WORKER-SECONDS, from v_pool_cost. Excludes cold-start warm-up -- if the denominator is a static fleet that never pays warm-up, this comparison slightly favours the autoscaler; see v_pool_cost.warmup_worker_seconds.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_kind IS
  'WHICH BASELINE this ratio is against: deployable_static_c8 | grid_sla_minimal_static | per_window_optimum. Never quote cost_ratio without also quoting this.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_run IS
  'Identity of the baseline: a grid_run_id for grid-derived denominators, or the synthetic token ''static:C=8'' for the constructed C=8 fleet.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_worker_seconds IS
  'The baseline cost, WORKER-SECONDS: denominator_workers x window span. Stated explicitly so the arithmetic behind cost_ratio is checkable without re-deriving it.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_workers IS
  'Constant worker count of the baseline fleet. 8 for deployable_static_c8; max over C* for grid_sla_minimal_static; this window''s C* for per_window_optimum.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_window IS
  'The window the denominator was computed for. Must equal window_name -- denominator_window_mismatch flags any row where it does not. This column exists because ewma_ablation_cell.denom_static_c8_ws carries the aggregate window''s denominator on every row, including burst windows ~300x smaller.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_basis IS
  'Prose statement of what the baseline assumes (foreknowledge of the trace, oracle window selection, none). Carried per row so it survives export.';
COMMENT ON COLUMN provenance.v_cost_ratio.cost_ratio IS
  'numerator_worker_seconds / denominator_worker_seconds, dimensionless. < 1 = cheaper than baseline, > 1 = more expensive. MEANINGLESS without denominator_kind.';
COMMENT ON COLUMN provenance.v_cost_ratio.savings_ratio IS
  '1 - cost_ratio, dimensionless. 0.38 reads "38% cheaper than denominator_kind". Negative means the run cost MORE.';
COMMENT ON COLUMN provenance.v_cost_ratio.denominator_window_mismatch IS
  'TRUE if a denominator from a different window leaked into the row. Should always be FALSE; a TRUE here is a bug in this view, and is the failure mode ewma_ablation_cell actually exhibits.';

-- =====================================================================
-- end 20_semantic.sql
-- =====================================================================
