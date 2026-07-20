# RESULTS_EVIDENCE — the complete results picture, per pool and jointly

**Source:** `provenance` schema, PostgreSQL 16 (`postgres@localhost:5433`, db `postgres`).
**Compiled:** 2026-07-20. Every table below is the pasted output of the SQL printed above it.
Nothing here is estimated, interpolated or carried over from a document.

Connect:

```bash
export PGPASSWORD=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' postgres \
  | sed -n 's/^POSTGRES_PASSWORD=//p')
psql -h localhost -p 5433 -U goku -d postgres -c "SET search_path=provenance,public; ..."
```

---

## 0. READ THIS FIRST — four facts that condition everything below

### 0.1 The store MOVED during compilation. It is now quiescent.

`runs` was **2060** when this pass began and **3044** when it ended. The families the brief
told me to exclude — `a16`, `a16_ft`, `g2`, `g3_32b`, `g4`, `g6` — were **ingested live, mid-session**.

```sql
SELECT experiment, count(*) FROM provenance.runs GROUP BY 1 ORDER BY 2 DESC LIMIT 8;
```

```
 experiment | count
------------+-------
 factorial  |  1284
 g6         |   456
 g3_32b     |   232
 g4         |   165
 grid       |   142
 a2x        |   100
 misc       |    94
 a11        |    52
```

I confirmed the ingest has stopped before finalising (three probes, 20 s apart, all identical):

```sql
SELECT now(), (SELECT count(*) FROM provenance.runs),
       (SELECT count(*) FROM provenance.ingest_log),
       (SELECT max(loaded_at) FROM provenance.ingest_log);
```

```
2026-07-20 04:19:42+00 | 3044 | 3594 | 2026-07-20 04:18:52+00
2026-07-20 04:20:02+00 | 3044 | 3594 | 2026-07-20 04:18:52+00
2026-07-20 04:20:22+00 | 3044 | 3594 | 2026-07-20 04:18:52+00
```

**Every headline number in this pack was re-run against the settled 3044-run store and is
unchanged.** The verification is in §6.1. But be aware: this document is a snapshot of a store
that was being written to hours ago, and the excluded families are now *in* it. Any query in this
pack that scans a family-agnostic surface must carry the exclusion predicate shown.

### 0.2 The new ingest broke two `error`-severity checks that were green

```sql
SELECT check_id, severity, left(detail,100) FROM provenance.check_failures('cheap');
```

```
 check_id | severity | detail
----------+----------+---------------------------------------------------------------------
 C107     | warn     | 1 of 7 soft reconciliation checks failing: client_gen_tokens_eq_gen
 C207     | warn     | 301 of 3594 ingest_log rows reference a run_id absent from runs
 C209     | warn     | 3 runs whose window_name is not in the windows dimension: week
 C210     | error    | ALIAS SPLIT: runs: week=3 vs canonical aggregate=135
 C302     | warn     | 2 runs whose run_id prefix <> experiment
 C306     | warn     | 94 runs filed under experiment = misc
 C601     | warn     | default-partition rows -- composed=21395430 llm=3348130 encoder_series=121060
 C603     | error    | 4 families have raw rows but no dedicated composed_request partition: a16, a16_ft, g2, g4
```

`C210` and `C603` were **passing** before this ingest. Both are confined to excluded families:

```sql
SELECT run_id, experiment FROM provenance.runs WHERE window_name='week';
SELECT run_id, window_name_raw, window_name FROM provenance.v_dim WHERE window_name_raw='week';
```

```
              run_id              | experiment       |  window_name_raw | window_name
----------------------------------+------------      +------------------+-------------
 g2:week_alt                      | g2               |  week            | aggregate
 g2:loop_week_fc_chronos_alt_L60  | g2               |  week            | aggregate
 g2:loop_week_fc_chronos_base_L60 | g2               |  week            | aggregate
```

The `week` alias regression is **exactly the failure mode `SCHEMA_GUIDE` §3 warns about**, and it
has returned. `v_dim` folds all three correctly, which is why every query in this pack goes through
`v_dim` and never filters a base table on `window_name`. **Do not query `runs.window_name`
directly until `22_corrections.sql` is re-run over the g2 family.**

### 0.3 The canonical arm set is anchored on artifact identity, not on dimension guessing

There are 332 runs on `burst1` alone; "the burst1 forecast result" is not a well-defined row. To
get one defensible arm per (window, policy) I anchored on the **composed_e2e source artifact** and
joined back to the run spine by exact `source_path`. This is 1:1 with zero ambiguity:

```sql
-- zero rows returned => every arm matches exactly one run
SELECT c.window_name, c.arm, count(d.run_id) AS n_match
  FROM provenance.composed_e2e c
  LEFT JOIN provenance.v_dim d ON d.source_path = '/home/gio/tese/'||c.composed_trace
 GROUP BY 1,2 HAVING count(d.run_id) <> 1;
```

```
(0 rows)
```

The resolved anchor — used as the CTE `arm` throughout this document:

```sql
WITH arm AS (
  SELECT c.window_name, c.arm, d.run_id
    FROM provenance.composed_e2e c
    JOIN provenance.v_dim d ON d.source_path = '/home/gio/tese/'||c.composed_trace
)
```

| window | arm | run_id |
|---|---|---|
| aggregate | fc_chronos | `misc:fc_p90_L30_issuetime` |
| aggregate | fc_timesfm | `a12:week_encoder_timesfm` |
| aggregate | fc_toto | `a6:toto_p90_L30` |
| aggregate | reactive | `a6:react_L30` |
| burst1/3/4/5 | fc_chronos | `a2:burstN_forecast_L30` |
| burst1/3/4/5 | fc_timesfm | `a2tf:burstN_forecast_timesfm_L30` |
| burst1/3/4/5 | fc_toto | `a2t:burstN_forecast_toto_L30` |
| burst1/3/4/5 | reactive | `a2:burstN_reactive_L30` |

The language-pool counterpart is the `a12` family; it reproduces `composed_e2e.ttft_p99_ms`,
`itl_p99_ms` and `gpu_hours` **exactly** (§B), which is what licenses treating them as the same arm.

### 0.4 Coverage of the window × policy grid is INCOMPLETE, and the gaps are structural

| Window | encoder | language | joint E2E | cost ratio |
|---|---|---|---|---|
| burst1, burst3, burst4, burst5 | yes | yes | **yes** | yes |
| aggregate | yes | yes | **yes** | **only 1 of 4 arms** (§0.5) |
| steady24h | yes | partial | **NO** | yes |
| burst2, burst6 | yes | yes (`g1`) | **NO** | yes |
| fulltrace | yes (`a13`) | yes (`a13`) | **NO** | **NO** (§0.5) |

`composed_e2e` holds **20 rows only** — 5 windows × 4 arms. There is **no request-linked composed
E2E for steady24h, burst2, burst6 or fulltrace**, and none for any static arm. Those cells are
genuinely uncomputable from this store, not merely absent from my queries.

```sql
SELECT count(*) FROM provenance.composed_e2e;   -- 20
```

### 0.5 The thesis headline arm cannot be cost-ratioed by the store's own cost view

Three of the four aggregate arms — including `misc:fc_p90_L30_issuetime`, **the run behind the
0.62× headline** — carry `window_name = NULL` on the spine, therefore no `window_span_s`,
therefore `v_cost_ratio` drops them (it requires `window_span_s IS NOT NULL`):

```sql
SELECT run_id, window_name_raw, window_name, window_span_s, policy, forecast_model, quantile
  FROM provenance.v_dim
 WHERE run_id IN ('misc:fc_p90_L30_issuetime','a12:week_encoder_timesfm',
                  'a6:toto_p90_L30','a6:react_L30');
```

```
          run_id           | window_name_raw | window_name | window_span_s |  policy  | model   | quantile
---------------------------+-----------------+-------------+---------------+----------+---------+---------
 a6:react_L30              |                 |             |               | reactive |         |
 a6:toto_p90_L30           |                 |             |               |          | toto    | p90
 misc:fc_p90_L30_issuetime |                 |             |               | forecast |         | p90
 a12:week_encoder_timesfm  | aggregate       | aggregate   |      483659.8 |          | timesfm |
```

```sql
WITH arm AS (SELECT c.window_name w, c.arm, d.run_id FROM provenance.composed_e2e c
  JOIN provenance.v_dim d ON d.source_path='/home/gio/tese/'||c.composed_trace)
SELECT a.w, a.arm, a.run_id, count(r.denominator_kind) AS n_denominators
  FROM arm a LEFT JOIN provenance.v_cost_ratio r ON r.run_id=a.run_id
 GROUP BY 1,2,3 ORDER BY 1,2;
```

```
     w     |    arm     |              run_id              | n_denominators
-----------+------------+----------------------------------+-------
 aggregate | fc_chronos | misc:fc_p90_L30_issuetime        |     0   <-- the 0.62x run
 aggregate | fc_timesfm | a12:week_encoder_timesfm         |     2
 aggregate | fc_toto    | a6:toto_p90_L30                  |     0
 aggregate | reactive   | a6:react_L30                     |     0
 burst1..5 | (all)      | a2/a2t/a2tf:*                    |     3
```

The same defect voids `a13` (fulltrace) entirely — `SELECT ... FROM v_cost_ratio WHERE run_id LIKE
'a13:%'` returns **0 rows**. **The aggregate and fulltrace cost ratios in this pack are therefore
computed by hand from `provisioned_worker_seconds` with the denominator written out explicitly**
(§D.2, §D.4). This is a fixable spine defect: populating `runs.window_name` for these four runs
would bring the headline back under the guarded view.

---

## A. ENCODER POOL (vision)

SLA bound, from the store rather than from memory:

```sql
SELECT * FROM provenance.v_sla_bound;
```

```
  sla_metric   | bound_ms | bound_stat |            bound_source
---------------+----------+------------+------------------------------------
 encoder_delay |     1000 | p99        | grid_run_summary.sla_vision_p99_ms
 ttft          |     1000 | p99        | grid_run_summary.sla_llm_ttft_p99_ms
 itl           |      100 | p99        | grid_run_summary.sla_llm_itl_p99_ms
```

### A.1 Delay quantiles, SLA verdict and infraction intensity — canonical arms

```sql
WITH arm AS (
  SELECT c.window_name, c.arm, d.run_id FROM provenance.composed_e2e c
    JOIN provenance.v_dim d ON d.source_path = '/home/gio/tese/'||c.composed_trace)
SELECT a.window_name, a.arm,
       round(l.p50_ms::numeric,1) p50, round(l.p90_ms::numeric,1) p90,
       round(l.p99_ms::numeric,1) p99, round(l.max_ms::numeric,1) mx,
       i.bound_ms, i.is_violation AS viol,
       round(i.overage_abs_ms::numeric,1) ov_ms,
       round(i.overage_ratio::numeric,4) ov_ratio,
       round(i.worst_excursion_ratio::numeric,3) worst_x,
       l.queue_divergent AS qdiv, l.n_requests
  FROM arm a
  JOIN provenance.v_pool_latency l ON l.run_id=a.run_id AND l.sla_metric='encoder_delay'
  LEFT JOIN provenance.v_infraction i ON i.run_id=a.run_id AND i.sla_metric='encoder_delay'
 ORDER BY a.window_name, a.arm;
```

```
 window_name |    arm     | p50 |  p90  |   p99   |   mx    | bound | viol |  ov_ms  | ov_ratio | worst_x | qdiv | n_requests
-------------+------------+-----+-------+---------+---------+-------+------+---------+----------+---------+------+-----------
 aggregate   | fc_chronos | 0.0 |  52.3 |   588.4 | 35807.1 |  1000 | f    |     0.0 |   0.0000 |  34.807 | f    |     749601
 aggregate   | fc_timesfm | 0.0 |  52.3 |   588.4 | 35807.1 |  1000 | f    |     0.0 |   0.0000 |  34.807 | f    |     749601
 aggregate   | fc_toto    | 0.0 |  52.3 |   588.4 | 35807.1 |  1000 | f    |     0.0 |   0.0000 |  34.807 | f    |     749601
 aggregate   | reactive   | 0.0 |  52.3 |   588.4 | 35807.1 |  1000 | f    |     0.0 |   0.0000 |  34.807 | f    |     749601
 burst1      | fc_chronos | 8.9 | 448.1 |   588.4 |  1262.3 |  1000 | f    |     0.0 |   0.0000 |   0.262 | f    |      64804
 burst1      | fc_timesfm | 8.9 | 448.1 |   588.4 |  1262.3 |  1000 | f    |     0.0 |   0.0000 |   0.262 | f    |      64804
 burst1      | fc_toto    | 8.9 | 448.1 |   588.4 |  1513.4 |  1000 | f    |     0.0 |   0.0000 |   0.513 | f    |      64804
 burst1      | reactive   | 8.9 | 448.1 |   588.4 |  2892.0 |  1000 | f    |     0.0 |   0.0000 |   1.892 | f    |      64804
 burst3      | fc_chronos | 0.0 | 268.3 |   588.4 |   588.4 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       3093
 burst3      | fc_timesfm | 0.0 | 268.3 |   588.4 |   904.7 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       3093
 burst3      | fc_toto    | 0.0 | 268.3 |   588.4 |   870.3 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       3093
 burst3      | reactive   | 0.0 | 565.2 | 16078.7 | 20240.0 |  1000 | t    | 15078.7 |  15.0787 |  19.240 | f    |       3093
 burst4      | fc_chronos | 8.9 | 502.1 |   588.4 |   904.7 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |      25639
 burst4      | fc_timesfm | 8.9 | 502.1 |   588.4 |   883.8 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |      25639
 burst4      | fc_toto    | 8.9 | 502.1 |   588.4 |   903.7 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |      25639
 burst4      | reactive   | 8.9 | 502.1 |   588.4 |  6947.0 |  1000 | f    |     0.0 |   0.0000 |   5.947 | f    |      25639
 burst5      | fc_chronos | 0.0 | 522.1 |   588.4 |   883.8 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       8983
 burst5      | fc_timesfm | 0.0 | 522.1 |   588.4 |   883.8 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       8983
 burst5      | fc_toto    | 0.0 | 522.1 |   588.4 |   883.8 |  1000 | f    |     0.0 |   0.0000 |   0.000 | f    |       8983
 burst5      | reactive   | 0.0 | 522.1 |   588.4 | 11004.4 |  1000 | f    |     0.0 |   0.0000 |  10.004 | f    |       8983
```

#### A.1.1 THE CENTRAL, EASILY-MISSED FACT: encoder p50/p90/p99 are policy-INVARIANT except on burst3

Read the table again at full precision. Within each window, **all four arms share byte-identical
p50, p90 and p99** — only `max` and cost differ:

```sql
WITH arm AS (SELECT c.window_name, c.arm, d.run_id FROM provenance.composed_e2e c
  JOIN provenance.v_dim d ON d.source_path = '/home/gio/tese/'||c.composed_trace)
SELECT a.window_name, a.arm, a.run_id,
       s.encoder_delay_p50_ms p50, s.encoder_delay_p90_ms p90,
       s.encoder_delay_p99_ms p99, s.encoder_delay_max_ms mx,
       s.provisioned_worker_seconds ws, s.busy_worker_seconds busy,
       round(s.encoder_utilization::numeric,4) util
  FROM arm a JOIN provenance.encoder_run_summary s ON s.run_id=a.run_id
 ORDER BY a.window_name, a.arm;
```

```
 window_name |    arm     |              run_id              |  p50  |   p90   |    p99    |    mx     |    ws     |  busy   |  util
-------------+------------+----------------------------------+-------+---------+-----------+-----------+-----------+---------+-------
 aggregate   | fc_chronos | misc:fc_p90_L30_issuetime        |     0 |  52.255 |    588.37 | 35807.108 | 2410754.7 | 57476.7 | 0.0238
 aggregate   | fc_timesfm | a12:week_encoder_timesfm         |     0 |  52.255 |    588.37 | 35807.108 | 2335019.6 | 57476.3 | 0.0246
 aggregate   | fc_toto    | a6:toto_p90_L30                  |     0 |  52.255 |    588.37 | 35807.108 | 2389709.5 | 57477.1 | 0.0241
 aggregate   | reactive   | a6:react_L30                     |     0 |  52.255 |    588.37 | 35807.108 | 2611319.7 | 57475.7 | 0.0220
 burst1      | fc_chronos | a2:burst1_forecast_L30           | 8.876 | 448.102 |    588.37 |  1262.345 |  540202.9 | 17327.6 | 0.0321
 burst1      | fc_timesfm | a2tf:burst1_forecast_timesfm_L30 | 8.876 | 448.102 |    588.37 |  1262.345 |  552771.6 | 17327.6 | 0.0313
 burst1      | fc_toto    | a2t:burst1_forecast_toto_L30     | 8.876 | 448.102 |    588.37 |  1513.399 |  537382.9 | 17327.6 | 0.0322
 burst1      | reactive   | a2:burst1_reactive_L30           | 8.876 | 448.102 |    588.37 |  2892.042 |  557458.5 | 17327.5 | 0.0311
 burst3      | fc_chronos | a2:burst3_forecast_L30           |     0 | 268.342 |    588.37 |    588.37 |     32228 |   711.9 | 0.0221
 burst3      | fc_timesfm | a2tf:burst3_forecast_timesfm_L30 |     0 | 268.342 |    588.37 |   904.739 |   23363.6 |   711.9 | 0.0305
 burst3      | fc_toto    | a2t:burst3_forecast_toto_L30     |     0 | 268.342 |    588.37 |   870.286 |   28643.6 |   711.9 | 0.0249
 burst3      | reactive   | a2:burst3_reactive_L30           |     0 | 565.249 | 16078.706 | 20239.987 |   28355.8 |   711.6 | 0.0251
 burst4      | fc_chronos | a2:burst4_forecast_L30           | 8.876 | 502.051 |    588.37 |   904.739 |  238172.9 |  7614.9 | 0.0320
 burst4      | fc_timesfm | a2tf:burst4_forecast_timesfm_L30 | 8.876 | 502.051 |    588.37 |   883.807 |  263476.8 |  7614.9 | 0.0289
 burst4      | fc_toto    | a2t:burst4_forecast_toto_L30     | 8.876 | 502.051 |    588.37 |   903.739 |  243738.5 |  7614.9 | 0.0312
 burst4      | reactive   | a2:burst4_reactive_L30           | 8.876 | 502.051 |    588.37 |  6947.046 |  242403.6 |  7614.9 | 0.0314
 burst5      | fc_chronos | a2:burst5_forecast_L30           |     0 |  522.09 |    588.37 |   883.807 |   88805.6 |  2756.5 | 0.0310
 burst5      | fc_timesfm | a2tf:burst5_forecast_timesfm_L30 |     0 |  522.09 |    588.37 |   883.807 |   96747.8 |  2756.5 | 0.0285
 burst5      | fc_toto    | a2t:burst5_forecast_toto_L30     |     0 |  522.09 |    588.37 |   883.807 |   88968.6 |  2756.5 | 0.0310
 burst5      | reactive   | a2:burst5_reactive_L30           |     0 |  522.09 |    588.37 | 11004.377 |     98643 |  2756.4 | 0.0279
```

**This is not a duplication artifact.** They are distinct run_ids with distinct `source_path`s,
distinct `provisioned_worker_seconds` and distinct `encoder_delay_max_ms`. The physical reading —
and the thesis states it explicitly at `closedloop.tex:445-452` — is that at **2.2–3.2 % encoder
utilisation** the queue is empty for essentially every request, so the delay is a *deterministic
service floor* set by the shared batching pipeline (a full-batch forward `f(64)=316.4 ms` plus the
p99 handoff `272 ms` = **588.4 ms**), identical across policies because all arms share the same
encoder. Policy only moves the distribution once the queue actually builds.

**Consequence for the results narrative, stated plainly: on the encoder SLA metric, forecast does
not beat reactive on 4 of the 5 jointly-covered windows — they tie exactly, at the floor. The
entire encoder-latency advantage of forecasting over reactive control in this arm set lives in
burst3.** Everywhere else the advantage is in `max` (tail excursions the p99 does not see) and in
cost, not in the graded SLA statistic. Any figure that plots per-window encoder p99 by policy will
show four flat identical lines and one spike; that is the true result, and it is a stronger,
more honest story than a bar chart implying uniform improvement.

The `worst_excursion_ratio` column is where the arms *do* separate on latency, and it is worth
promoting in the results chapter because it is the only latency statistic in the encoder pool that
discriminates policy on every window:

| window | fc_chronos | fc_timesfm | fc_toto | reactive |
|---|---|---|---|---|
| burst1 | 0.262 | 0.262 | 0.513 | **1.892** |
| burst3 | 0.000 | 0.000 | 0.000 | **19.240** |
| burst4 | 0.000 | 0.000 | 0.000 | **5.947** |
| burst5 | 0.000 | 0.000 | 0.000 | **10.004** |
| aggregate | 34.807 | 34.807 | 34.807 | 34.807 |

(`worst_excursion_ratio` = `max_ms / bound_ms − 1`. On aggregate all four arms share the same
35807.1 ms max — a single trace-wide worst request that no policy in this set avoids.)

### A.1.2 Infraction intensity, and the hard limit on it

Only **one** canonical encoder arm violates: `burst3/reactive`, and it violates
**catastrophically** — p99 16,078.7 ms against a 1,000 ms bound, an **overage ratio of 15.08**
(1,508 % over), worst excursion 19.24×.

**Duration-in-violation is genuinely uncomputable for the encoder pool.** `v_infraction` returns
NULL for `violation_seconds`, `fraction_time_in_violation` and `fraction_requests_over_bound` on
every `sla_metric='encoder_delay'` row, because there is no stored per-request encoder delay —
`encoder_series` holds per-second *occupancy*, not latency. This is a structural absence, not an
ingest gap; queue depth is not a substitute. The `has_raw_backing` column says so per row.
**Report absolute and relative overage and worst excursion for the encoder; do not report duration.**

`queue_divergent` is `false` on all 20 arms, so no encoder p99 here is a lower bound on an
unbounded quantity.

### A.2 Cost, utilisation, GPU-hours and the cold-start bill

```sql
WITH arm AS (SELECT c.window_name, c.arm, d.run_id FROM provenance.composed_e2e c
  JOIN provenance.v_dim d ON d.source_path='/home/gio/tese/'||c.composed_trace)
SELECT a.window_name, a.arm, p.window_span_s span_s,
       round(p.provisioned_worker_seconds::numeric,1) ws,
       round((p.provisioned_worker_seconds/3600)::numeric,2) gpu_h_5090_derived,
       round(p.utilization_ratio::numeric,4) util,
       p.has_cold_start_accounting cs,
       round(p.warmup_worker_seconds::numeric,1) warmup_ws,
       round(p.total_from_order_worker_seconds::numeric,1) from_order_ws,
       round(p.warmup_fraction::numeric,4) warm_frac
  FROM arm a JOIN provenance.v_pool_cost p
    ON p.run_id=a.run_id AND p.source_relation='encoder_run_summary'
 ORDER BY a.window_name, a.arm;
```

```
 window_name |    arm     |  span_s  |    ws     | gpu_h_5090_derived |  util  | cs | warmup_ws | from_order_ws | warm_frac
-------------+------------+----------+-----------+--------------------+--------+----+-----------+---------------+----------
 aggregate   | fc_chronos |          | 2410754.7 |             669.65 | 0.0238 | f  |           |               |
 aggregate   | fc_timesfm | 483659.8 | 2335019.6 |             648.62 | 0.0246 | f  |           |               |
 aggregate   | fc_toto    |          | 2389709.5 |             663.81 | 0.0241 | f  |           |               |
 aggregate   | reactive   |          | 2611319.7 |             725.37 | 0.0220 | f  |           |               |
 burst1      | fc_chronos |  29939.3 |  540202.9 |             150.06 | 0.0321 | t  |    3810.0 |      544012.9 |    0.0071
 burst1      | fc_timesfm |  29939.3 |  552771.6 |             153.55 | 0.0313 | t  |    3810.0 |      544012.9 |    0.0071
 burst1      | fc_toto    |  29939.3 |  537382.9 |             149.27 | 0.0322 | t  |    3810.0 |      544012.9 |    0.0071
 burst1      | reactive   |  29939.3 |  557458.5 |             154.85 | 0.0311 | t  |   19470.0 |      576928.5 |    0.0349
 burst3      | fc_chronos |   1619.7 |   32228.0 |               8.95 | 0.0221 | t  |     540.0 |       32768.0 |    0.0168
 burst3      | fc_timesfm |   1619.7 |   23363.6 |               6.49 | 0.0305 | t  |     540.0 |       32768.0 |    0.0168
 burst3      | fc_toto    |   1619.7 |   28643.6 |               7.96 | 0.0249 | t  |     540.0 |       32768.0 |    0.0168
 burst3      | reactive   |   1619.7 |   28355.8 |               7.88 | 0.0251 | t  |    2520.0 |       30875.8 |    0.0889
 burst4      | fc_chronos |  11339.2 |  238172.9 |              66.16 | 0.0320 | t  |    3135.0 |      241307.9 |    0.0132
 burst4      | fc_timesfm |  11339.2 |  263476.8 |              73.19 | 0.0289 | t  |    3135.0 |      241307.9 |    0.0132
 burst4      | fc_toto    |  11339.2 |  243738.5 |              67.71 | 0.0312 | t  |    3135.0 |      241307.9 |    0.0132
 burst4      | reactive   |  11339.2 |  242403.6 |              67.33 | 0.0314 | t  |    8190.0 |      250593.6 |    0.0338
 burst5      | fc_chronos |   4857.9 |   88805.6 |              24.67 | 0.0310 | t  |    1170.0 |       89975.6 |    0.0132
 burst5      | fc_timesfm |   4857.9 |   96747.8 |              26.87 | 0.0285 | t  |    1170.0 |       89975.6 |    0.0132
 burst5      | fc_toto    |   4857.9 |   88968.6 |              24.71 | 0.0310 | t  |    1170.0 |       89975.6 |    0.0132
 burst5      | reactive   |   4857.9 |   98643.0 |              27.40 | 0.0279 | t  |    4140.0 |      102783.0 |    0.0420
```

**Three caveats on this table, all load-bearing.**

**(a) `gpu_h_5090_derived` is DERIVED, not stored.** `encoder_run_summary` has no GPU-hours column
(the asymmetry is deliberate — see `v_pool_cost` comment). I computed
`provisioned_worker_seconds / 3600` under a **1 worker = 1 RTX-5090** assumption. That assumption
is corroborated by the grid, where `gpu_hours_rtx5090_effective` reproduces `c_star × span_h`
exactly (burst1: 6 × 8.316 = 49.9 ✓). State the assumption whenever quoting these.

**(b) `cost_accounting` has NO forecast-model dimension, so the warm-up columns are WRONG for two
of the three forecast arms.** Its PK is `(source_path, window_name, policy, lead_s)`:

```sql
SELECT DISTINCT source_path FROM provenance.cost_accounting;
-- /home/gio/tese/defense/anim/data/a2_cost_accounting.csv   (1 row)
```

`v_pool_cost` joins it on `(window_name, policy, lead_s)`, so all three forecast arms on a window
inherit the **same** warm-up row. The decomposition check `total = provisioned + warmup` holds only
for the arm the row was actually measured on (chronos): burst1 `540202.9 + 3810.0 = 544012.9` ✓,
whereas timesfm's own `552771.6 + 3810.0 = 556581.6 ≠ 544012.9`. **`warmup_ws`, `from_order_ws` and
`warm_frac` are trustworthy only on the `fc_chronos` and `reactive` rows.** Quote them nowhere else.

**(c) `has_cold_start_accounting = false` on all four aggregate arms** — the week-scale warm-up
component is **unmeasured, not zero**. `cost_accounting` covers 40 (window, policy, lead) cells and
aggregate is not among them.

### A.3 The full cold-start ledger — both billing bases

This is the complete `cost_accounting` table, and it is the strongest cost-honesty evidence in the
store: it separates **bill-from-readiness** (`provisioned_ws`, what the headline quotes) from
**bill-from-order** (`total_from_order_ws`, what an operator actually pays).

```sql
SELECT window_name, policy, lead_s, round(p99_ms::numeric,1) p99,
       round(provisioned_ws::numeric,1) prov, round(warmup_ws::numeric,1) warm,
       round(total_from_order_ws::numeric,1) tot, round(warmup_frac::numeric,4) frac
  FROM provenance.cost_accounting ORDER BY window_name, policy, lead_s;
```

```
 window_name |  policy  | lead_s |   p99   |   prov   |   warm   |   tot    |  frac
-------------+----------+--------+---------+----------+----------+----------+--------
 burst1      | forecast |     15 |   588.4 | 540412.9 |   1905.0 | 542317.9 | 0.0035
 burst1      | forecast |     30 |   588.4 | 540202.9 |   3810.0 | 544012.9 | 0.0071
 burst1      | forecast |     45 |   588.4 | 539992.9 |   5715.0 | 545707.9 | 0.0106
 burst1      | forecast |    165 |   588.4 | 537778.5 |  21489.0 | 559267.5 | 0.0400
 burst1      | reactive |     15 |   588.4 | 567193.5 |   9735.0 | 576928.5 | 0.0172
 burst1      | reactive |     30 |   588.4 | 557458.5 |  19470.0 | 576928.5 | 0.0349
 burst1      | reactive |     45 |   588.4 | 547723.5 |  29205.0 | 576928.5 | 0.0533
 burst1      | reactive |    165 |   609.7 | 469903.9 | 106755.0 | 576658.9 | 0.2272
 burst3      | forecast |     15 |   588.4 |  32303.0 |    270.0 |  32573.0 | 0.0084
 burst3      | forecast |     30 |   588.4 |  32228.0 |    540.0 |  32768.0 | 0.0168
 burst3      | forecast |     45 |   588.4 |  32153.0 |    810.0 |  32963.0 | 0.0252
 burst3      | forecast |    165 |   588.4 |  31553.0 |   2970.0 |  34523.0 | 0.0941
 burst3      | reactive |     15 |  9481.3 |  29615.8 |   1260.0 |  30875.8 | 0.0425
 burst3      | reactive |     30 | 16078.7 |  28355.8 |   2520.0 |  30875.8 | 0.0889
 burst3      | reactive |     45 | 28342.2 |  27095.8 |   3780.0 |  30875.8 | 0.1395
 burst3      | reactive |    165 | 54169.5 |  17018.1 |  12540.0 |  29558.1 | 0.7369
 burst4      | forecast |     15 |   588.4 | 238367.9 |   1575.0 | 239942.9 | 0.0066
 burst4      | forecast |     30 |   588.4 | 238172.9 |   3135.0 | 241307.9 | 0.0132
 burst4      | forecast |     45 |   588.4 | 237977.9 |   4695.0 | 242672.9 | 0.0197
 burst4      | forecast |    165 |   588.4 | 234559.3 |  18944.0 | 253503.3 | 0.0808
 burst4      | reactive |     15 |   588.4 | 246498.6 |   4095.0 | 250593.6 | 0.0166
 burst4      | reactive |     30 |   588.4 | 242403.6 |   8190.0 | 250593.6 | 0.0338
 burst4      | reactive |     45 |   588.4 | 238308.6 |  12285.0 | 250593.6 | 0.0516
 burst4      | reactive |    165 |   904.7 | 205548.6 |  45045.0 | 250593.6 | 0.2191
 burst5      | forecast |     15 |   588.4 |  88955.6 |    585.0 |  89540.6 | 0.0066
 burst5      | forecast |     30 |   588.4 |  88805.6 |   1170.0 |  89975.6 | 0.0132
 burst5      | forecast |     45 |   588.4 |  88655.6 |   1755.0 |  90410.6 | 0.0198
 burst5      | forecast |    165 |   588.4 |  86852.1 |   6708.0 |  93560.1 | 0.0772
 burst5      | reactive |     15 |   588.4 | 100713.0 |   2070.0 | 102783.0 | 0.0206
 burst5      | reactive |     30 |   588.4 |  98643.0 |   4140.0 | 102783.0 | 0.0420
 burst5      | reactive |     45 |   588.4 |  96573.0 |   6210.0 | 102783.0 | 0.0643
 burst5      | reactive |    165 |  3250.2 |  80910.6 |  20460.0 | 101370.6 | 0.2529
 steady24h   | forecast |     15 |   677.4 | 162355.8 |   1230.0 | 163585.8 | 0.0076
 steady24h   | forecast |     30 |   677.4 | 162325.8 |   2460.0 | 164785.8 | 0.0152
 steady24h   | forecast |     45 |   677.4 | 162295.8 |   3690.0 | 165985.8 | 0.0227
 steady24h   | forecast |    165 |   685.3 | 162055.8 |  13530.0 | 175585.8 | 0.0835
 steady24h   | reactive |     15 |   548.4 | 186956.7 |   4470.0 | 191426.7 | 0.0239
 steady24h   | reactive |     30 |   682.1 | 182486.7 |   8940.0 | 191426.7 | 0.0490
 steady24h   | reactive |     45 |   733.6 | 178016.7 |  13410.0 | 191426.7 | 0.0753
 steady24h   | reactive |    165 |   733.6 | 142256.7 |  49170.0 | 191426.7 | 0.3456
```

**This table contains a result the thesis under-uses.** Reading `prov` alone, reactive looks
*cheaper* than forecast at long lead: burst3 reactive L=165 is 17,018 ws against forecast's 31,553.
Reading `tot` — the honest bill — the gap collapses to 29,558 vs 34,523, and reactive is buying that
14 % discount with a p99 of **54,169.5 ms** against forecast's 588.4. The warm-up fraction is the
mechanism: reactive at L=165 spends **73.7 % of its bill on workers that were not yet serving**
(burst3), 25.3 % (burst5), 22.7 % (burst1), 21.9 % (burst4), 34.6 % (steady24h).

**Forecast's warm-up fraction never exceeds 9.4 %; reactive's reaches 73.7 %.** That contrast is a
first-class finding and it is *independent* of the p99 argument: anticipation converts cold-start
from a dominant cost term into a rounding error. Under bill-from-order at L=165, forecast is
cheaper than reactive on burst1 (559,268 vs 576,659), burst4 (253,503 vs 250,594 — reactive
marginally ahead), burst5 (93,560 vs 101,371) and steady24h (175,586 vs 191,427).

### A.4 Remaining windows — steady24h, burst2, burst6 (excluded families filtered out)

```sql
SELECT d.run_id, d.window_name, d.policy, d.forecast_model, d.lead_s,
       s.encoder_workers cw, s.encoder_delay_p99_ms p99, s.encoder_delay_max_ms mx,
       s.provisioned_worker_seconds ws, round(s.encoder_utilization::numeric,4) util
  FROM provenance.v_dim d JOIN provenance.encoder_run_summary s ON s.run_id=d.run_id
 WHERE d.window_name IN ('steady24h','burst2','burst6')
   AND d.experiment NOT IN ('a16','a16_ft','g2','g3_32b','g4','g6')
 ORDER BY d.window_name, s.provisioned_worker_seconds;
```

Selected rows (68 returned; full output reproducible from the query):

```
                run_id                 | window_name |  policy  | model   | lead_s | cw |    p99    |    mx     |    ws    |  util
---------------------------------------+-------------+----------+---------+--------+----+-----------+-----------+----------+-------
 g1:burst2_enc_static_C2               | burst2      | static   |         |        |  2 |  6321.347 | 17557.676 |  13674.8 | 0.3085
 g1:burst2_enc_static_C8               | burst2      | static   |         |        |  8 |   855.829 |  2215.696 |  54694.8 | 0.0772
 reactive:burst2_react_L300            | burst2      | reactive |         |    300 |  2 |  4281.664 | 14760.918 |  94104.2 | 0.0449
 a2x:burst2_reactive_L165              | burst2      | reactive |         |    165 |  2 |  1065.045 |    5661.3 | 106267.9 | 0.0397
 g1:burst2_enc_fc_chronos_L30          | burst2      | forecast | chronos |     30 |  1 |    588.37 |  4113.909 | 124293.4 | 0.0340
 g1:burst2_enc_fc_toto_L30             | burst2      | forecast | toto    |     30 |  1 |   654.739 |  7773.127 | 125253.7 | 0.0337
 g1:burst2_enc_fc_timesfm_L30          | burst2      | forecast | timesfm |     30 |  1 |    588.37 |  4113.909 | 134283.7 | 0.0314
 g1:burst6_enc_static_C2               | burst6      | static   |         |        |  2 |  5333.174 | 12497.554 |   9838.8 | 0.2211
 g1:burst6_enc_static_C8               | burst6      | static   |         |        |  8 |   720.108 |  1412.152 |  39355.1 | 0.0553
 reactive:burst6_react_L300            | burst6      | reactive |         |    300 |  2 |  4606.148 | 15586.854 |  52978.8 | 0.0411
 a2x:burst6_reactive_L165              | burst6      | reactive |         |    165 |  2 |  3281.929 | 15586.854 |  65188.8 | 0.0334
 g1:burst6_enc_fc_toto_L30             | burst6      | forecast | toto    |     30 |  1 |    588.37 |   939.045 |  85032.9 | 0.0256
 g1:burst6_enc_fc_chronos_L30          | burst6      | forecast | chronos |     30 |  1 |    588.37 |  1065.045 |  88374.4 | 0.0246
 g1:burst6_enc_fc_timesfm_L30          | burst6      | forecast | timesfm |     30 |  1 |    588.37 |  1065.045 |  96220.5 | 0.0226
 a2:steady24h_forecast_L165            | steady24h   | forecast |         |    165 |  2 |   685.323 |   2083.97 | 162055.8 | 0.0151
 a2:steady24h_forecast_L30             | steady24h   | forecast |         |     30 |  2 |   677.365 |   2083.97 | 162325.8 | 0.0151
 a2tf:steady24h_forecast_timesfm_L30   | steady24h   | forecast | timesfm |     30 |  2 |   671.975 |  2109.788 | 167815.8 | 0.0146
 a2t:steady24h_forecast_toto_L30       | steady24h   | forecast | toto    |     30 |  2 |   548.363 |   2083.97 | 175765.8 | 0.0139
 a2:steady24h_reactive_L165            | steady24h   | reactive |         |    165 |  2 |   733.643 |  3691.632 | 142256.7 | 0.0172
 a2:steady24h_reactive_L30             | steady24h   | reactive |         |     30 |  2 |   682.109 |  3691.632 | 182486.7 | 0.0134
 grid:grid_steady24h_C2                | steady24h   |          |         |        |  2 |   733.643 |  3024.915 |          | 0.0142
```

**burst2 and burst6 are the two windows where reactive genuinely fails at long lead and forecast
does not** (burst2 reactive L=300 → 4,281.7 ms; burst6 reactive L=300 → 4,606.1 ms; both forecast
arms at 588.4). They are **absent from `composed_e2e`**, so they contribute to the per-pool story
but cannot enter the joint E2E story. This is worth stating rather than quietly dropping them.

On **steady24h, forecast is more expensive than reactive at long lead** (162,056 vs 142,257 ws at
L=165) while being only marginally better on p99 (685.3 vs 733.6). The calm day is where
anticipation earns least — consistent with the grid's `C* = 2` for that window.

### A.5 Fulltrace (A13) — the only 1,000,000-request encoder evidence

```sql
SELECT s.run_id, s.requests, s.encoder_workers cw,
       s.encoder_delay_p50_ms p50, s.encoder_delay_p90_ms p90,
       s.encoder_delay_p99_ms p99, s.encoder_delay_max_ms mx,
       s.provisioned_worker_seconds ws, s.busy_worker_seconds busy,
       round(s.encoder_utilization::numeric,4) util, s.queue_divergent qdiv
  FROM provenance.encoder_run_summary s
 WHERE s.run_id LIKE 'a13:%' OR s.run_id LIKE 'a14:%' ORDER BY 1;
```

```
        run_id        | requests | cw |  p50  |   p90   |   p99    |    mx     |    ws     |  busy   |  util  | qdiv
----------------------+----------+----+-------+---------+----------+-----------+-----------+---------+--------+------
 a13:ft_reactive_L30  |  1000000 |  2 | 8.876 |  52.255 |   588.37 | 35807.108 | 3323189.5 | 72392.7 | 0.0218 | f
 a13:ft_static_C2     |  1000000 |  2 | 8.876 | 119.849 | 2904.556 | 28245.859 | 1209599.4 | 72330.8 | 0.0598 | f
 a13:ft_static_C8     |  1000000 |  8 | 8.876 |  52.255 |  677.461 | 10845.573 | 4838397.6 | 72400.5 | 0.0150 | f
 a14:chronos_composed |   749601 |  2 |     0 |  52.255 |   588.37 | 35807.108 | 2410754.7 | 57476.7 | 0.0238 | f
 a14:timesfm_composed |   931628 |  2 |     0 |  52.255 |   588.37 | 35807.108 | 2803229.6 | 69149.5 | 0.0247 | f
 a14:toto_composed    |   872980 |  2 |     0 |  52.255 |   588.37 | 35807.108 | 2535179.7 | 60571.9 | 0.0239 | f
```

Fulltrace verdicts against the 1,000 ms bound: `ft_static_C2` **FAILS** (2,904.6 ms, overage ratio
1.905); `ft_static_C8` **passes** (677.5); `ft_reactive_L30` **passes** (588.4). A14 confirms all
three foundation models hold the 588.4 floor over their maximum forecastable spans
(749,601 / 931,628 / 872,980 requests).

---

## B. LANGUAGE POOL

### B.1 Canonical arms (a12) — TTFT, ITL, TPOT, cost

```sql
SELECT d.window_name, coalesce('fc_'||d.forecast_model, d.policy) arm,
       l.completed_requests req,
       round(l.median_ttft_ms::numeric,1) t50, round(l.p90_ttft_ms::numeric,1) t90,
       round(l.p99_ttft_ms::numeric,1) t99, round(l.max_ttft_ms::numeric,1) tmax,
       round(l.mean_itl_ms::numeric,2) itl_mean, round(l.p99_itl_ms::numeric,2) itl99,
       round(l.mean_tpot_ms::numeric,2) tpot_mean, round(l.p99_tpot_ms::numeric,2) tpot99,
       round(l.gpu_hours::numeric,2) gpu_h,
       round(l.decode_worker_seconds::numeric,1) dec_ws,
       round(l.prefill_worker_seconds::numeric,1) pre_ws, l.has_raw_records raw
  FROM provenance.v_dim d JOIN provenance.llm_run_summary l ON l.run_id=d.run_id
 WHERE d.run_id IN (SELECT run_id FROM provenance.v_dim
                     WHERE experiment='a12' AND pool='language')
 ORDER BY d.window_name, arm;
```

```
 window_name |    arm     |  req   | t50  |  t90  |   t99   |  tmax   | itl_mean | itl99  | tpot_mean | tpot99 | gpu_h  |  dec_ws   | pre_ws | raw
-------------+------------+--------+------+-------+---------+---------+----------+--------+-----------+--------+--------+-----------+--------+-----
 aggregate   | fc_chronos | 749601 | 22.6 |  96.2 |   651.1 |  4365.9 |     4.62 |   6.32 |      4.71 |   9.43 | 550.21 |  990384.0 |    0.0 | t
 aggregate   | fc_timesfm | 749601 | 22.4 |  93.8 |   651.1 |  4365.9 |     4.57 |   5.92 |      4.65 |   8.86 | 610.65 | 1099167.8 |    0.0 | t
 aggregate   | fc_toto    | 749601 | 22.5 |  96.5 |   651.1 |  4365.9 |     4.61 |   6.30 |      4.70 |   9.33 | 609.18 | 1096520.6 |    0.0 | t
 aggregate   | reactive   | 749601 | 25.1 | 157.9 |  1191.6 | 15902.8 |     5.43 |  21.14 |      6.12 |  36.45 | 281.46 |  506630.9 |    0.0 | t
 burst1      | fc_chronos |  64804 | 22.1 | 471.7 |   651.1 |  2503.2 |     4.36 |   5.22 |      4.39 |   5.36 | 114.32 |  205775.7 |    0.0 | t
 burst1      | fc_timesfm |  64804 | 22.7 | 494.3 |   671.3 |  2591.7 |     4.48 |   5.41 |      4.55 |   8.31 |  93.82 |  168870.2 |    0.0 | t
 burst1      | fc_toto    |  64804 | 23.0 | 494.3 |   671.6 |  2899.6 |     4.53 |   5.47 |      4.62 |   9.64 |  72.54 |  130564.4 |    0.0 | t
 burst1      | reactive   |  64804 | 35.1 | 710.3 |  1664.7 |  4329.2 |     7.00 | 124.08 |      9.25 |  79.30 |  20.51 |   36912.5 |    0.0 | t
 burst3      | fc_chronos |   3093 | 21.7 | 267.3 |   651.1 |  2185.8 |     4.34 |   5.13 |      4.38 |   5.29 |   6.34 |   11419.9 |    0.0 | t
 burst3      | fc_timesfm |   3093 | 21.7 | 267.3 |   651.1 |  2185.8 |     4.39 |   5.18 |      4.48 |   8.08 |   4.87 |    8760.2 |    0.0 | t
 burst3      | fc_toto    |   3093 | 21.7 | 267.3 |   651.1 |  2185.8 |     4.34 |   5.13 |      4.38 |   5.35 |   6.31 |   11359.9 |    0.0 | t
 burst3      | reactive   |   3093 | 30.5 | 996.3 | 10573.7 | 15902.8 |     8.94 | 160.80 |     15.68 | 154.67 |   1.04 |    1872.1 |    0.0 | t
 burst4      | fc_chronos |  25639 | 24.7 | 538.6 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.39 |   5.13 |  49.44 |   88984.9 |    0.0 | t
 burst4      | fc_timesfm |  25639 | 24.7 | 538.6 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.39 |   5.13 |  49.74 |   89526.3 |    0.0 | t
 burst4      | fc_toto    |  25639 | 24.7 | 538.6 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.40 |   5.13 |  48.87 |   87968.6 |    0.0 | t
 burst4      | reactive   |  25639 | 60.4 | 821.8 |  2807.0 |  6395.6 |     8.59 | 151.08 |     12.45 | 143.10 |   8.13 |   14626.2 |    0.0 | t
 burst5      | fc_chronos |   8983 | 25.5 | 558.9 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.39 |   5.13 |  20.98 |   37764.6 |    0.0 | t
 burst5      | fc_timesfm |   8983 | 25.5 | 558.9 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.39 |   5.13 |  21.18 |   38124.6 |    0.0 | t
 burst5      | fc_toto    |   8983 | 25.5 | 558.9 |   651.1 |  2572.5 |     4.35 |   5.14 |      4.39 |   5.13 |  20.93 |   37674.9 |    0.0 | t
 burst5      | reactive   |   8983 | 55.3 | 764.4 |  2181.6 |  3470.6 |     7.75 | 145.89 |     11.26 | 120.59 |   3.39 |    6095.5 |    0.0 | t
```

Notes: `prefill_worker_seconds = 0` on every row (disaggregated prefill is not separately billed in
this simulator; cost is decode-side). `has_raw_records = true` on all 20, so every percentile here
is auditable via `check_run()` / `recompute_p99()` — unlike 395 of 520 `llm_run_summary` rows
store-wide (§6.3).

**ITL p50/p90/max do not exist** in `v_pool_latency` (`llm_run_summary` stored only mean and p99).
The `mean_itl_ms` and `p99_itl_ms` columns above are the complete ITL evidence. Note also the two
distinct "ITL p99" definitions in the same row — `p99_itl_ms` (token-pooled) and `p99_tpot_ms`
(`(RequestLatency − TTFT)/(OSL − 1)`, the aiperf TPOT the thesis's `tab:val-anchor` uses). They
differ materially (aggregate reactive: 21.14 vs 36.45). **Say which one you mean.**

### B.2 Language SLA verdict + infraction intensity, WITH duration (raw-backed)

Unlike the encoder, TTFT has per-request raw backing, so duration-in-violation is real:

```sql
SELECT i.run_id, i.window_name, i.sla_metric, i.bound_ms,
       round(i.achieved_p99_ms::numeric,1) p99, round(i.achieved_max_ms::numeric,1) mx,
       i.is_violation viol, round(i.overage_abs_ms::numeric,1) ov_ms,
       round(i.overage_ratio::numeric,4) ov_r,
       i.n_requests_over_bound n_over, round(i.fraction_requests_over_bound::numeric,6) f_over,
       i.violation_seconds v_s, round(i.observed_span_s::numeric,1) span_s,
       round(i.fraction_time_in_violation::numeric,6) f_time,
       round(i.worst_request_ms::numeric,1) worst_ms, i.has_raw_backing raw
  FROM provenance.v_infraction i
 WHERE (i.run_id LIKE 'a12:%' OR i.run_id LIKE 'a13:%') AND i.sla_metric IN ('ttft','itl')
 ORDER BY i.sla_metric, i.run_id;
```

TTFT (bound 1000 ms):

```
        run_id         | window_name |   p99   |   mx    | viol | ov_ms  |  ov_r  | n_over |  f_over  | v_s  |  span_s  |  f_time  | worst_ms | raw
-----------------------+-------------+---------+---------+------+--------+--------+--------+----------+------+----------+----------+----------+-----
 a12:burst1_fc_chronos | burst1      |   651.1 |  2503.2 | f    |    0.0 | 0.0000 |    203 | 0.003133 |  202 |  29939.3 | 0.006747 |   2503.2 | t
 a12:burst1_fc_timesfm | burst1      |   671.3 |  2591.7 | f    |    0.0 | 0.0000 |    253 | 0.003904 |  221 |  29939.3 | 0.007382 |   2591.7 | t
 a12:burst1_fc_toto    | burst1      |   671.6 |  2899.6 | f    |    0.0 | 0.0000 |    248 | 0.003827 |  222 |  29939.3 | 0.007415 |   2899.6 | t
 a12:burst1_reactive   | burst1      |  1664.7 |  4329.2 | t    |  664.7 | 0.6647 |   3038 | 0.046880 | 1326 |  29939.3 | 0.044290 |   4329.2 | t
 a12:burst3_fc_chronos | burst3      |   651.1 |  2185.8 | f    |    0.0 | 0.0000 |      3 | 0.000970 |    3 |   1619.7 | 0.001852 |   2185.8 | t
 a12:burst3_fc_timesfm | burst3      |   651.1 |  2185.8 | f    |    0.0 | 0.0000 |      3 | 0.000970 |    3 |   1619.7 | 0.001852 |   2185.8 | t
 a12:burst3_fc_toto    | burst3      |   651.1 |  2185.8 | f    |    0.0 | 0.0000 |      3 | 0.000970 |    3 |   1619.7 | 0.001852 |   2185.8 | t
 a12:burst3_reactive   | burst3      | 10573.7 | 15902.8 | t    | 9573.7 | 9.5737 |    308 | 0.099580 |   87 |   1619.7 | 0.053714 |  15902.8 | t
 a12:burst4_fc_chronos | burst4      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     36 | 0.001404 |   36 |  11339.2 | 0.003175 |   2572.5 | t
 a12:burst4_fc_timesfm | burst4      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     36 | 0.001404 |   36 |  11339.2 | 0.003175 |   2572.5 | t
 a12:burst4_fc_toto    | burst4      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     36 | 0.001404 |   36 |  11339.2 | 0.003175 |   2572.5 | t
 a12:burst4_reactive   | burst4      |  2807.0 |  6395.6 | t    | 1807.0 | 1.8070 |   1988 | 0.077538 |  708 |  11339.2 | 0.062438 |   6395.6 | t
 a12:burst5_fc_chronos | burst5      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     11 | 0.001225 |   11 |   4858.4 | 0.002264 |   2572.5 | t
 a12:burst5_fc_timesfm | burst5      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     11 | 0.001225 |   11 |   4858.4 | 0.002264 |   2572.5 | t
 a12:burst5_fc_toto    | burst5      |   651.1 |  2572.5 | f    |    0.0 | 0.0000 |     11 | 0.001225 |   11 |   4858.4 | 0.002264 |   2572.5 | t
 a12:burst5_reactive   | burst5      |  2181.6 |  3470.6 | t    | 1181.6 | 1.1816 |    608 | 0.067683 |  243 |   4858.4 | 0.050017 |   3470.6 | t
 a12:week_fc_chronos   | aggregate   |   651.1 |  4365.9 | f    |    0.0 | 0.0000 |   1941 | 0.002589 | 1552 | 483659.9 | 0.003209 |   4365.9 | t
 a12:week_fc_timesfm   | aggregate   |   651.1 |  4365.9 | f    |    0.0 | 0.0000 |   1804 | 0.002407 | 1513 | 483659.9 | 0.003128 |   4365.9 | t
 a12:week_fc_toto      | aggregate   |   651.1 |  4365.9 | f    |    0.0 | 0.0000 |   1945 | 0.002595 | 1524 | 483659.9 | 0.003151 |   4365.9 | t
 a12:week_reactive     | aggregate   |  1191.6 | 15902.8 | t    |  191.6 | 0.1916 |  10824 | 0.014440 | 4803 | 483659.9 | 0.009931 |  15902.8 | t
 a13:ft_llm_reactive   |             |  1144.8 | 15902.8 | t    |  144.8 | 0.1448 |  13286 | 0.013286 | 5899 | 604799.7 | 0.009754 |  15902.8 | t
 a13:ft_llm_static     |             |   655.2 |  4365.9 | f    |    0.0 | 0.0000 |   2072 | 0.002072 | 1968 | 604799.7 | 0.003254 |   4365.9 | t
```

ITL (bound 100 ms) — **note `has_raw_backing = f` on every ITL row; duration is not computable for
ITL either**, only magnitude:

```
        run_id         | window_name |  p99  | viol | ov_ms  |  ov_r
-----------------------+-------------+-------+------+--------+--------
 a12:burst1_fc_*       | burst1      | 5.2-5.5 | f  |    0.0 | 0.0000
 a12:burst1_reactive   | burst1      | 124.1 | t    |   24.1 | 0.2408
 a12:burst3_fc_*       | burst3      | 5.1-5.2 | f  |    0.0 | 0.0000
 a12:burst3_reactive   | burst3      | 160.8 | t    |   60.8 | 0.6080
 a12:burst4_fc_*       | burst4      |   5.1 | f    |    0.0 | 0.0000
 a12:burst4_reactive   | burst4      | 151.1 | t    |   51.1 | 0.5108
 a12:burst5_fc_*       | burst5      |   5.1 | f    |    0.0 | 0.0000
 a12:burst5_reactive   | burst5      | 145.9 | t    |   45.9 | 0.4589
 a12:week_fc_*         | aggregate   | 5.9-6.3 | f  |    0.0 | 0.0000
 a12:week_reactive     | aggregate   |  21.1 | f    |    0.0 | 0.0000
 a13:ft_llm_reactive   |             |  22.2 | f    |    0.0 | 0.0000
 a13:ft_llm_static     |             |   6.0 | f    |    0.0 | 0.0000
```

**Unlike the encoder pool, the language pool separates policies on every window.** Forecast holds
TTFT p99 at 651.1 ms and ITL p99 at ~5.1 ms universally; reactive violates TTFT on **all five**
windows and violates ITL on **four of five** (aggregate reactive at 21.1 ms is the one ITL pass,
because week-scale aggregation masks the burst excursions — the dashboard-masking effect).

**The duration numbers are the most under-used evidence in the store.** Reactive burst3 fails TTFT
for **87 s of a 1,619.7 s window (5.37 % of wall-clock)** affecting **9.96 % of requests**; burst4
fails for 708 s (6.24 %) affecting 7.75 %. These are per-request, raw-backed, and they answer "how
long was it broken" — a question the boolean `feasible` flag cannot.

### B.3 Fulltrace language (A13/A14)

```sql
SELECT l.run_id, l.completed_requests req, round(l.median_ttft_ms::numeric,1) t50,
       round(l.p90_ttft_ms::numeric,1) t90, round(l.p99_ttft_ms::numeric,1) t99,
       round(l.max_ttft_ms::numeric,1) tmax, round(l.p99_itl_ms::numeric,2) itl99,
       round(l.p99_tpot_ms::numeric,2) tpot99, round(l.gpu_hours::numeric,2) gpu_h,
       round(l.decode_worker_seconds::numeric,1) dec_ws
  FROM provenance.llm_run_summary l
 WHERE l.run_id LIKE 'a13:%' OR l.run_id LIKE 'a14:%' ORDER BY 1;
```

```
       run_id        |   req   | t50  |  t90  |  t99   |  tmax   | itl99 | tpot99 | gpu_h  |  dec_ws
---------------------+---------+------+-------+--------+---------+-------+--------+--------+-----------
 a13:ft_llm_reactive | 1000000 | 25.7 | 155.6 | 1144.8 | 15902.8 | 22.20 |  33.81 | 352.87 |  635172.2
 a13:ft_llm_static   | 1000000 | 22.8 |  93.0 |  655.2 |  4365.9 |  6.03 |  11.11 | 672.01 | 1209616.7
 a14:chronos_e2e     |  749601 | 22.6 |  95.9 |  651.1 |  4365.9 |  6.17 |   9.79 | 528.28 |  950911.1
 a14:timesfm_e2e     |  931628 | 22.7 |  93.7 |  651.1 |  4365.9 |  6.12 |   9.01 | 704.98 | 1268961.4
 a14:toto_e2e        |  872980 | 22.8 |  91.8 |  651.1 |  4365.9 |  6.35 |   9.01 | 751.43 | 1352581.0
```

H100 GPU-hours here are **stored**, not derived (contrast §A.2(a)).

---

## C. JOINT / COMPOSED E2E

Complete `v_joint_e2e` — all 20 rows, the entire request-linked composed evidence in the store:

```sql
SELECT window_name, arm, forecast_model, n_requests,
       encoder_delay_p99_ms enc, ttft_p99_ms ttft, itl_p99_ms itl,
       e2e_p99_ms e2e, e2e_max_ms e2e_max, gpu_hours,
       naive_sum_of_p99s_ms naive_sum,
       round(naive_sum_minus_joined_ms::numeric,1) err_ms,
       round(naive_sum_over_joined_ratio::numeric,4) err_x,
       e2e_vs_sum_evidence
  FROM provenance.v_joint_e2e ORDER BY window_name, arm;
```

```
 window_name |    arm     | model   | n_req  |   enc   |  ttft   |  itl  |   e2e   | e2e_max | gpu_h  | naive_sum | err_ms | err_x  |    evidence
-------------+------------+---------+--------+---------+---------+-------+---------+---------+--------+-----------+--------+--------+--------------------------
 aggregate   | fc_chronos | chronos | 749601 |   588.4 |   651.1 |   6.3 |  1239.5 | 38188.0 | 550.21 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 aggregate   | fc_timesfm | timesfm | 749601 |   588.4 |   651.1 |   5.9 |  1239.5 | 38182.4 | 610.65 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 aggregate   | fc_toto    | toto    | 749601 |   588.4 |   651.1 |   6.3 |  1239.5 | 38188.0 | 609.18 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 aggregate   | reactive   |         | 749601 |   588.4 |  1191.6 |  21.1 |  1695.9 | 38049.5 | 281.46 |    1780.0 |   84.1 | 1.0496 | strictly_differs_from_sum
 burst1      | fc_chronos | chronos |  64804 |   588.4 |   651.1 |   5.2 |  1239.5 |  2503.2 | 114.32 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst1      | fc_timesfm | timesfm |  64804 |   588.4 |   671.3 |   5.4 |  1258.4 |  3035.7 |  93.82 |    1259.7 |    1.3 | 1.0010 | strictly_differs_from_sum
 burst1      | fc_toto    | toto    |  64804 |   588.4 |   671.6 |   5.5 |  1259.2 |  3735.3 |  72.54 |    1260.0 |    0.8 | 1.0006 | strictly_differs_from_sum
 burst1      | reactive   |         |  64804 |   588.4 |  1664.7 | 124.1 |  2069.2 |  4650.4 |  20.51 |    2253.1 |  183.9 | 1.0889 | strictly_differs_from_sum
 burst3      | fc_chronos | chronos |   3093 |   588.4 |   651.1 |   5.1 |  1239.5 |  2185.8 |   6.34 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst3      | fc_timesfm | timesfm |   3093 |   588.4 |   651.1 |   5.2 |  1239.5 |  2185.8 |   4.87 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst3      | fc_toto    | toto    |   3093 |   588.4 |   651.1 |   5.1 |  1239.5 |  2185.8 |   6.31 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst3      | reactive   |         |   3093 | 16078.7 | 10573.7 | 160.8 | 21868.0 | 24877.1 |   1.04 |   26652.4 | 4784.4 | 1.2188 | strictly_differs_from_sum
 burst4      | fc_chronos | chronos |  25639 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  49.44 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst4      | fc_timesfm | timesfm |  25639 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  49.74 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst4      | fc_toto    | toto    |  25639 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  48.87 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst4      | reactive   |         |  25639 |   588.4 |  2807.0 | 151.1 |  3064.0 |  7846.8 |   8.13 |    3395.4 |  331.4 | 1.1082 | strictly_differs_from_sum
 burst5      | fc_chronos | chronos |   8983 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  20.98 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst5      | fc_timesfm | timesfm |   8983 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  21.18 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst5      | fc_toto    | toto    |   8983 |   588.4 |   651.1 |   5.1 |  1239.5 |  2572.5 |  20.93 |    1239.5 |    0.0 | 1.0000 | coincides_with_sum
 burst5      | reactive   |         |   8983 |   588.4 |  2181.6 | 145.9 |  2714.4 | 11633.8 |   3.39 |    2770.0 |   55.6 | 1.0205 | strictly_differs_from_sum
```

### C.1 Where the naive sum of per-pool p99s differs from the measured join — with numbers

**The brief's framing is correct and the store bears it out exactly.** `e2e_p99_ms` is the p99 of
**per-request** composed latency (stages joined on request identity, *then* the percentile).
`naive_sum_of_p99s_ms = enc_p99 + ttft_p99` is a different quantity with no interpretation, because
the two percentiles are attained by different requests.

**Every reactive arm strictly differs; the error is always the naive sum OVERSTATING the truth:**

| window | arm | measured E2E p99 | naive sum | absolute error | ratio |
|---|---|---|---|---|---|
| burst3 | reactive | **21,868.0** | 26,652.4 | **+4,784.4 ms** | **1.2188** |
| burst4 | reactive | **3,064.0** | 3,395.4 | +331.4 ms | 1.1082 |
| burst1 | reactive | **2,069.2** | 2,253.1 | +183.9 ms | 1.0889 |
| aggregate | reactive | **1,695.9** | 1,780.0 | +84.1 ms | 1.0496 |
| burst5 | reactive | **2,714.4** | 2,770.0 | +55.6 ms | 1.0205 |
| burst1 | fc_timesfm | 1,258.4 | 1,259.7 | +1.3 ms | 1.0010 |
| burst1 | fc_toto | 1,259.2 | 1,260.0 | +0.8 ms | 1.0006 |
| all 13 other forecast arms | — | 1,239.5 | 1,239.5 | 0.0 | 1.0000 |

**Stated as the brief asks: the naive sum is exact for forecast (0.00–0.13 % error) and materially
wrong for reactive (2.05 %–21.88 % error, worst case +4.78 seconds on burst3).**

The asymmetry has a physical cause, not a data-quality cause. On forecast arms the encoder is never
saturated, so both stage distributions are pinned near-deterministic at their service floors
(enc 588.4, ttft 651.1); when both stages are near-deterministic the p99 of the sum *happens* to
equal the sum of the p99s. That is arithmetic coincidence. `e2e_vs_sum_evidence` records this per
row and **neither value is a defect flag**:

- `strictly_differs_from_sum` (7 rows) — **independently proves** the join. A stored sum cannot be
  less than itself, and all 7 differing rows are strictly *below* the sum.
- `coincides_with_sum` (13 rows) — consistent with the join, but not proof of it.

The clincher that the join is real on the coinciding rows too: `e2e_max_ms` **varies by window**
(2,185.8 / 2,572.5 / 3,735.3 / 38,188.0) off a supposedly identical stage distribution. A hardcoded
additive placeholder could not produce that.

**Rule for the results chapter: never write `enc_p99 + ttft_p99` and call it an E2E latency. If a
composed number is needed for steady24h, burst2, burst6 or fulltrace, it does not exist — say so.**

---

## D. COST RATIOS, WITH THE DENOMINATOR NAMED

### D.1 The three denominators, and the fact that two of them coincide

```sql
SELECT * FROM provenance.v_grid_static_effective;
```

```
 static_encoder_workers_effective | binding_window_effective | static_as_ingested | binding_as_ingested
----------------------------------+--------------------------+--------------------+---------------------
                                8 | burst2                   |                 16 | burst1
```

| `denominator_kind` | What it assumes | Value here |
|---|---|---|
| `deployable_static_c8` | C=8 held for the span; provisionable with **no foreknowledge**. Most operationally honest. | 8 × span |
| `grid_sla_minimal_static` | max over per-window C\*, held for the span; smallest single static fleet meeting SLA everywhere. Needs the whole trace known in advance. | **also 8** × span |
| `per_window_optimum` | this window's SLA-minimal C\* — an **oracle**. Strictest; flatters autoscaling least. | 6/7/7/8 × span |

**`deployable_static_c8` and `grid_sla_minimal_static` currently COINCIDE** (both C=8). Agreement
between them is **not** independent corroboration; report it as one argument, not two.

Per-window C\*, with the burst5 supersession applied (use `grid_window_effective`, never
`grid_window`, never `v_grid_cheapest_feasible`):

```sql
SELECT window_name, c_star_as_ingested, c_star_effective, is_superseded,
       round(span_h::numeric,3) span_h, gpu_hours_rtx5090_effective gpuh,
       overprovision_vision_x_as_ingested op_in, overprovision_vision_x_effective op_eff
  FROM provenance.grid_window_effective ORDER BY window_name;
```

```
 window_name | c_star_as_ingested | c_star_effective | is_superseded | span_h | gpuh  | op_in | op_eff
-------------+--------------------+------------------+---------------+--------+-------+-------+--------
 burst1      |                  6 |                6 | f             |  8.316 |  49.9 |  2.67 |   1.33
 burst2      |                  8 |                8 | f             |  1.899 | 15.19 |     2 |      1
 burst3      |                  7 |                7 | f             |  0.450 |  3.15 |  2.29 |   1.14
 burst4      |                  7 |                7 | f             |  3.150 | 22.05 |  2.29 |   1.14
 burst5      |                 16 |                8 | t             |  1.349 | 10.79 |     1 |      1
 burst6      |                  6 |                6 | f             |  1.366 |   8.2 |  2.67 |   1.33
 steady24h   |                  2 |                2 | f             | 23.999 |    48 |     8 |      4
```

### D.2 Canonical arms — every ratio under every denominator

```sql
WITH arm AS (SELECT c.window_name w, c.arm, d.run_id FROM provenance.composed_e2e c
  JOIN provenance.v_dim d ON d.source_path='/home/gio/tese/'||c.composed_trace)
SELECT a.w, a.arm, r.denominator_kind, r.denominator_workers dw,
       round(r.numerator_worker_seconds::numeric,0) num_ws,
       round(r.denominator_worker_seconds::numeric,0) den_ws,
       round(r.cost_ratio::numeric,4) ratio,
       round((100*r.savings_ratio)::numeric,1) pct_cheaper,
       r.denominator_window_mismatch mism
  FROM arm a JOIN provenance.v_cost_ratio r ON r.run_id=a.run_id
 ORDER BY a.w, a.arm, r.denominator_kind;
```

```
     w     |    arm     |    denominator_kind     | dw | num_ws  | den_ws  | ratio  | pct_cheaper | mism
-----------+------------+-------------------------+----+---------+---------+--------+-------------+------
 aggregate | fc_timesfm | deployable_static_c8    |  8 | 2335020 | 3869278 | 0.6035 |        39.7 | f
 aggregate | fc_timesfm | grid_sla_minimal_static |  8 | 2335020 | 3869278 | 0.6035 |        39.7 | f
 burst1    | fc_chronos | deployable_static_c8    |  8 |  540203 |  239514 | 2.2554 |      -125.5 | f
 burst1    | fc_chronos | grid_sla_minimal_static |  8 |  540203 |  239514 | 2.2554 |      -125.5 | f
 burst1    | fc_chronos | per_window_optimum      |  6 |  540203 |  179636 | 3.0072 |      -200.7 | f
 burst1    | fc_timesfm | deployable_static_c8    |  8 |  552772 |  239514 | 2.3079 |      -130.8 | f
 burst1    | fc_timesfm | per_window_optimum      |  6 |  552772 |  179636 | 3.0772 |      -207.7 | f
 burst1    | fc_toto    | deployable_static_c8    |  8 |  537383 |  239514 | 2.2436 |      -124.4 | f
 burst1    | fc_toto    | per_window_optimum      |  6 |  537383 |  179636 | 2.9915 |      -199.2 | f
 burst1    | reactive   | deployable_static_c8    |  8 |  557459 |  239514 | 2.3275 |      -132.7 | f
 burst1    | reactive   | per_window_optimum      |  6 |  557459 |  179636 | 3.1033 |      -210.3 | f
 burst3    | fc_chronos | deployable_static_c8    |  8 |   32228 |   12958 | 2.4872 |      -148.7 | f
 burst3    | fc_chronos | per_window_optimum      |  7 |   32228 |   11338 | 2.8425 |      -184.3 | f
 burst3    | fc_timesfm | deployable_static_c8    |  8 |   23364 |   12958 | 1.8031 |       -80.3 | f
 burst3    | fc_timesfm | per_window_optimum      |  7 |   23364 |   11338 | 2.0607 |      -106.1 | f
 burst3    | fc_toto    | deployable_static_c8    |  8 |   28644 |   12958 | 2.2106 |      -121.1 | f
 burst3    | fc_toto    | per_window_optimum      |  7 |   28644 |   11338 | 2.5264 |      -152.6 | f
 burst3    | reactive   | deployable_static_c8    |  8 |   28356 |   12958 | 2.1884 |      -118.8 | f
 burst3    | reactive   | per_window_optimum      |  7 |   28356 |   11338 | 2.5010 |      -150.1 | f
 burst4    | fc_chronos | deployable_static_c8    |  8 |  238173 |   90714 | 2.6255 |      -162.6 | f
 burst4    | fc_chronos | per_window_optimum      |  7 |  238173 |   79374 | 3.0006 |      -200.1 | f
 burst4    | fc_timesfm | deployable_static_c8    |  8 |  263477 |   90714 | 2.9045 |      -190.4 | f
 burst4    | fc_timesfm | per_window_optimum      |  7 |  263477 |   79374 | 3.3194 |      -231.9 | f
 burst4    | fc_toto    | deployable_static_c8    |  8 |  243739 |   90714 | 2.6869 |      -168.7 | f
 burst4    | fc_toto    | per_window_optimum      |  7 |  243739 |   79374 | 3.0707 |      -207.1 | f
 burst4    | reactive   | deployable_static_c8    |  8 |  242404 |   90714 | 2.6722 |      -167.2 | f
 burst4    | reactive   | per_window_optimum      |  7 |  242404 |   79374 | 3.0539 |      -205.4 | f
 burst5    | fc_chronos | deployable_static_c8    |  8 |   88806 |   38863 | 2.2851 |      -128.5 | f
 burst5    | fc_chronos | per_window_optimum      |  8 |   88806 |   38863 | 2.2851 |      -128.5 | f
 burst5    | fc_timesfm | deployable_static_c8    |  8 |   96748 |   38863 | 2.4894 |      -148.9 | f
 burst5    | fc_toto    | deployable_static_c8    |  8 |   88969 |   38863 | 2.2893 |      -128.9 | f
 burst5    | reactive   | deployable_static_c8    |  8 |   98643 |   38863 | 2.5382 |      -153.8 | f
```

(`grid_sla_minimal_static` rows omitted where identical to `deployable_static_c8`; on burst5,
`per_window_optimum` also coincides because C\* = 8 there.)

**THE SINGLE MOST IMPORTANT HONESTY POINT IN THIS PACK: on every burst window, every autoscaling
arm — forecast AND reactive — costs 1.80× to 3.32× MORE than static.** `cost_ratio > 1` is not a
bug and filtering it away would be selecting on the dependent variable. Short bursty windows do not
give an autoscaler enough runway to amortise spin-up; the saving is a **week-scale** phenomenon
that only materialises once calm periods are included. The thesis is right to headline the
aggregate, but the results chapter should show this table, because it is the boundary condition on
the claim.

### D.3 The 0.62× headline — stated in full, and its ρ-frontier

The headline cell (hand-computed ratio is required here; see §0.5):

```sql
SELECT model, window_name, quantile, rho, readiness, lead_s, ws, denom_static_c8_ws,
       round(ratio_vs_static::numeric,6) ratio, round(p99_ms::numeric,3) p99, feasible
  FROM provenance.ewma_ablation_cell
 WHERE window_name='aggregate' AND ratio_vs_static IS NOT NULL
 ORDER BY ratio_vs_static;
```

Key rows (48 returned):

```
   model   | quantile | rho | readiness | lead_s |    ws     |  ratio   |   p99    | feasible
-----------+----------+-----+-----------+--------+-----------+----------+----------+---------
 chronos   | p50      |  15 | warm      |     30 |  982874.8 | 0.254000 | 2758.810 | f
 ewma-wsc  | p90      |  25 | warm      |     30 | 1391114.7 | 0.359500 |  906.600 | t
 chronos   | p90      |  25 | warm      |     30 | 1551944.8 | 0.401100 |  750.404 | t
 chronos   | p90      |  20 | warm      |     30 | 1865594.8 | 0.482200 |  630.479 | t
 ewma-wsc  | p90      |  15 | warm      |     30 | 2163749.5 | 0.559200 |  589.301 | t
 chronos   | p90      |  15 | strict    |    165 | 2274104.7 | 0.587700 |  589.301 | t
 chronos   | p90      |  15 | strict    |     30 | 2387924.7 | 0.617100 |  589.301 | t
 chronos   | p90      |  15 | warm      |     30 | 2410754.7 | 0.623100 |  589.301 | t   <-- HEADLINE
 ewma-add  | p90      |  15 | warm      |     30 | 2696099.3 | 0.696800 |  589.301 | t
 chronos   | p90      |  10 | warm      |     30 | 3436304.7 | 0.888100 |  589.301 | t
 ewma-mult | p90      |  15 | warm      |     30 | 4217578.8 | 1.090000 |  589.301 | t
```

**Stated in full: 0.62× = the provisioned encoder-worker-seconds of the Chronos p90 forecast policy
(ρ=15, L=30 s, warm-pool readiness, issue-time actuation) over the 5.60-day covered span
(2,410,754.7 worker-seconds), divided by the provisioned worker-seconds of the deployable static
fleet C=8 over the same span (8 × 483,659.8 = 3,869,278.4 worker-seconds).** Any quotation omitting
the denominator, the span, the readiness model or the actuation basis is incomplete.

Exact value: `2410754.7 / 3869278.4 = 0.6231044…`. **`ratio_vs_static` is stored pre-rounded to
4 dp** (0.623100) — recompute from `ws / denom_static_c8_ws` if more precision is needed, and never
chain the rounded cell (`SCHEMA_GUIDE` §4.6).

**The ρ-frontier (Chronos p90, warm, L=30) — and the thesis reports it honestly:**
ρ=10 → 0.8881, ρ=15 → **0.6231**, ρ=20 → 0.4822, ρ=25 → 0.4011. The thesis prints
"0.89/0.62/0.48/0.40×" at `closedloop.tex:243` ✓ and explicitly justifies ρ=15 as a *deliberately
conservative* operating point, noting ρ=20 passes 60/60 cells more cheaply. **No discrepancy.**

**EWMA-width-scaled is cheaper than Chronos at the headline point (0.5592 vs 0.6231, identical
p99 589.301) — and the thesis already handles this**: `tab:cl-ewma` shows EWMA-wsc failing burst3
(2,084 ms) and burst5 (divergent), so it is cheaper but per-episode infeasible. The published EWMA
ratios (0.70 add / 1.09 mult / 0.56 wsc) reproduce as 0.6968 / 1.0900 / 0.5592 ✓.

**CAUTION on `ewma_ablation_cell.denom_static_c8_ws`:** it is the constant **3,869,278.4 on all 208
rows**, which is the C=8 cost of the *aggregate* window. On the 160 non-aggregate rows it belongs to
a different window (for burst3 it is ~299× too large). The loader correctly left `ratio_vs_static`
NULL there. **Computing `ws / denom_static_c8_ws` on a burst row yields a meaningless number and
raises no error.**

### D.4 The aggregate frontier, and fulltrace (hand-computed — see §0.5)

The full aggregate ladder, all policies, against C=8 = 3,869,278.4 ws:

```sql
SELECT d.run_id, d.policy, d.forecast_model, d.quantile, d.rho, d.lead_s,
       s.encoder_workers cw, s.encoder_delay_p99_ms p99, s.provisioned_worker_seconds ws,
       round((s.provisioned_worker_seconds/3869278.4)::numeric,4) ratio_c8
  FROM provenance.v_dim d JOIN provenance.encoder_run_summary s ON s.run_id=d.run_id
 WHERE d.window_name='aggregate' ORDER BY s.provisioned_worker_seconds;
```

Anchor rows (122 returned):

```
          run_id           | policy   | q   | rho | L   | cw |   p99    |    ws     | ratio_c8
---------------------------+----------+-----+-----+-----+----+----------+-----------+---------
 misc:static_C2 / a6:*     | static   |     |     |     |  2 | 2952.781 |  967319.7 |   0.2500
 misc:fc_p50_L30_issuetime | forecast | p50 |  15 |  30 |  2 | 2735.075 |  982874.8 |   0.2540
 misc:fc_p90_L30_issuetime | forecast | p90 |  15 |  30 |  2 |   588.37 | 2410754.7 |   0.6231
 a12:week_encoder_timesfm  |          |     |     |     |  2 |   588.37 | 2335019.6 |   0.6035
 a6:toto_p90_L30           |          | p90 |     |  30 |  2 |   588.37 | 2389709.5 |   0.6176
 a6:react_L30              | reactive |     |  15 |  30 |  2 |   588.37 | 2611319.7 |   0.6749
 factorial:react_rho15_L300| reactive |     |  15 | 300 |  2 |  904.739 | 1671854.8 |   0.4321
 misc:week_static_C6       | static   |     |     |     |  6 |  904.739 | 2901959.1 |   0.7500
 misc:week_static_C7       | static   |     |     |     |  7 |  764.524 | 3385619.0 |   0.8750
 misc:week_static_C8       | static   |     |     |     |  8 |   644.44 | 3869278.8 |   1.0000
 misc:static_C16           | static   |     |     |     | 16 |  565.249 | 7738557.6 |   2.0000
```

**Fulltrace, hand-computed.** `windows.fulltrace.span_s = 604,799.7`, so C=8 = 4,838,397.6 ws —
which is `a13:ft_static_C8.provisioned_worker_seconds` **exactly**, confirming the denominator:

| arm | ws | ÷ C=8 (4,838,397.6) | ÷ C=2 (1,209,599.4) | enc p99 | verdict |
|---|---|---|---|---|---|
| `a13:ft_static_C8` | 4,838,397.6 | 1.0000 | 4.0000 | 677.5 | pass |
| `a13:ft_reactive_L30` | 3,323,189.5 | **0.6868** | 2.7473 | 588.4 | pass |
| `a13:ft_static_C2` | 1,209,599.4 | 0.2500 | 1.0000 | **2,904.6** | **FAIL** |

**On the full 7-day trace, reactive reaches 0.687× C=8 while holding the SLA.** This is the
strongest single-number result in the store that does *not* depend on a forecaster, and it is
currently invisible to `v_cost_ratio`.

### D.5 The language-pool ratio — 0.96×, and it is a KNOWN OPEN DEFECT

```sql
WITH n AS (SELECT gpu_hours num FROM provenance.llm_run_summary WHERE run_id='planner:week_fc_p90'),
     s AS (SELECT gpu_hours ft  FROM provenance.llm_run_summary WHERE run_id='a13:ft_llm_static')
SELECT n.num AS fc_gpu_h, s.ft AS static_fulltrace_gpu_h,
       s.ft*(483659.8/604799.7)               AS den_span_scaled,
       n.num/(s.ft*(483659.8/604799.7))       AS ratio_span_scaled,
       4*483668382.4763285/3.6e6              AS den_4gpu_artifact,
       n.num/(4*483668382.4763285/3.6e6)      AS ratio_4gpu,
       s.ft*(749601.0/1000000)                AS den_req_scaled,
       n.num/(s.ft*(749601.0/1000000))        AS ratio_req_scaled
  FROM n,s;
```

```
     fc_gpu_h      | static_fulltrace | den_span_scaled  | ratio_span_scaled  | den_4gpu_artifact | ratio_4gpu | den_req_scaled | ratio_req_scaled
-------------------+------------------+------------------+--------------------+-------------------+------------+----------------+------------------
 518.6063450234815 | 672.0093014234247| 537.407482716333 | 0.9650151173969128 | 537.4093138625872 | 0.9650118  | 503.7388443563 | 1.0295143
```

| denominator (NAMED) | value (H100 GPU-h) | ratio |
|---|---|---|
| static TP2×2 full-trace, **time-scaled** to the 5.60-d span | 537.4075 | **0.96502** |
| static TP2×2 as **4 constant GPUs × artifact span** (483,668,382.48 ms) | 537.4093 | **0.96501** |
| static TP2×2 full-trace, **request-scaled** (749,601/1,000,000) | 503.7388 | **1.02951** |

**The thesis prints 0.96×. The correct two-decimal rounding of 0.96501 is 0.97×.** This is
`audit/internal_defects.json:246` and `audit/adversarial/conclusion.json:51`, already adjudicated
as `THESIS_WRONG` (rounding), affecting `conclusion.tex:85`, `closedloop.tex:375`, and the
abstract/resumo in `tese.tex` (`0.96` / `0,96`). It is a **knife-edge**: the value sits 1.2e-5
above the 0.965 tie point, so the fifth significant digit decides it, and the spread *between*
defensible denominators (3.3e-6) is smaller than that margin. 0.96 is reachable only by truncation,
and the same paragraph rounds its companions half-up (625/537.4 → 1.16; 641/537.4 → 1.19).

**Recommended (per the adversarial pass): weaken rather than restate** — "at essentially
break-even against its burst-sized static shape (518.6 versus 537.4 H100 GPU-hours)". That is the
brief's "near-break-even" and it is the robust statement. Note the request-scaled denominator gives
**1.03×** (forecast *more* expensive), which is why the time-matched denominator must be named.

---

## E. IMPROVEMENT SUMMARY — by how much, including where forecast is WORSE

### E.1 Encoder pool

| window | metric | static C=8 | reactive L=30 | forecast p90 L=30 | forecast vs reactive |
|---|---|---|---|---|---|
| aggregate | enc p99 (ms) | 644.4 | 588.4 | 588.4 | **tie** (both at floor) |
| aggregate | ws (M) | 3.87 | 2.61 | 2.41 | **−7.7 %** |
| aggregate | ×C=8 | 1.00 | 0.675 | **0.623** | −0.052× |
| burst1 | enc p99 | — | 588.4 | 588.4 | **tie** |
| burst1 | ws | 239.5k (C8) | 557.5k | 540.2k | −3.1 % |
| burst3 | enc p99 | — | **16,078.7** | 588.4 | **−96.3 % (27.3× better)** |
| burst3 | ws | 13.0k (C8) | 28.4k | 32.2k | **+13.7 % (forecast WORSE)** |
| burst4 | enc p99 | — | 588.4 | 588.4 | **tie** |
| burst4 | ws | 90.7k (C8) | 242.4k | 238.2k | −1.8 % |
| burst5 | enc p99 | — | 588.4 | 588.4 | **tie** |
| burst5 | ws | 38.9k (C8) | 98.6k | 88.8k | −9.9 % |
| steady24h | enc p99 | — | 682.1 | 677.4 | −0.7 % (negligible) |
| steady24h | ws (L=165) | — | 142.3k | 162.1k | **+13.9 % (forecast WORSE)** |
| fulltrace | enc p99 | 677.5 | 588.4 | *(no forecast arm)* | — |
| fulltrace | ×C=8 | 1.00 | **0.687** | *(unavailable)* | — |

**Where forecast is WORSE or break-even on the encoder:**
- **Latency: break-even on 4 of 5 jointly-covered windows.** Forecast and reactive both sit at the
  588.4 ms service floor on aggregate, burst1, burst4, burst5. The entire encoder-latency win is
  burst3 (and, from §A.4, burst2 and burst6 at long lead).
- **Cost: forecast is more expensive than reactive on burst3 (+13.7 %) and on steady24h at L=165
  (+13.9 %).** On the calm day, anticipation earns nothing and costs more.
- **Cost vs static: forecast loses badly on every burst window** (1.80×–3.32×, §D.2). The 0.62×
  saving is a week-scale result only.

**Where forecast wins decisively:**
- burst3 encoder p99 **16,078.7 → 588.4 ms** (−96.3 %), turning a 15.08× SLA overage into a pass.
- Lead-robustness: reactive degrades monotonically with lead (burst3: 9,481 → 16,079 → 28,342 →
  54,170 ms at L=15/30/45/165) while forecast holds 588.4 ms at **every** lead.
- Cold-start efficiency: warm-up fraction ≤9.4 % for forecast vs up to **73.7 %** for reactive (§A.3).

### E.2 Language pool

| window | metric | reactive | forecast (chronos) | forecast vs reactive |
|---|---|---|---|---|
| aggregate | TTFT p99 (ms) | 1,191.6 **FAIL** | 651.1 **pass** | −45.4 % |
| aggregate | ITL p99 (ms) | 21.14 pass | 6.32 pass | −70.1 % |
| aggregate | TPOT p99 (ms) | 36.45 | 9.43 | −74.1 % |
| aggregate | H100 GPU-h | 281.46 | 550.21 | **+95.5 % (forecast WORSE)** |
| burst1 | TTFT p99 | 1,664.7 **FAIL** | 651.1 **pass** | −60.9 % |
| burst1 | ITL p99 | 124.08 **FAIL** | 5.22 pass | −95.8 % |
| burst1 | GPU-h | 20.51 | 114.32 | **+457 % (forecast WORSE)** |
| burst3 | TTFT p99 | 10,573.7 **FAIL** | 651.1 **pass** | −93.8 % |
| burst3 | ITL p99 | 160.80 **FAIL** | 5.13 pass | −96.8 % |
| burst3 | GPU-h | 1.04 | 6.34 | **+510 % (forecast WORSE)** |
| burst4 | TTFT p99 | 2,807.0 **FAIL** | 651.1 **pass** | −76.8 % |
| burst4 | ITL p99 | 151.08 **FAIL** | 5.14 pass | −96.6 % |
| burst5 | TTFT p99 | 2,181.6 **FAIL** | 651.1 **pass** | −70.2 % |
| burst5 | ITL p99 | 145.89 **FAIL** | 5.14 pass | −96.5 % |
| fulltrace | TTFT p99 | 1,144.8 **FAIL** | 655.2 (static) **pass** | −42.8 % |
| fulltrace | H100 GPU-h | 352.87 | 672.01 (static) | +90.4 % |

**This is the brief's "near-break-even language fleet", and it needs stating carefully.** Two
different comparisons are in play and they point opposite ways:

1. **Forecast vs reactive on the language pool: forecast is 2×–6× MORE expensive in GPU-hours**
   (aggregate +95.5 %, burst1 +457 %, burst3 +510 %). Reactive is cheap because it under-provisions
   decode capacity — which is precisely why it fails TTFT on all five windows and ITL on four. The
   "saving" is the SLA violation. This comparison should never be quoted as a language-pool win.

2. **Forecast vs the burst-sized static language shape: essentially break-even** — 518.6 vs 537.4
   H100 GPU-hours over the 5.60-day span, **0.965×** (§D.5). This is the defensible statement, and
   "break-even" is a more honest word than any two-decimal ratio given the knife-edge.

**The language pool is where forecasting buys compliance, not savings.** The encoder pool is where
it buys savings (0.62× at week scale). Conflating the two is the main risk in the results chapter.

### E.3 Joint

- Forecast holds composed E2E p99 at **1,239.5 ms** on 13 of 15 forecast arms (1,258.4 / 1,259.2 on
  the two burst1 outliers) — a flat, window-independent result.
- Reactive composed E2E p99 ranges **1,695.9 → 21,868.0 ms**, i.e. **1.37× to 17.64× worse** than
  forecast on the same window.
- Worst case (burst3): **21,868.0 vs 1,239.5 ms = 17.6× better under forecast.**
- The naive-sum error is ≤0.13 % for forecast and 2.05 %–21.88 % for reactive (§C.1).

---

## 6. TRUST, DISCREPANCIES AND WHAT IS NOT AVAILABLE

### 6.1 Stability re-verification (post-ingest)

All headline numbers re-run against the settled 3,044-run store — **unchanged**:

```sql
SELECT run_id, encoder_delay_p99_ms p99, provisioned_worker_seconds ws
  FROM provenance.encoder_run_summary WHERE run_id IN
  ('misc:fc_p90_L30_issuetime','misc:fc_p50_L30_issuetime','a6:static_C2','a6:static_C8',
   'a6:react_L30','misc:week_static_C8','a13:ft_static_C8','a13:ft_static_C2','a13:ft_reactive_L30');
```

```
          run_id           |   p99    |    ws
---------------------------+----------+-----------
 a13:ft_reactive_L30       |   588.37 | 3323189.5
 a13:ft_static_C2          | 2904.556 | 1209599.4
 a13:ft_static_C8          |  677.461 | 4838397.6
 a6:react_L30              |   588.37 | 2611319.7
 a6:static_C2              | 2952.781 |  967319.7
 a6:static_C8              |   644.44 | 3869278.8
 misc:fc_p50_L30_issuetime | 2735.075 |  982874.8
 misc:fc_p90_L30_issuetime |   588.37 | 2410754.7
 misc:week_static_C8       |   644.44 | 3869278.8
```

`v_grid_static_effective` unchanged (C=8, binding burst2). `composed_e2e` still 20 rows.

### 6.2 Verification of the thesis's `tab:cl-aggregate` — every row reproduces

| thesis row | thesis p99 / Mws / ×static | DB run_id | DB p99 / ws / ratio | verdict |
|---|---|---|---|---|
| Static C=8 (deployable) | 644 / 3.87 / 1.00 | `misc:week_static_C8` | 644.44 / 3,869,278.8 / 1.0000 | ✓ |
| Static C=2 (calm-day opt) | 2,953 / 0.97 / 0.25 | `a6:static_C2` | 2,952.781 / 967,319.7 / 0.2500 | ✓ |
| Forecast p90 L=30 issue-time | 588 / 2.41 / 0.62 | `misc:fc_p90_L30_issuetime` | 588.37 / 2,410,754.7 / 0.6231 | ✓ |
| Forecast p90 L=165 issue-time | 588 / 2.41 / 0.62 | `misc:fc_p90_L165_issuetime` | 588.37 / 2,406,584.7 / 0.6220 | ✓ |
| Forecast p50 L=30 | 2,735 / 0.98 / 0.25 | `misc:fc_p50_L30_issuetime` | 2,735.075 / 982,874.8 / 0.2540 | ✓ |
| Reactive L=30 | 588 / 2.61 / 0.67 | `a6:react_L30` | 588.37 / 2,611,319.7 / 0.6749 | ✓ |
| Reactive L=300 | 905 / 1.67 / 0.43 | `factorial:react_rho15_L300` | 904.739 / 1,671,854.8 / 0.4321 | ✓ |

**All seven rows reproduce.** Also verified: ρ-frontier 0.89/0.62/0.48/0.40 ✓; `tab:cl-ewma`
0.70/1.09/0.56 ✓; target-time vs issue-time 2.38M vs 2.41M ✓ (`factorial:forecast_p90_chronos_rho15_L30`
= 2,375,654.6 vs `misc:fc_p90_L30_issuetime` = 2,410,754.7); strict-re-warm 0.59–0.62 ✓
(0.5877 at L=165 to 0.6202 at L=15).

### 6.3 Numbers that DISAGREE with what the thesis prints

**(1) Language-pool 0.96× should be 0.97× (or, better, "essentially break-even").** §D.5. Already
adjudicated `THESIS_WRONG`; still present at `conclusion.tex:85`, `closedloop.tex:375`,
`tese.tex` (abstract + resumo). Knife-edge; the recommended fix is to weaken the claim, not restate
the digit.

**(2) `ewma_ablation_cell.p99_ms` and `encoder_run_summary.encoder_delay_p99_ms` disagree for the
SAME run.** Joining on identical `provisioned_worker_seconds`:

```sql
SELECT e.model,e.quantile,e.rho,e.readiness,e.lead_s,e.ws,e.p99_ms AS ewma_cell_p99,
       s.run_id, s.encoder_delay_p99_ms AS enc_summary_p99,
       e.p99_ms - s.encoder_delay_p99_ms AS delta
  FROM provenance.ewma_ablation_cell e
  JOIN provenance.encoder_run_summary s ON s.provisioned_worker_seconds = e.ws
 WHERE e.window_name='aggregate' AND s.run_id LIKE 'misc:fc_%issuetime%';
```

```
  model  | q   | rho | readiness | L   |    ws     | ewma_cell_p99 |             run_id              | enc_summary_p99 |  delta
---------+-----+-----+-----------+-----+-----------+---------------+---------------------------------+-----------------+---------
 chronos | p50 |  15 | warm      |  30 |  982874.8 |       2758.81 | misc:fc_p50_L30_issuetime       |        2735.075 | 23.735
 chronos | p90 |  15 | warm      |  15 | 2411099.7 |       589.301 | misc:fc_p90_L15_issuetime       |          588.37 |   0.931
 chronos | p90 |  15 | warm      | 165 | 2406584.7 |       589.301 | misc:fc_p90_L165_issuetime      |          588.37 |   0.931
 chronos | p90 |  15 | warm      |  30 | 2410754.7 |       589.301 | misc:fc_p90_L30_issuetime       |          588.37 |   0.931
 chronos | p90 |  15 | warm      |  45 | 2410304.7 |       589.301 | misc:fc_p90_L45_issuetime       |          588.37 |   0.931
 chronos | p90 |  10 | warm      |  30 | 3436304.7 |       589.301 | misc:fc_p90_rho10_L30_issuetime |          588.37 |   0.931
 chronos | p90 |  20 | warm      |  30 | 1865594.8 |       630.479 | misc:fc_p90_rho20_L30_issuetime |         628.618 |   1.861
 chronos | p90 |  25 | warm      |  30 | 1551944.8 |       750.404 | misc:fc_p90_rho25_L30_issuetime |         748.543 |   1.861
```

`ewma_ablation_cell.p99_ms` is **systematically higher** by 0.93–23.7 ms. The thesis quotes **588**
from `encoder_run_summary` in `tab:cl-aggregate` and **589** from `ewma_ablation_cell` in
`tab:cl-ewma` — internally consistent with its two sources, but **the two DB tables disagree about
the same run**. This is not currently covered by any check in `21_checks.sql`. It does not move any
verdict (both sides pass 1,000 ms), but a results chapter printing both tables should either
reconcile them or state which projection each column comes from. **Recommend adding a check.**

**(3) Not a discrepancy, but a trap corrected:** `grid_window.c_star` for burst5 is **16**; the
publishable value is **8** (`grid_window_effective`, `is_superseded = t`). `v_grid_cheapest_feasible`
also reports 16 — it is an *audit* view that recomputes from the raw curves and is doing its job.
Never publish from it. Likewise `overprovision_vision_x` for steady24h is 8.0 as ingested and
**4.0** effective.

### 6.4 Figures that are NOT AVAILABLE (say so; do not approximate)

1. **Composed E2E for steady24h, burst2, burst6, fulltrace** — `composed_e2e` has 20 rows covering
   5 windows × 4 arms only. No static arm has a composed E2E at all.
2. **Encoder time-in-violation / fraction-of-requests-over-bound, any window, any policy** —
   structurally uncomputable: no per-request encoder delay is stored (`encoder_series` is per-second
   occupancy). `v_infraction` returns NULL and `has_raw_backing = f` for all `encoder_delay` rows.
3. **ITL time-in-violation** — same: `has_raw_backing = f` on every ITL row. Magnitude only.
4. **ITL p50 / p90 / max, any run** — `llm_run_summary` stored only mean and p99 for ITL. NULL means
   *never computed*, not zero.
5. **Encoder GPU-hours as a stored quantity** — derived only, under 1 worker = 1 RTX-5090 (§A.2a).
6. **Warm-up / cold-start for the aggregate window** — `has_cold_start_accounting = f` on all four
   aggregate arms; `cost_accounting` covers 40 cells and aggregate is not among them. Unmeasured,
   not zero.
7. **Warm-up for the timesfm and toto forecast arms** — `cost_accounting` has no model dimension;
   only the chronos and reactive rows are trustworthy (§A.2b).
8. **Cost ratio for `misc:fc_p90_L30_issuetime`, `a6:toto_p90_L30`, `a6:react_L30`, and all of
   `a13`** — NULL `window_name` on the spine; hand-computed in §D.3/§D.4 with the denominator
   written out (§0.5).
9. **A forecast arm on fulltrace** — `a13` has static C=2, static C=8 and reactive only. The A14
   runs cover per-model max spans (749,601 / 931,628 / 872,980 requests), not the full 1,000,000.
10. **Any number from `a16`, `a16_ft`, `g2`, `g3_32b`, `g4`, `g6`** — still-generating families,
    excluded by the brief, now physically present in the store and responsible for the two new
    `error`-severity check failures (§0.2).

### 6.5 Recommended store fixes arising from this pass

| # | Defect | Fix |
|---|---|---|
| 1 | `runs.window_name` NULL for `misc:fc_p90_L30_issuetime`, `misc:fc_p50_L30_issuetime`, `a6:*`, all `a13:*` | populate → restores `v_cost_ratio` coverage for the headline and fulltrace arms |
| 2 | `week` alias reintroduced by g2 ingest (`C210` error) | re-run `22_corrections.sql` over g2 |
| 3 | `composed_request` partitions missing for a16/a16_ft/g2/g4 (`C603` error) | register the families before further ingest |
| 4 | `ewma_ablation_cell.p99_ms` vs `encoder_run_summary` disagree 0.93–23.7 ms | add a cross-projection check; document which is canonical |
| 5 | `ewma_ablation_cell.ratio_vs_static` stored pre-rounded to 4 dp | document; always recompute from `ws / denom` |
| 6 | `cost_accounting` lacks a forecast-model key, so `v_pool_cost` mis-attributes warm-up to 2 of 3 forecast arms | add `model` to the PK, or have `v_pool_cost` NULL the warm-up columns when the decomposition identity fails |
