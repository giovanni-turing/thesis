# SCHEMA_GUIDE — `provenance` (PostgreSQL 16)

**Audience: an LLM agent that must answer questions about these experiments in SQL and must not be
misled.** Every query below was executed against the live store while this file was written
(`postgres@localhost:5433`, schema `provenance`, 2026-07-20) and the outputs pasted are real. Nothing
is documented here that was not run.

Connect:

```bash
export PGPASSWORD=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' postgres \
  | sed -n 's/^POSTGRES_PASSWORD=//p')
psql -h localhost -p 5433 -U goku -d postgres -c "SET search_path=provenance,public; ..."
```

---

## 1. ORIENTATION

### What the store is

`provenance` is a **byte-faithful archive of experiment artifacts, plus a semantic layer over it.**
211 tables (including partitions), 56 views, 5 materialized views, 99,019,523 rows, 21 GB. Data
generation is **complete** and the store is effectively read-only. The experiments are a two-pool
(vision encoder + language)
disaggregated LLM serving study: a 1,000,000-request trace is replayed through a simulator under
static, reactive and forecast-driven encoder-autoscaling policies, and the results are compared against
a static grid sweep, against silicon measurements from a physical GPU collector, and against a measured
vLLM deployment.

The design intent is a **star schema**:

- **`runs`** is the spine — one row per experiment run, carrying every dimension
  (`pool`, `window_name`, `policy`, `model`, `quantile`, `lead_s`, `rho`, `resolution`,
  `actuation`, `engine`, `tp`, `experiment`, `is_current`, `source_path`). **3,147 rows**, of which
  2,461 are `is_current`.
- **`windows`** is the second dimension — one row per trace window (`aggregate`, `burst1..burst6`,
  `steady24h`, `e7..e18`, `head2k`, the per-model forecast spans). Carries `span_s`, the multiplier
  that turns a worker count into worker-seconds. Every `runs.window_name` is drawn from it (`C209`).
- **Summary facts** hang off `runs` by `run_id`: `llm_run_summary`, `encoder_run_summary`,
  `factorial_cell`, `composed_e2e`, `sweep_point`, `grid_*`, `ewma_ablation_cell`, `verification`.
- **Raw facts** are LIST-partitioned by `experiment`: `composed_request` (**41,106,599** rows),
  `llm_request` (**18,869,922**), `encoder_series` (**10,342,685**), `forecast` (**22,003,500**),
  `worker_schedule` (**235,827**, the C(t) step function). Since the 2026-07-20 partition migration
  **no rows remain in any default partition** and `experiment = 'misc'` is empty.
- **`ingest_log`** records every file loaded, with sha256, kind code and row count. **4,149 rows over
  4,149 distinct files** (1:1), every one of which still exists on disk.

The intent is only partly realised. **§4 and §6 are not optional reading** — they are the difference
between a correct answer and a confidently wrong one.

### How to answer a typical question, in one paragraph

Start at **`v_dim`**, never at `runs` — `v_dim` is one row per run with the vocabulary drift folded away
(`'both (E2E)'→'both'`, `'vLLM'→'vllm'`, `'1min'→'60s'`, `'week'→'aggregate'`, and the seven spellings of
the encoder worker count collapsed to one column). Join the semantic view that owns your quantity:
`v_pool_latency` for latency, `v_pool_cost` for cost, `v_cost_ratio` for anything comparative,
`v_infraction` for SLA questions, `v_joint_e2e` for end-to-end. Always filter `is_current`. Before
quoting a number, ask three questions: *is there a denominator, and is it stated?* (§4.1); *am I adding
percentiles?* (§4.2); *has this row been superseded?* (§4.3). If the number is a percentile of a run,
you can re-derive it from raw with `provenance.check_run(run_id)` or
`provenance.recompute_p99(run_id, metric)` — but only **178 of 610** language summaries have raw
backing (§4.5), so check `v_llm_summary_backing` first and say "summary-only, not recomputable" when
it is.

---

## 2. QUESTION → TABLE MAP

Each subsection: the question, the relation to use, a runnable query, and its real output.

### 2.1 Latency by pool — `v_pool_latency`

Long form, one row per `(run_id, sla_metric)` where `sla_metric ∈ {encoder_delay, ttft, itl}`.
Everything is **milliseconds** and every column name says so. The two pools do not share an SLA
metric, which is exactly why this is long form and not a wide row.

```sql
SELECT window_name, forecast_model, lead_s,
       round(p99_ms::numeric,1) AS p99_ms,
       round(max_ms::numeric,1) AS max_ms
  FROM provenance.v_pool_latency
 WHERE sla_metric = 'encoder_delay' AND policy = 'forecast' AND is_current
 ORDER BY p99_ms DESC LIMIT 8;
```

```
 window_name | forecast_model | lead_s | p99_ms  | max_ms
-------------+----------------+--------+---------+---------
 burst3      |                |        | 54169.5 | 63447.5
 burst3      |                |        | 54169.5 | 63447.5
 e13         |                |    165 |  6786.6 |  9971.7
 e13         | timesfm        |    165 |  6786.6 |  9971.7
 e13         | toto           |    165 |  6786.6 |  9971.7
 e13         | timesfm        |     30 |  6093.2 |  8177.8
 e13         | toto           |     30 |  6093.2 |  8177.8
 e13         | timesfm        |     45 |  6093.2 |  8177.8
```

Note the NULL `forecast_model` rows and the duplicate-looking pairs: `runs.model` is not populated for
every family. Group by the dimensions you actually filtered on, and do not assume one row per
configuration.

**ITL asymmetry:** for `sla_metric='itl'`, `p50_ms`, `p90_ms` and `max_ms` are NULL because
`llm_run_summary` only ever stored mean and p99 for ITL. NULL means *never computed*, not zero.

### 2.2 Cost — `v_pool_cost`

Canonicalises the seven spellings of provisioned worker-seconds. Encoder rows carry
`provisioned_worker_seconds` / `busy_worker_seconds` / `utilization_ratio`; language rows carry
`gpu_hours` and `prefill+decode` worker-seconds and have NULL utilization (busy time was never
measured there). This asymmetry is real, not an ingest gap.

```sql
SELECT window_name, policy, lead_s,
       round(provisioned_worker_seconds::numeric,1) AS ws,
       round(warmup_worker_seconds::numeric,1)      AS warmup_ws,
       round(warmup_fraction::numeric,4)            AS warmup_frac
  FROM provenance.v_pool_cost
 WHERE has_cold_start_accounting
 ORDER BY warmup_fraction DESC NULLS LAST LIMIT 5;
```

```
 window_name |  policy  | lead_s |    ws    | warmup_ws | warmup_frac
-------------+----------+--------+----------+-----------+-------------
 burst3      | reactive |    165 |  17018.1 |   12540.0 |      0.7369
 burst3      | reactive |    165 |  17018.1 |   12540.0 |      0.7369
 steady24h   | reactive |    165 | 142256.7 |   49170.0 |      0.3456
 burst5      | reactive |    165 |  80910.6 |   20460.0 |      0.2529
 burst1      | reactive |    165 | 469903.9 |  106755.0 |      0.2272
```

**Critical:** `provisioned_worker_seconds` **excludes** cold-start/warm-up. On burst3 reactive at
L=165 the omitted warm-up is **73.7%** of the true bill — the headline cost understates it by nearly
a factor of four. Where `cost_accounting`
covers the cell, the warm-up component is exposed separately. `has_cold_start_accounting = FALSE`
means *unmeasured*, not *zero* — `cost_accounting` has only 40 rows.

**Select on `source_relation`, not on `pool`.** 372 runs carry `encoder_run_summary` rows while being
labelled `pool='both'`; `WHERE pool='encoder'` silently drops them. `v_cost_ratio` does this correctly
(`WHERE source_relation='encoder_run_summary'`).

### 2.3 Cost ratios / "X% cheaper" — `v_cost_ratio` (**mandatory**, see §4.1)

Never compute a cost ratio by hand. `v_cost_ratio` emits one row per *(run, denominator)* and carries
the denominator as columns. Three denominators, all defensible, all separate rows.

```sql
SELECT denominator_kind, denominator_workers,
       round(denominator_worker_seconds::numeric,0) AS den_ws,
       round(numerator_worker_seconds::numeric,0)   AS run_ws,
       round(cost_ratio::numeric,4)                 AS ratio,
       round((100*savings_ratio)::numeric,1)        AS pct_cheaper
  FROM provenance.v_cost_ratio
 WHERE window_name='aggregate' AND policy='forecast' AND is_current
 ORDER BY denominator_kind, cost_ratio LIMIT 5;
```

```
   denominator_kind   | denominator_workers | den_ws  | run_ws | ratio  | pct_cheaper
----------------------+---------------------+---------+--------+--------+------
 deployable_static_c8 |                   8 | 3869278 | 668040 | 0.1727 | 82.7
 deployable_static_c8 |                   8 | 3869278 | 670935 | 0.1734 | 82.7
 deployable_static_c8 |                   8 | 3869278 | 686865 | 0.1775 | 82.2
 deployable_static_c8 |                   8 | 3869278 | 726165 | 0.1877 | 81.2
 deployable_static_c8 |                   8 | 3869278 | 726270 | 0.1877 | 81.2
```

The **thesis headline 0.62×** is a specific cell, not the minimum of this view:

```sql
SELECT model, window_name, quantile, rho, readiness, lead_s,
       round(ws::numeric,1) AS ws, denom_static_c8_ws,
       round(ratio_vs_static::numeric,4) AS ratio,
       round(p99_ms::numeric,3) AS p99_ms, feasible
  FROM provenance.ewma_ablation_cell
 WHERE model='chronos' AND window_name='aggregate' AND quantile='p90'
   AND rho=15 AND readiness='warm' AND lead_s=30;
```

```
  model  | window_name | quantile | rho | readiness | lead_s |    ws     | denom_static_c8_ws | ratio  | p99_ms  | feasible
---------+-------------+----------+-----+-----------+--------+-----------+--------------------+--------+---------+---
 chronos | aggregate   | p90      |  15 | warm      |     30 | 2410754.7 |          3869278.4 | 0.6231 | 589.301 | t
```

Stated in full: **0.62× = provisioned encoder-worker-seconds of the Chronos p90 forecast policy
(ρ=15, L=30 s, warm readiness) over the 5.60-day covered span, divided by the provisioned
worker-seconds of the deployable static fleet C=8 over the same span.** Any quotation of 0.62× that
omits the denominator, the span or the readiness model is incomplete.

### 2.4 Feasibility / static optimum — `grid_window_effective`, `v_grid_static_effective`

Use `grid_window_effective`, **not** `grid_window` and **not** `v_grid_cheapest_feasible`, for any
published fleet-sizing number. It applies the burst5 correction (§4.3).

For the **fleet-wide** static configuration use `grid_run_summary_effective`, never
`grid_run_summary` and never its `raw` JSON:

```sql
SELECT static_encoder_workers_as_ingested, static_encoder_workers_effective,
       static_encoder_workers_is_superseded
  FROM provenance.grid_run_summary_effective;
--  16 | 8 | t
```

`static_encoder_workers = 16` was the max over a per-window `C*` set in which burst5 was wrongly 16;
the corrected max is **8**, attained at burst2 and burst5. Everything derived from the stale 16 moved with
it: `overprovision_vision_x` is superseded on **all seven** windows (steady24h 8.0 → **4.0**, the calm-day
overprovisioning headline; bursts 2.67/2.0/2.29/2.29/1.0/2.67 → 1.33/1.0/1.14/1.14/1.0/1.33). The archived
values, including `grid_run_summary.raw->'headline'->'overprovision_vs_per_window'`, are preserved
byte-for-byte and must never be quoted; every supersession is itemised in `provenance.grid_correction`.

The same treatment applies to the phase-E silicon comparison: read
`collector_multiworker_window_effective` (burst5 `aic_feasible_cstar` 16 → 8, `silicon_feasible_cstar`
16 → 15, `worker_inflation_x` 1.0 → 1.88). The **fleet** silicon `C* = 16` is unchanged — it is now
attained at burst2's genuine measured knee rather than at burst5's artifact.

```sql
SELECT window_name, c_star_as_ingested, c_star_effective, is_superseded,
       round(span_h::numeric,3) AS span_h, gpu_hours_rtx5090_effective,
       overprovision_vision_x_as_ingested, overprovision_vision_x_effective
  FROM provenance.grid_window_effective ORDER BY window_name;
```

```
 window_name | c_star_as_ingested | c_star_effective | is_superseded | span_h | gpu_hours_rtx5090_effective | overprovision_vision_x_as_ingested | overprovision_vision_x_effective
-------------+--------------------+------------------+---------------+--------+-----------------------------+------------------------------------+----------------------------------
 burst1      |                  6 |                6 | f             |  8.316 |                        49.9 |                          2.67 |                        1.33
 burst2      |                  8 |                8 | f             |  1.899 |                       15.19 |                             2 |                           1
 burst3      |                  7 |                7 | f             |  0.450 |                        3.15 |                          2.29 |                        1.14
 burst4      |                  7 |                7 | f             |  3.150 |                       22.05 |                          2.29 |                        1.14
 burst5      |                 16 |                8 | t             |  1.349 |                       10.79 |                             1 |                           1
 burst6      |                  6 |                6 | f             |  1.366 |                         8.2 |                          2.67 |                        1.33
 steady24h   |                  2 |                2 | f             | 23.999 |                          48 |                             8 |                           4
```

```sql
SELECT * FROM provenance.v_grid_static_effective;
```

```
 static_encoder_workers_effective | binding_window_effective | static_as_ingested | binding_as_ingested
----------------------------------+--------------------------+--------------------+-----------
                                8 | burst2                   |                 16 | burst1
```

The SLA bounds all three metrics are judged against live in `v_sla_bound`: encoder_delay p99 ≤ 1000 ms,
ttft p99 ≤ 1000 ms, itl p99 ≤ 100 ms.

### 2.5 Infraction intensity — `v_infraction`

The store's native feasibility flags (`factorial_cell.feasible`, `grid_vision_point.feasible`,
`sweep_point.over_threshold`) are booleans; they cannot distinguish a 3 ms miss from a 24 s miss.
`v_infraction` adds magnitude, and — for `ttft` only — duration from raw `llm_request`.

```sql
SELECT CASE WHEN overage_ratio <= 0.05 THEN 'marginal(<=5%)'
            WHEN overage_ratio <= 0.50 THEN 'moderate'
            ELSE 'catastrophic(>50%)' END AS severity,
       sla_metric, count(*)
  FROM provenance.v_infraction
 WHERE is_violation AND is_current
 GROUP BY 1,2 ORDER BY 3 DESC;
```

```
      severity      |  sla_metric   | count
--------------------+---------------+-------
 catastrophic(>50%) | encoder_delay |   310
 catastrophic(>50%) | ttft          |   194
 catastrophic(>50%) | itl           |   144
 moderate           | encoder_delay |   122
 moderate           | itl           |    74
 moderate           | ttft          |    49
 marginal(<=5%)     | encoder_delay |    27
 marginal(<=5%)     | itl           |    22
 marginal(<=5%)     | ttft          |     1
```

**Two hard limits.** (a) `violation_seconds` / `fraction_time_in_violation` /
`fraction_requests_over_bound` exist **only for `sla_metric='ttft'`** — `has_raw_backing` says so per
row. There is no stored per-request encoder delay (`encoder_series` is per-second *occupancy*), so
time-in-violation for the vision pool is genuinely uncomputable, not merely missing. Queue depth is not
a substitute. (b) The raw tier is a LATERAL over 15.7 M rows: **always filter by `run_id`,
`window_name` or `experiment`.** An unfiltered `SELECT *` walks the table.

Also read `queue_divergent`: TRUE means the encode queue never drained, so `achieved_p99_ms` is a lower
bound on an unbounded quantity and `overage_ratio` *understates* the failure.

### 2.6 Forecast accuracy — `forecast_metrics`, `v_forecast_best`

Dimensions: `variate ∈ {images, requests, ctx, gen}`, `resolution ∈ {1s,15s,30s,45s,1min}`,
`mode ∈ {uni,cov}` (univariate / with covariates), `span ∈ {full,common}`,
`candidate ∈ {point, p10..p90}`, `h` (horizon step; **`h = -1` is the aggregate over all horizons**),
`model ∈ {chronos, toto, timesfm, ewma, naive, holt_winters}`.

```sql
SELECT model, h, round(wape::numeric,4) AS wape
  FROM provenance.forecast_metrics
 WHERE variate='images' AND resolution='1min' AND mode='uni'
   AND span='common' AND candidate='point' AND h IN (-1,1)
 ORDER BY h, wape;
```

```
    model     | h  |  wape
--------------+----+--------
 toto         | -1 | 0.5298
 chronos      | -1 | 0.5307
 timesfm      | -1 | 0.5339
 ewma         | -1 | 0.5416
 naive        | -1 | 0.6783
 holt_winters | -1 | 0.6938
 toto         |  1 | 0.5153
 timesfm      |  1 | 0.5188
 ewma         |  1 | 0.5217
 chronos      |  1 | 0.5246
 holt_winters |  1 | 0.5946
 naive        |  1 | 0.6180
```

`v_forecast_best` gives the min-WAPE forecaster per `(variate, resolution, mode)` directly.
**Always quote WAPE from the unrounded column** — the inter-model gaps here are ~0.001–0.01, smaller
than one printed digit (§4.6).

### 2.7 Silicon vs model (AIC under-modelling) — `collector_encoder_fn`

Measured GPU vision-tower latency beside the aiconfigurator analytic prediction, per batch size.
`ratio_meas_over_aic` is the headline quantity.

```sql
SELECT n_images, round(mean_ms::numeric,2) AS meas_ms, aic_pred_ms,
       round(ratio_meas_over_aic::numeric,4) AS ratio
  FROM provenance.collector_encoder_fn
 WHERE source_path LIKE '%anchor_dense_sdpa_2400%' AND n_images IN (8,32,64,96,128)
 ORDER BY n_images;
```

```
 n_images | meas_ms | aic_pred_ms | ratio
----------+---------+-------------+--------
        8 |   58.71 |      43.126 | 1.3613
       32 |  253.80 |     160.196 | 1.5843
       64 |  511.57 |     316.369 | 1.6170
       96 |  771.29 |     519.941 | 1.4834
      128 | 1034.98 |     723.514 | 1.4305
```

The measured band over N ≤ 64 is **1.3613 (N=8) – 1.6170 (N=64)**, which is the "≈1.4–1.6×" the thesis
reports. `aic_pred_ms` is NULL beyond N=128, so ratios do not exist at N ∈ {192,256,512}. Sibling
tables: `collector_fn`, `collector_kernel_perf`, `collector_vit_op_breakdown`,
`collector_burst_anchor_latency`, `collector_system_spec`.

### 2.8 Coverage — `v_coverage`, `coverage`, `coverage_meta`

```sql
SELECT fleet, run, pool, requests, expect, is_full, ok
  FROM provenance.v_coverage WHERE fleet='A13';
```

```
 fleet |       run       |   pool   | requests | expect  | is_full | ok
-------+-----------------+----------+----------+---------+---------+----
 A13   | ft_static_C8    | encoder  |  1000000 | 1000000 | t       | t
 A13   | ft_static_C2    | encoder  |  1000000 | 1000000 | t       | t
 A13   | ft_reactive_L30 | encoder  |  1000000 | 1000000 | t       | t
 A13   | ft_llm_static   | language |  1000000 | 1000000 | t       | t
 A13   | ft_llm_reactive | language | 1000000  | 1000000 | t       | t
```

80 rows total across A11/A12/A13/A14. The A14 rows use `pool = 'both (E2E)'` — a spelling that exists
**only** in `coverage`; `v_dim` folds it to `'both'`. The trace splits exactly
1,000,000 = 749,601 (forecast-covered span) + 250,399 (context days); check `C103` verifies it.

### 2.9 Trace characterization — `eda_metric` and friends

`eda_metric` is a long-form key/value store: `(script, metric_path, run_id, signal, window_bin, stat,
value_num, value_bool, value_text)`. 14 scripts, 1,469 rows.

```sql
SELECT script, metric_path, value_num
  FROM provenance.eda_metric
 WHERE script='d_signals' AND (metric_path LIKE 'pearson_1min%' OR metric_path LIKE '%r2')
 ORDER BY metric_path;
```

```
  script   |        metric_path         |      value_num
-----------+----------------------------+---------------------
 d_signals | constant_fraction_fit.r2   | 0.12253911262014872
 d_signals | pearson_1min.ctx_vs_req    |  0.6630381074227859
 d_signals | pearson_1min.gen_vs_req    |  0.8121338734126078
 d_signals | pearson_1min.img_vs_ctx    |  0.8935608337383335
 d_signals | pearson_1min.img_vs_req    |  0.3546002012649865
```

Companion tables: `eda_rate_series` (2.74 M per-second rate rows), `eda_burst_episode`,
`eda_request_class`, `eda_request_archetype`, `eda_silhouette`. **Caveat:** `eda_burst_episode` holds
24 `episode_kind='merged'` rows, a *different population* from the 18 episodes the EDA figures report.
Filter `episode_kind` explicitly.

### 2.10 Measured ground truth (real vLLM deployment) — `measured_request`, `vllm_*`

One measured deployment, `run_id = 'measured:vllm_h100_trace'`, 7,817 requests. This is the only
non-simulated request-level data in the store.

```sql
SELECT run_id, check_name, level, passed, detail
  FROM provenance.vllm_reconcile_check WHERE level='hard';
```

```
          run_id          |    check_name     | level | passed |                        detail
--------------------------+-------------------+-------+--------+------------------------------------------------
 measured:vllm_h100_trace | join_1to1         | hard  | t      | client=7817 otlp=7817 fe=7817 merged=7817 unique=True
 measured:vllm_h100_trace | all_status_200    | hard  | t      | non-200=0
 measured:vllm_h100_trace | completion_eq_gen | hard  | t      | mismatch=0
 measured:vllm_h100_trace | token_accounting  | hard  | t      | template_tokens range=[8,12] mode=9
 measured:vllm_h100_trace | phase_identity    | hard  | t      | max|q+pf+dc+other-e2e|=0.00e+00s
 measured:vllm_h100_trace | ttft_le_e2e       | hard  | t      | violations=0
```

All 6 hard reconciliation checks pass; **1 of 7 soft checks fails** (`client_gen_tokens_eq_g...`,
check `C107`, severity `warn`). Detail tables: `vllm_token_itl` (1,354,025 rows — exactly
`SUM(gen_tokens)`), `vllm_engine_step`, `vllm_bucket_1s`, `vllm_vision_encode`, `vllm_prom_sample`
(2.25 M), `vllm_detok`, `vllm_sys_sample`. Two views reconstruct parquet files that were deliberately
*not* ingested because they are pure derivations: `v_vllm_prom_wide` and `v_vllm_vision_cost_by_n`.

> **Unit trap, `measured_request`:** TTFT is stored **twice**, `ttft_server` in **seconds** and
> `ttft_server_ms` in **milliseconds**, and the seconds column is unlabelled.
> `SELECT count(*), round(avg(ttft_server)::numeric,4), round(avg(ttft_server_ms)::numeric,2)
>  FROM provenance.measured_request;` → `7817 | 0.4746 | 474.55`. Use only the `_ms` form.

### 2.11 End-to-end composition — `v_joint_e2e` (see §4.2)

### 2.12 Trust / verification — `v_verification_resolved`, `v_corroboration`

`verification.run_id` is mostly stored **unprefixed** (`burst3_fc_timesfm_L60`) while `runs.run_id` is
namespaced (`a11:burst3_fc_timesfm_L60`). **Join `resolved_run_id`, never `verification.run_id`** —
either the table column or the view, which now agree.

```sql
SELECT resolution_source, count(*) FROM provenance.v_verification_resolved GROUP BY 1 ORDER BY 2 DESC;
```

```
 resolution_source | count
-------------------+-------
 stored            |   371
 unresolved        |     9
```

**371 of 380 resolve; 9 never will** (3 structural markers, 6 model-level aggregates — see §6.2).

> **Do not use `n_candidates`.** It still reports the *old* unique-suffix heuristic and shows
> `0 | 75`, which contradicts `resolution_source`. It is retained only so pre-existing queries do not
> break. `resolution_source` is the truth. Both the table column and this view were repaired
> 2026-07-20: previously the view recomputed its own pointer with
> `split_part(runs.run_id,':',2) = verification.run_id`, which can never match an already-namespaced
> id, so 66 rows that the table had resolved correctly still read as unresolvable through the view.

---

## 3. DIMENSION VOCABULARY

Live census (`runs`, **3,147 rows**; `factorial_cell` for `readiness`), re-derived 2026-07-20 at the
final-certification state:

| Dimension | Legal values (count) | Caveats |
|---|---|---|
| `pool` | `encoder` 2040, `language` 615, `both` 450, NULL 42 | `coverage` additionally uses **`both (E2E)`** — folded to `both` by `v_dim`. Many `pool='both'` runs carry encoder summaries; **filter cost on `source_relation`, not `pool`**. |
| `policy` | `forecast` 1891, NULL 738, `reactive` 290, `static` 228 | NULL is common — many families do not set it. `WHERE policy='X'` silently drops 742 runs. |
| `model` (forecast model) | NULL 1612, `chronos` 507, `toto` 506, `timesfm` 504, `ewma` 7, `naive` 4, `holt_winters` 4, `arima`/`kalman`/`prophet` 1 each | **This is the forecaster name, not the served LLM.** Filtering `runs.model` for `Qwen`/`32B` returns nothing; served-model runs live in the `g3_32b` family and are identified by `run_id` pattern and `tp`. Use `model_checkpoint` for the served checkpoint (`C412` guarantees it never holds a forecast name). |
| `quantile` | NULL 1778, `p90` 889, `p50` 475, `obs` 5 | `obs` = observed/no-quantile arm. `forecast_metrics.candidate` is a *different* vocabulary: `point, p10…p90`. |
| `resolution` | NULL 2463, `15s` 684 | `v_dim` also folds `'1min'→'60s'`; `runs` carries no `1min` rows, but `forecast_metrics.resolution` uses `1s/15s/30s/45s/1min` and is **not** folded. |
| `lead_s` | NULL 1114, 30 (677), 15 (401), 45 (399), 165 (240), 300 (222), 60 (66), 120 (27), 90 (1) | |
| `rho` | NULL 1660, 15 (472), 25 (349), 20 (335), 10 (331) | Integer percent-style band; `factorial_cell` has a `rho_band` CHECK. |
| `readiness` | `warm` 396, `strict` 300, NULL 684 (`factorial_cell`) | `warm` vs `strict` billing changes the headline ratio (0.6231 warm vs 0.6202 strict at L=15). Never mix. |
| `actuation` | NULL 1767, `issue-time` 696, **`target-time` 684** | **`target-time` now exists in `runs`** (it did not when this table was first written). `C507` guarantees `current_factorial` exposes only one actuation (`issue-time`), so published aggregates never pool the two — but a hand-written `GROUP BY` over `runs` *will*. Always state which. |
| `engine` | NULL 3140, `vLLM` 7 | Case drift is real: `v_dim` lowercases. `collector_encoder_fn.engine` is a *different* vocabulary (`sdpa`, `eager`, `flash_attention_2`, `vllm`). |
| `experiment` (partition key) | `factorial` 1380, `g6` 456, `g3_32b` 232, `g4` 165, `grid` 142, `a2x` 100, `a11` 52, `a16` 51, `a16_ft` 48, `rerun_verify` 47, `g1` 42, `predictors` 41, `a2` 40, `a2t`/`a2tf` 36, `sweeps` 33, `g2` 32, `reactive` 32, `a12` 21, `ctmatrix`/`riders` 20, `aggregate44` 18, `aggregate44_rho` 17, `eda` 16, `planner` 12, `live` 10, `a14`/`a15` 9, `aggregate44_strict` 7, `episode` 6, `a6` 5, `a13` 5, `closedloop_v2` 3, `srcbuild`/`cap_sensitivity` 2 | **`misc` is now 0** — the dumping ground is gone (`C306`, `C601`, `C603` all pass). Every family has its own partition. |
| `window_name` | `aggregate`, `burst1..burst6`, `steady24h`, `e7..e18`, `head2k`, `fulltrace`, `span_chronos`, `span_timesfm`, `span_toto`, `span_expctx` (**26** registered in `windows`) | `C209` passes: **every** `runs.window_name` is now in the dimension. Aliases still documented below. |

### Window-name drift — the biggest silent-wrong-answer generator

```sql
SELECT * FROM provenance.v_window_alias;
```

```
    alias     | canonical_window |                              note
--------------+------------------+------------------------------------------------------
 week         | aggregate        | CONFIRMED. Base tables NORMALISED 2026-07-20; now a defensive no-op.
 steady       | steady24h        | CONFIRMED (upgraded from PROBABLE). Base tables NORMALISED 2026-07-20.
 span_chronos | aggregate        | CONFIRMED: byte-identical windows row; kept only for the forecast-coverage narrative.
 head2k       |                  | GENUINELY DISTINCT. DO NOT FOLD. Registered in windows() 2026-07-20.
 fulltrace    |                  | GENUINELY DISTINCT: 7 d / 1 000 000 req, NOT the 5.60 d aggregate span. DO NOT FOLD.
```

**RESOLVED 2026-07-20 — the drift is gone from the base tables.** `schema/22_corrections.sql` normalised
every alias spelling in place (`runs` 129 and `composed_e2e` 4 `week`→`aggregate`; `rerun_b1_window` 1 and
`rerun_b1_curve_point` 20 `steady`→`steady24h`), registered `head2k` in `windows()` (2000 req / 721.072 s,
so `sweep_*` cost ratios are computable at last), and registered `span_chronos` as an alias of `aggregate`.
`C209`, `C210` and `C211` are all **green**.

```sql
SELECT (SELECT count(*) FROM provenance.v_dim WHERE window_name='aggregate') AS canon_aggregate,
       (SELECT count(*) FROM provenance.runs  WHERE window_name='aggregate') AS naive_aggregate,
       (SELECT count(*) FROM provenance.runs  WHERE window_name='week')      AS raw_week;
--  canon_aggregate | naive_aggregate | raw_week
-- -----------------+-----------------+----------
--              234 |             234 |        0     -- fold is a no-op (canon=naive); raw_week=0. Pre-normalisation this was 6 | 129 split
```

The as-ingested spelling of every row is preserved in a sibling `window_name_as_ingested` column on all
four tables; `WHERE window_name <> window_name_as_ingested` reconstructs the rename exactly.

> **TRAP — still start at `v_dim`.** The alias fold in `v_dim` is now a *defensive no-op*, retained so that
> a future ingest reintroducing the old spelling is still resolved (and still trips `C210`). The historical
> failure mode is worth remembering: `runs` used to carry both spellings, so
> `WHERE window_name='aggregate'` returned 6 of 135 rows — answering the aggregate-window question from 4 %
> of the evidence, with no error raised. Full analysis, blast radius and thesis impact (nil):
> **`provenance/audit/WINDOW_ALIAS.md`**.

### The synonym dictionary is queryable

```sql
SELECT source_table, source_column, note
  FROM provenance.v_dim_synonym
 WHERE concept='provisioned_worker_seconds' ORDER BY source_table;
```

Seven physical columns hold provisioned worker-seconds, one of them the bare `ws`
(`ewma_ablation_cell`). Encoder worker count has **eleven** spellings across ten tables. Consult
`v_dim_synonym` before writing any cross-family join.

---

## 4. THE TRAPS

Each one is a live, reproducible failure mode. All examples were executed.

### 4.0 THE SHORT LIST — traps that cost the most, including four found on 2026-07-20

Read the full subsection before relying on any of these; this is the index, not the explanation.

| # | Trap | One-line rule |
|---|---|---|
| 4.1 | cost ratio with an unstated denominator | use `v_cost_ratio`, name the `denominator_kind` |
| 4.2 | adding percentiles | E2E is a **join**, not `enc_p99 + ttft_p99` |
| 4.3 | reading a superseded base-table value | read the `*_effective` view; the DB can hold superseded artifacts |
| — | window aliases (`span_chronos`≡`aggregate`, etc.) | join through `v_dim`; never match `window_name` by string — §3 |
| — | "not in the DB" read as "unverifiable" | absence ≠ refutation; go to the named artifact — §6.15 |
| 4.5 | percentiles with no raw backing | check `v_llm_summary_backing` (432 of 610 unbacked) |
| 4.6 | recomputing a % from a rounded value | round once, at the end |
| **NEW** | `check_failures('cheap')` **hides the only error-severity failure** (`C002` is `moderate`) | preflight with `check_failures('expensive')` — §5 |
| **NEW** | `v_verification_resolved.n_candidates` contradicts the repaired pointer | read `resolution_source`, not `n_candidates` — §2.12 |
| **NEW** | `main.py` printing nonzero counters is **not** a failed idempotency check | judge by row counts + content hashes — §6.14 |
| **NEW** | `runs.actuation` now holds **two** values (`issue-time`, `target-time`) | a raw `GROUP BY` pools them; `current_factorial` does not (`C507`) — §3 |
| **NEW** | `ingest_log.run_id` is not always a spine reference | for 6 aggregate kinds it is an artifact-group label — §6.5 |

### 4.1 THE DENOMINATOR PROBLEM — a cost ratio without its denominator is not a number

**Use `v_cost_ratio`. It carries the denominator as columns and refuses to pick one for you.**

There are three defensible baselines and they are different arguments:

| `denominator_kind` | What it assumes |
|---|---|
| `deployable_static_c8` | C=8 held for the window span. The fleet you could provision with **no foreknowledge**. Most operationally honest. |
| `grid_sla_minimal_static` | max over per-window C*, held for the span. Smallest single static fleet meeting SLA **everywhere**; needs the whole trace known in advance. |
| `per_window_optimum` | this window's SLA-minimal C* (an **oracle**). Strictest; flatters autoscaling least. A saving that survives this one is real. |

Two facts you must state when using them:

1. **`deployable_static_c8` and `grid_sla_minimal_static` currently coincide** — the effective static
   fleet *is* C=8 (`v_grid_static_effective`, binding window burst2). Agreement between them is **not**
   independent corroboration.
2. **`cost_ratio > 1` is common and is not a bug.** Filtering to `cost_ratio < 1` is selecting on the
   dependent variable.

```sql
SELECT run_id, denominator_workers,
       round(numerator_worker_seconds::numeric,0)   AS num_ws,
       round(denominator_worker_seconds::numeric,0) AS den_ws,
       round(cost_ratio::numeric,3) AS ratio
  FROM provenance.v_cost_ratio
 WHERE denominator_kind='per_window_optimum' AND window_name='burst1'
   AND policy='forecast' AND is_current
 ORDER BY cost_ratio LIMIT 5;
```

```
               run_id               | denominator_workers |  num_ws |  den_ws | ratio
------------------------------------+---------------------+--------+--------+-------
 ctmatrix:forecast_burst1_p50_rho25 |                   6 | 146639 | 179636 | 0.816
 ctmatrix:forecast_burst1_p50_rho15 |                   6 | 234478 | 179636 | 1.305
 ctmatrix:forecast_burst1_p90_rho25 |                   6 | 257217 | 179636 | 1.432
 rerun_verify:fc_p90_burst1_L300    |                   6 | 409434 | 179636 | 2.279
 ctmatrix:forecast_burst1_p90_rho15 |                   6 | 417054 | 179636 | 2.322
```

On burst1 the same policy family spans **0.82× to 2.32×** against the same denominator. There is no
single "the ratio". Quote the cell.

**The live trap this view exists to prevent — `ewma_ablation_cell.denom_static_c8_ws`:**

```sql
SELECT window_name, count(*), min(denom_static_c8_ws) AS mn, max(denom_static_c8_ws) AS mx,
       count(ratio_vs_static) AS has_ratio
  FROM provenance.ewma_ablation_cell GROUP BY 1 ORDER BY 1;
```

```
 window_name | count |    mn     |    mx     | has_ratio
-------------+-------+-----------+-----------+-----------
 aggregate   |    48 | 3869278.4 | 3869278.4 |        48
 burst1      |    32 | 3869278.4 | 3869278.4 |         0
 burst3      |    32 | 3869278.4 | 3869278.4 |         0
 burst4      |    32 | 3869278.4 | 3869278.4 |         0
 burst5      |    32 | 3869278.4 | 3869278.4 |         0
 steady24h   |    32 | 3869278.4 | 3869278.4 |         0
```

`denom_static_c8_ws` is the **constant 3,869,278.4 on all 208 rows** — the C=8 cost of the *aggregate*
window (8 × 483,659.8 s). On the 160 non-aggregate rows it belongs to a different window: for burst3
(span 1,619.7 s, true C=8 cost 12,957.6) it is ~299× too large. The loader correctly left
`ratio_vs_static` NULL there, but the denominator column is still populated. **Computing
`ws / denom_static_c8_ws` on a burst row yields a meaningless number and no error.**
`v_cost_ratio.denominator_window_mismatch` flags exactly this class of error.

Related: `v_ewma_ablation_ratio` documents that `ratio_vs_static` is populated for only 48/208 rows
(23%), so any `avg(ratio_vs_static)` silently averages the aggregate window alone.

### 4.2 PERCENTILES DO NOT ADD — composed E2E is a join, not a sum

`e2e_p99_ms` is the 99th percentile of **per-request** composed latency: the vision and language stages
joined **on request identity**, *then* the percentile taken. It is **not**
`encoder_delay_p99_ms + ttft_p99_ms` — those two percentiles are attained by *different requests*, so
their sum is neither an upper nor a lower bound. `v_joint_e2e` computes the naive sum anyway, purely so
the error is visible:

```sql
SELECT window_name, arm,
       round(encoder_delay_p99_ms::numeric,1) AS enc,
       round(ttft_p99_ms::numeric,1)          AS ttft,
       round(e2e_p99_ms::numeric,1)           AS e2e,
       round(naive_sum_of_p99s_ms::numeric,1) AS naive_sum,
       round(naive_sum_over_joined_ratio::numeric,3) AS sum_over_true,
       e2e_vs_sum_evidence
  FROM provenance.v_joint_e2e
 ORDER BY abs(naive_sum_over_joined_ratio-1) DESC LIMIT 8;
```

```
 window_name |    arm     |   enc   |  ttft   |   e2e   | naive_sum | sum_over_true |    e2e_vs_sum_evidence
-------------+------------+---------+---------+---------+-----------+-------+---------------------------
 burst3      | reactive   | 16078.7 | 10573.7 | 21868.0 |   26652.4 | 1.219 | strictly_differs_from_sum
 burst4      | reactive   |   588.4 |  2807.0 |  3064.0 |    3395.4 | 1.108 | strictly_differs_from_sum
 burst1      | reactive   |   588.4 |  1664.7 |  2069.2 |    2253.1 | 1.089 | strictly_differs_from_sum
 aggregate   | reactive   |   588.4 |  1191.6 |  1695.9 |    1780.0 | 1.050 | strictly_differs_from_sum
 burst5      | reactive   |   588.4 |  2181.6 |  2714.4 |    2770.0 | 1.020 | strictly_differs_from_sum
 burst1      | fc_timesfm |   588.4 |   671.3 |  1258.4 |    1259.7 | 1.001 | strictly_differs_from_sum
 burst1      | fc_toto    |   588.4 |   671.6 |  1259.2 |    1260.0 | 1.001 | strictly_differs_from_sum
 burst5      | fc_timesfm |   588.4 |   651.1 |  1239.5 |    1239.5 | 1.000 | coincides_with_sum
```

**The size of the error: ~22% on reactive burst3 (1.219), ~0.1% on forecast arms.** The asymmetry has a
physical cause — on forecast arms the encoder is never saturated, so the encoder delay is pinned flat
at the 588.4 ms service floor and both stage distributions are near-deterministic, in which case the
p99 of the sum happens to equal the sum of the p99s. That is arithmetic coincidence, **not** additive
computation.

`e2e_vs_sum_evidence` records this per row:
- `strictly_differs_from_sum` — this row **independently proves** the join (a stored sum cannot be less
  than itself, and all 7 differing rows are strictly *below* the sum);
- `coincides_with_sum` — consistent with the join but not proof of it (the 13 floor-pinned rows).

Neither value is a data-quality flag. Do not read `coincides_with_sum` as a defect, and do not read it
as confirmation. The clincher for the join being real throughout: on those same forecast rows
`e2e_max_ms` varies by window (2185.8 / 2572.5 / 3735.3 / 38188.0) off a supposedly identical
distribution — a hardcoded additive placeholder could not do that.

**Rule: never write `enc_p99 + ttft_p99` in a query and call the result an E2E latency.**

### 4.3 THE DB CAN BE STALE — some archived rows are superseded

The store deliberately preserves the pre-correction artifact *and* records the correction. Reading the
base table gets you the retracted value.

**Case: burst5 C\*.** `grid_window.c_star = 16`; the thesis publishes **8**.

```sql
SELECT correction_id, window_name, field, correction_type,
       original_value, corrected_value, published_value, affects_headline
  FROM provenance.grid_correction;
```

```
                   correction_id                    | window_name |           field            |  correction_type   | original_value | corrected_value | published_value | affects_headline
----------------------------------------------------+-------------+----------------------------+--------------------+----------------+-----------------+-----------------+------------------
 burst5:c_star:supersession                         | burst5      | c_star                     | supersession       |             16 |               8 |               8 | f
 burst1:c_star:alternative_metric                   | burst1      | c_star                     | alternative_metric |              6 |               7 |               6 | f
 grid:static_encoder_workers:supersession           | ALL         | static_encoder_workers     | supersession       |             16 |               8 |               8 | t
 grid:steady24h:overprovision_vision_x:supersession | steady24h   | overprovision_vision_x     | supersession       |              8 |               4 |               4 | t
 grid:burst6:overprovision_vision_x:supersession    | burst6      | overprovision_vision_x     | supersession       |           2.67 |            1.33 |                 | f
 grid:burst4:overprovision_vision_x:supersession    | burst4      | overprovision_vision_x     | supersession       |           2.29 |            1.14 |                 | f
 grid:burst3:overprovision_vision_x:supersession    | burst3      | overprovision_vision_x     | supersession       |           2.29 |            1.14 |                 | f
 grid:burst2:overprovision_vision_x:supersession    | burst2      | overprovision_vision_x     | supersession       |              2 |               1 |                 | f
 grid:burst1:overprovision_vision_x:supersession    | burst1      | overprovision_vision_x     | supersession       |           2.67 |            1.33 |                 | f
 silicon:burst5:aic_feasible_cstar:supersession     | burst5      | aic_feasible_cstar         | supersession       |             16 |               8 |               8 | f
 silicon:burst5:silicon_feasible_cstar:supersession | burst5      | silicon_feasible_cstar     | supersession       |             16 |              15 |                 | f
 burst3:c_star:alternative_metric                   | burst3      | c_star                     | alternative_metric |              7 |               8 |               7 | f
 burst4:c_star:alternative_metric                   | burst4      | c_star                     | alternative_metric |              7 |               8 |               7 | f
 burst6:c_star:alternative_metric                   | burst6      | c_star                     | alternative_metric |              6 |               8 |               6 | f
 burst5:stage_conditional_baseline:supersession     | burst5      | stage_conditional_baseline | supersession       |             16 |               8 |               8 | f
(15 rows)
```

**Two of the 15 carry `affects_headline = true`** — `grid:static_encoder_workers` (16→8, the
deployable static baseline used as the cost denominator everywhere) and
`grid:steady24h:overprovision_vision_x` (8→4). Any number that touches those two must come from the
`*_effective` view, never the base table.

Note the **two different `correction_type`s**, and that they mean opposite things:
- `supersession` (burst5) — the original is **wrong**; use 8. `grid_window.is_superseded = true`.
- `alternative_metric` (burst1) — the original is **right under its own definition** (all-request
  encoder-delay p99, C*=6); C=7 is the answer under the *stage-conditional* metric (image-bearing
  requests only). `is_superseded` is **false**. Both numbers are correct; state which metric.

`v_grid_cheapest_feasible` — an audit view that recomputes the optimum from the raw feasibility curves
— **reports burst5 = 16**, because that is genuinely what the grid curves say. It is doing its job.
It is not the view to publish from.

**Checklist before quoting any grid/fleet number:**

```sql
-- 1. is the row superseded?
SELECT window_name, c_star_as_ingested, c_star_effective, is_superseded, correction_source
  FROM provenance.grid_window_effective WHERE is_superseded;
-- 2. is the RUN superseded?  v_retractions returns all 686 non-current runs; only 4 of
--    them name a successor, so filter unless you want the whole retracted set.
SELECT * FROM provenance.v_retractions WHERE coalesce(superseded_by,'') <> '';
```

```
           run_id           | experiment |         superseded_by         | ...
----------------------------+------------+-------------------------------+----
 riders:fc_scale6.22_burst4 | riders     | riders:fc_scale6.22_burst4_v2 | ...
 riders:fc_scale8_burst4    | riders     | riders:fc_scale8.0_burst4_v2  | ...
 sweeps:llm_head2k_aic_s1   | sweeps     | srcbuild:llm_head2k_aic_src   | ...
 sweeps:llm_head2k_poly_s1  | sweeps     | srcbuild:llm_head2k_poly_src  | ...
```
(The two `sweeps:*` rows are the wheel-runtime cells superseded by the `srcbuild:*` source-build
artifacts — the R4/R12 adjudication that backs `tab:sim-poly-aic`.)

**But do not trust `is_current` as a completeness signal.** It is now partially live — `is_current =
false` for **686 of 3,147** runs, so `current_runs` / `current_llm_summary` /
`current_encoder_summary` are no longer pass-throughs. But only **4** runs carry
`supersedes`/`superseded_by`, so the retraction *pointer* graph is still nearly empty while the
*flag* is meaningful. Two mechanisms coexist (§6.8); read both:
- `current_encoder_summary` — the filter removes **zero** rows (neither retracted run has an encoder
  summary). Row-identical to the unfiltered join.
- `current_factorial` — removes **zero** rows.
- `current_llm_summary` — removes exactly **2 of 495**.

`is_current = true` means **"not known to be retracted"**, never "verified correct". Real retraction is
also expressed through `grid_window.is_superseded`, `grid_correction` and `artifact_quarantine`.
`v_run_status` exposes the signals that actually discriminate (raw backing, schedule integrity,
unclassified family).

**Freshness of the drift guard.** `mv_llm_p99_check` is a *snapshot*:

```sql
SELECT * FROM provenance.v_mv_freshness;
```

```
 materialized_rows | live_eligible_rows | is_fresh
-------------------+--------------------+----------
               101 |                125 | f
```

**Currently stale**: `v_llm_drift` is silently auditing 101 of 125 eligible runs (81%) and will report
"no drift" for the 24 it cannot see. See §5.

### 4.4 NOT EVERY TABLE IS A RESULT — some raw tables are simulator INPUT

`composed_request` is the largest table in the store (~15.3 M rows). It is **the composed trace fed
into the simulator**, not an outcome:

```sql
\d provenance.composed_request
```

```
 experiment    | text             | not null
 run_id        | text             | not null
 line_index    | integer
 ts            | double precision
 input_length  | integer
 output_length | integer
 hash_ids      | bigint[]
```

**There is no latency column at all.** Any question of the form "how did the system perform" cannot be
answered from `composed_request`. Its legitimate uses are: counting requests (it backs the
`encoder_run_summary.requests = count(*)` identity, check `C004`), and characterizing the offered load.

Compare `llm_request`, which *is* an outcome — it carries `ttft_ms`, `ttst_ms`, `e2e_latency_ms`,
`itl_ms`, `arrival_time_ms`, `first_token_ms`, `last_token_ms`.

Other input-side or descriptive relations that are easy to mistake for results:

| Relation | What it actually is |
|---|---|
| `composed_request` (41.1 M) | the composed input trace; no latencies |
| `grid_command` (149) | the shell commands that ran the grid, not its results |
| `windows` | trace-window definitions (offsets, spans, request counts) |
| `worker_schedule` (235,827) | the C(t) actuation schedule — a *control input*, integrate it for cost |
| `eda_rate_series` (2.74 M) | trace arrival rates — a property of the workload, not of any system |
| `forecast` (22.0 M) | predicted series; accuracy lives in `forecast_metrics` |
| `check_definition` (70) | the test registry, not test results — run `check_all()` for those |
| `partition_migration_baseline` | pre-migration row counts, kept so conservation stays re-provable |
| `verification_resolution_backfill` | audit record of the 66 resolved_run_id fills, not a measurement |
| `v_grid_cheapest_feasible` | an **audit** view (recomputes from curves); use `grid_window_effective` to publish |
| `ledger_entry`, `vllm_critic_note`, `vllm_facet_claim` | prose/commentary, not measurements |

### 4.5 NOT ALL SUMMARIES ARE RECOMPUTABLE

```sql
SELECT has_raw_rows, count(*) AS n, sum(completed_requests) AS requests
  FROM provenance.v_llm_summary_backing GROUP BY 1;
```

```
 has_raw_rows |  n  | requests
--------------+-----+----------
 f            | 432 | 11536096
 t            | 178 | 18869922
```

**432 of 610 `llm_run_summary` rows — 11,536,096 requests — have zero backing rows in `llm_request`.**
Their percentiles cannot be audited against evidence. This is not a reason to distrust them (they came
from the producer's own computation) but it **is** a reason to label them: *"summary-only, not
recomputable"*. Affected families are concentrated in `grid`, `riders`, `sweeps`, `reactive`,
`planner`, `live`, `episode`. The raw request logs for these runs were never archived, so this cannot
be repaired from inside the store — it is permanent.

The 178 that *are* backed are checked hard: `C001` (row counts, 0 mismatches), `C002` (median, 1
known failure at 0.18 % — §6.3), `C003` (p99, worst 1.22 %). `v_llm_drift` audits all 178 and is
fresh.

For the 125 backed runs, lineage is one call:

```sql
SELECT aspect, round(stored::numeric,4) AS stored, round(recomputed::numeric,4) AS recomputed,
       round(rel_diff::numeric,9) AS rel_diff, tolerance, passed, source
  FROM provenance.check_run('g1:burst6_lang_fc_chronos_L120');
```

```
       aspect       |  stored   | recomputed |  rel_diff   | tolerance | passed |   source
--------------------+-----------+------------+-------------+-----------+--------+-------------
 completed_requests | 9821.0000 |  9821.0000 | 0.000000000 |         0 | t      | llm_request
 mean_ttft_ms       |   87.4367 |    87.4367 | 0.000000000 |     0.001 | t      | llm_request
 median_ttft_ms     |   21.5496 |    21.5496 | 0.000000000 |     0.001 | t      | llm_request
 p90_ttft_ms        |  219.6962 |   219.6962 | 0.000000000 |     0.005 | t      | llm_request
 p99_ttft_ms        |  657.0261 |   657.0186 | 0.000011479 |      0.02 | t      | llm_request
 max_ttft_ms        | 1420.7693 |  1420.7693 | 0.000000000 |     1e-06 | t      | llm_request
 p99_e2e_latency_ms | 4462.2074 |  4459.6732 | 0.000568242 |      0.02 | t      | llm_request
 p99_itl_ms         |    5.3789 |     6.1395 | 0.123891687 |      0.02 | f      | llm_request
```

**`p99_itl_ms` fails by design and is not a defect.** The stored summary ITL is **token-pooled**
(percentile over all inter-token gaps); the recomputation is over `llm_request.itl_ms`, a
**per-request mean**. They are different statistics of different populations. `v_llm_drift` omits ITL
for exactly this reason. Everything else reproduces; the residual on tail percentiles is numpy's
linear interpolation vs `percentile_cont`.

Single-number lineage:

```sql
SELECT * FROM provenance.recompute_p99('g1:burst6_lang_fc_chronos_L120','ttft');
```

```
             run_id             | metric  |  q   |  n   |       value       |      stored       | source_table
--------------------------------+---------+------+------+-------------------+-------------------+--------------
 g1:burst6_lang_fc_chronos_L120 | ttft_ms | 0.99 | 9821 | 657.0185941997916 | 657.0261359997094 | llm_request
```

`recompute_quantile(run_id, metric, q)` generalises it. Known metrics: `ttft_ms`, `e2e_latency_ms`,
`itl_ms`, `ttst_ms`, `vllm_itl`. An unknown metric raises rather than returning NULL.

### 4.6 NEVER RECOMPUTE A PERCENTAGE FROM AN ALREADY-ROUNDED PUBLISHED VALUE

This produced **six independent wrong "corrections"** during the thesis audit
(`audit/ADJUDICATION.md §0.4.1`), several of them re-proposed across separate review passes. The
failure is always the same shape: someone reads two rounded cells off a table, divides them, and gets a
different last digit from the true ratio.

The store holds full precision. Use it.

```sql
SELECT run_id, round(p99_ttft_ms::numeric,6) AS p99_ttft_ms,
       round(p99_tpot_ms::numeric,6) AS p99_tpot_ms,
       round(p99_itl_ms::numeric,6)  AS p99_itl_ms
  FROM provenance.llm_run_summary
 WHERE run_id IN ('live:twin_re','a11:burst3_reactive_L120');
```

```
          run_id          | p99_ttft_ms | p99_tpot_ms | p99_itl_ms
--------------------------+-------------+-------------+------------
 a11:burst3_reactive_L120 | 3494.725887 |  152.732781 | 162.116962
 live:twin_re             | 3494.725887 |  152.681078 | 160.259633
```

Worked instance. Live TTFT p99 = 3531.4532, offline twin = **3494.725887**.
- Correct: (3531.4532 − 3494.725887)/3494.725887 = **1.05094% → 1.1%** ✔
- From the printed cells 3,531 / 3,495: 1.03% → "1.0%" ✘ — proposed and rejected three times.

Second instance: ITL p99 live 11.469605 vs offline `p99_tpot_ms` 9.718328 → 1.751277/9.718328 =
**18.020% → 18.0%** ✔. From pre-rounded 1.8/9.7 → 18.6% ✘.

Three corollaries:

1. **Round once, at the end.** Never chain a rounded intermediate.
2. **Check you are on the same metric.** `p99_itl_ms` (5.29/160.26) and `p99_tpot_ms` (9.72/152.68) are
   *different definitions* of "ITL p99" and both exist in the same row. The thesis' `tab:val-anchor`
   defines it as `(RequestLatency − TTFT)/(OSL − 1)` = aiperf TPOT = **`p99_tpot_ms`**.
3. **A 2-dp tie is not a bug to fix.** The 0.96× headline evaluates to 0.96501675 / 0.96502895 /
   0.96501512 under three legitimate denominators — the spread *between defensible denominators*
   (3e-5) exceeds the distance from the 0.965 tie point (1.5e-5). The value is not resolvable to two
   decimals; "correcting" 0.96 to 0.97 makes a consistent thesis inconsistent.

---

## 5. PROVENANCE + FRESHNESS

### `ingest_log` — what was loaded, from where, with what hash

`(file_path PK, sha256, kind, n_rows, run_id, bytes, loaded_at)`. **4,149 rows over 4,149 distinct
files** (1:1), every one of which still exists on disk (verified 2026-07-20: 0 dangling paths).
`sha256` is CHECK-constrained to `^[0-9a-f]{64}$` (`C602` passes).

**Idempotency is by `file_path` + `sha256`.** A re-run skips a file already logged with the same hash;
if the file is edited, its hash changes and it reloads. `run_id` is NULL on 563 rows *by design* —
loaders that write into keyless dimension tables have no spine id to record (§6.5, §6.12). Do **not**
read `ingest_log.run_id` as a spine reference: for six aggregate kinds it is a logical artifact-group
label, which is precisely why `C207` fails and is left failing.

```sql
SELECT kind, count(*) AS files, sum(n_rows) AS rows
  FROM provenance.ingest_log GROUP BY 1 ORDER BY 1;
```

Kind codes, live counts 2026-07-20 (abridged — 35 kinds total, top 20 by rows):

| Kind | Files | Rows | What |
|---|---|---|---|
| `K6` | 436 | 41,106,599 | composed request trace |
| `K10` | 41 | 22,003,500 | forecast series (now complete — §6.10) |
| `K2` | 178 | 18,869,922 | per-request language raw (`llm_request`) |
| `K5` | 254 | 10,342,685 | encoder series (per-second occupancy) |
| `K23` | 26 | 3,630,354 | measured vLLM ETL |
| `K29` | 5 | 2,755,200 | trace arrival-rate series (`eda_rate_series`, no `run_id`) |
| `K4` | 514 | 235,827 | worker schedule (C(t)) |
| `K10m` | 3 | 44,800 | forecast metrics |
| `K50` | 9 | 8,715 | live arm |
| `K11` | 1 | 7,817 | measured per-request |
| `K31` | 23 | 5,469 | group C |
| `K21` | 38 | 1,671 | collector silicon |
| `K22` | 15 | 1,525 | trace EDA |
| `K7` | 22 | 1,172 | factorial cells |
| `K3` | 1,117 | 1,117 | encoder run summary |
| `K42` | 5 | 747 | sweep manifests |
| `K1` | 611 | 611 | language run summary (`llm_run_summary`) |
| `K26` | 6 | 426 | cost model |
| `K12` | 4 | 392 | collector |
| `K8b` | 13 | 368 | verification |

`K20` (grid, 257 files) and `K25`/`K27`/`K28`/`K29` write aggregate artifacts and are the population
behind `C207` — see §6.5. `K35` is **legacy and no longer registered** in `main.py`.

### `is_current` — read §4.3 first

`is_current = false` on **686 of 3,147** runs (it was 2 when this guide was first written). It means
**"not known to be retracted"**. Use `v_retractions` for the retraction set, `grid_correction` +
`grid_window.is_superseded` for row-level corrections, and `artifact_quarantine` for quarantined
artifacts. Only 4 runs carry an explicit `supersedes`/`superseded_by` pointer, so the flag is far more
informative than the pointer graph.

### Is the store current? — a four-query preflight

```sql
-- 1. anything failing?  NOTE: check_failures() returns (check_id,title,severity,detail)
--    -- there is NO `passed` column (every row IS a failure). And see the cost trap below.
SELECT check_id, severity, left(detail,80) FROM provenance.check_failures('expensive');
-- 2. is the drift matview stale?
SELECT * FROM provenance.v_mv_freshness_all;
SELECT * FROM provenance.v_llm_p99_check_freshness;
-- 3. did any join regress?
SELECT * FROM provenance.v_orphan_audit;
-- 4. did a load destroy an earlier load?
SELECT * FROM provenance.v_id_collision;
```

> **TRAP — `check_failures('cheap')` hides the only error-severity failure.** `cheap` runs 57 of the
> 70 registered probes and skips all 13 `moderate`/`expensive` ones — which is exactly where the
> projection-vs-raw identities `C001`–`C008` live. `C002` is `moderate` **and currently failing at
> `error` severity**, so the `cheap` suite reports four `warn` failures and looks clean. Always
> preflight with `check_failures('expensive')`. `'expensive'` is a *ceiling*, not a selector: it runs
> everything enabled, ~43 s.

Live results of (2) and (3), 2026-07-20:

```
      matview       | materialized_rows | live_rows      matview_runs | live_joinable_runs | summary_runs | raw_runs | is_fresh
--------------------+-------------------+-----------    -------------+--------------------+--------------+----------+---------
 mv_llm_p99_check   |               178 |       178              178 |                178 |          610 |      178 | t
 mv_llm_percentiles |               178 |       178
 mv_worker_seconds  |               234 |       234     all five matviews fresh (incl. mv_check_results since D92); v_mv_stale is empty
 mv_infraction      |              2337 |      2337
```

```
       tbl       | orphan_rows
-----------------+-------------
 worker_schedule |           0     <- repaired; baseline was 118,861
 verification    |         314     <- EXPECTED: this counts the bare run_id column, not the join key.
                                      Join verification.resolved_run_id (or the view) -- 371 of 380
                                      resolve, 9 deliberately do not. See C214 and §6.2.
 ingest_log      |         306     <- C207; characterised in §6.5, not a failed load
```

`worker_schedule` orphans are **0** of 235,827 (118,861 at the 2026-07-19 audit). A full sweep of
**every** `run_id`-bearing table (2026-07-20) finds orphans in these two tables and nowhere else —
every fact, summary and cell table is clean. Any increase means a new load regressed.

### Running `check_all()`

```sql
-- the whole enabled suite (69 probes, ~43 s) -- this is what to run
SELECT check_id, severity, passed, left(detail,90) AS detail
  FROM provenance.check_all(NULL,NULL,NULL);
-- only failures, any cost
SELECT * FROM provenance.check_failures('expensive');
-- one block, e.g. all vocabulary checks
SELECT * FROM provenance.check_all(NULL,'cheap','C5');
```

Signature: `check_all(p_severity, p_max_cost, p_prefix)`, all three nullable. `p_max_cost ∈ {cheap,
moderate, expensive}` is a **ceiling**: `expensive` runs everything, `cheap` runs only the 57 cheap
probes. A probe that raises is reported `passed=false` with the SQLERRM in `detail`; it is **never
silently skipped**, so a malformed probe cannot look green.

**Full-matrix result, 2026-07-20 (certification run): 70 defined, 69 enabled, 64 pass, 5 fail.**

```
 check_id | severity | passed |                       detail
----------+----------+--------+------------------------------------------------------------
 C002     | error    | f      | 1 of 178 backed runs exceed 1e-3 relative on median_ttft_ms
 C107     | warn     | f      | 1 of 7 soft reconciliation checks failing: .../client_gen_tokens_eq_gen mismatch=24
 C207     | warn     | f      | 306 of 4149 ingest_log rows reference a run_id absent from runs
 C214     | warn     | f      | 9 of 380 verification rows have no resolved_run_id
 C302     | warn     | f      | 2 runs whose run_id prefix <> experiment (measured:vllm_*, experiment=eda)
```

**One `error`-severity probe fails: `C002`.** It is a percentile-interpolation artefact on a single
run, documented in §6.3 and in `check_definition.note`, and its 1e-3 tolerance was deliberately NOT
loosened. The other four are `warn`. Every one of the five carries a `note` explaining why it is
left failing rather than exempted — **read the note before "fixing" any of them**; each was
adjudicated and the fix rejected on the grounds that it would narrow the population.

`C007` is the one **disabled** probe (`is_enabled = false`) — an exhaustive superset of `C006` over
all ten quantile candidates. It is disabled for cost only, not to hide a failure: re-run on
2026-07-20 it returns `0 of 19,200 cells disagree` in 15.4 s. Run it whenever you want the
exhaustive proof:

```sql
-- there is no "run one check by id" helper (check_run(p_run_id) audits a RUN, not a check).
-- Enable it, then run the suite filtered to its prefix:
UPDATE provenance.check_definition SET is_enabled = true WHERE check_id = 'C007';
SELECT * FROM provenance.check_all(NULL, 'expensive', 'C007');
UPDATE provenance.check_definition SET is_enabled = false WHERE check_id = 'C007';  -- restore
```

### Refreshing `mv_llm_p99_check`

```sql
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;
```

**Run this after every K1 or K2 ingest** (`main.py --only K1` / `--only K2`). Until you do,
`v_llm_drift` — a correctness guard — audits an old snapshot and can report "no drift" for runs it has
never seen. Verify with `v_llm_p99_check_freshness` / `v_mv_freshness`; both must show `is_fresh = t`.

---

## 6. KNOWN LIMITATIONS

Read this before making any coverage claim. **Rewritten 2026-07-20 at the settled, read-only state**
(data generation complete, partition migration applied, certification sweep done). The previous
version of this section described the 2026-07-19 pre-repair store and was substantially obsolete;
items 6.1, 6.4, 6.6, 6.7, 6.9 and 6.10 below record what was *resolved*, because a reader who
remembers the old text needs to know it no longer applies.

### 6.1 RESOLVED — the a16/g2/g3_32b/g6 families are ingested and registered

The old text said these were "still being written, DO NOT INGEST, zero run_ids, collapsed onto
`misc:*`". That is no longer true. Generation is finished and every family is registered:

```sql
SELECT experiment, count(*) AS runs FROM provenance.runs
 WHERE experiment IN ('a16','a16_ft','g1','g2','g3_32b','g4','g6') GROUP BY 1 ORDER BY 1;
```

```
 experiment | runs
------------+------
 a16        |   51
 a16_ft     |   48
 g1         |   42
 g2         |   32
 g3_32b     |  232
 g4         |  165
 g6         |  456
```

`experiment = 'misc'` is now **0 runs** and there are **no** `misc:iter*` / `misc:enc` / `misc:e2e` /
`misc:composed` rows. The `run_id` collision class that caused the original data loss is closed:
`C301` (run_id injective over source files) passes, and `runid.py` now scopes per-run subdirectories.
The 37 rows still listed by `v_id_collision` are all benign multi-directory *artifact groups*
(`grid:grid_summary` 256 files, `measured:vllm_h100_trace` 26, the `sweeps:*` report/log pairs) which
key on their own PKs, not on `run_id`.

### 6.2 `verification` — join `resolved_run_id`, and 9 rows resolve to nothing

**Always join `resolved_run_id`, never the bare `verification.run_id`.** The bare column holds the
unprefixed simulator id and is orphan for 314 of 380 rows *by design* (`C206`, info).

Repaired 2026-07-20: 66 rows whose `run_id` was already namespaced and matched `runs.run_id`
verbatim had been left `resolved_run_id = NULL` by the original resolver, which only rewrote *bare*
ids. They are now filled — every fill recorded in `verification_resolution_backfill`. `v_verification_resolved`
was **also** rewritten: it had been recomputing its own pointer via
`split_part(runs.run_id,':',2) = verification.run_id`, which can never match an already-namespaced
id, so it reported those 66 as unresolvable even after the column was correct. It now prefers the
stored column and exposes `resolution_source ∈ {stored, unique_suffix, unresolved}`.

**371 of 380 now resolve.** The remaining **9 are permanently unresolvable and must stay NULL**
(`C214`, warn, deliberately left failing rather than exempted):

- 3 structural markers with no measurements: `a16:cells`, `g1:_preflight`, `_preflight`.
- 6 model-level **aggregate** rows — `chronos`/`timesfm`/`toto` × a14/a15 — which carry real numbers
  (`completed`, `enc_p99`, `ttft_p99`, `itl_p99`, `gpu_h`) but summarise a whole forecast family over
  the full trace. They have no single backing run *by construction*; inventing a pointer would be a
  fabricated join.

Note `n_candidates = 0` for 75 rows: that column reports the **old suffix heuristic** and is kept only
for backward compatibility. Read `resolution_source`, not `n_candidates`.

### 6.3 432 of 610 language summaries are not recomputable — and C002

See §4.5. `v_llm_summary_backing`: 178 summaries have raw backing (18,869,922 requests), **432 do not**
(11,536,096 requests behind percentiles that cannot be audited against evidence). This got larger in
absolute terms as more families landed; it is inherent — the raw request log was not archived for
those runs — and is **not** a defect that can be repaired from within the store.

Of the 178 that *are* backed, one fails `C002` (`error`): `a16_ft:runs:e12_ft:e2e`, stored
`median_ttft_ms` 27.938447 vs `percentile_cont` 27.886508 — 0.18 % relative, over 5,114 rows. Cause is
percentile-interpolation convention (numpy linear vs `percentile_cont`) in a dense low-latency
cluster, not drift. **The 1e-3 tolerance was deliberately not loosened**; re-verified 2026-07-20 the
deviation is a fixed property of the archived summary. Worst `p99` drift across all backed runs is
1.24 % (`v_llm_drift`).

### 6.4 RESOLVED — the matviews are fresh

The old text reported `mv_llm_p99_check` at 101 materialized vs 125 live. All FIVE matviews
(incl. `mv_check_results` since D92) are now fresh and `v_mv_stale` is empty.
Do not rely on point-in-time counts here: the row-count invariant is
`SELECT count(*) FROM provenance.v_mv_stale` = 0, which catches cardinality
drift only; same-cardinality verdict/evidence drift in the check cache is
caught by the SEPARATE full-content gate in `verify_all.sh` A3, which
compares every `mv_check_results` field except `evaluated_at` against a
live `check_all()` evaluation in both directions. The delivery gate
enforces both invariants on every run. The
refresh discipline in §5 still applies
after any future K1/K2 ingest.

### 6.5 306 `ingest_log` rows have no spine row — now characterised, and NOT a failed load

`C207`, `warn`. The previous diagnosis ("files whose load created no spine row, self-perpetuating")
**was wrong** and is corrected here. Re-derived 2026-07-20, the 306 rows span only 21 distinct labels
and are two disjoint things, neither a failed load:

1. **301 rows / 6 kinds that are 100 % orphan by definition** — K20 grid 257/257, K25 sweeps 31/31,
   K26 costmodel 6/6, K27 ewma_cal 1/1, K28 rerun_b1 1/1, K29 eda_rates 5/5. These loaders write
   **aggregate/derived** artifacts into dimension tables, so their `ingest_log.run_id` is a logical
   *artifact-group label*, not a spine reference. Proof: the single label `grid:grid_summary` is shared
   by 256 files, which cannot be a run identity (`C301` asserts run_id → source_path is 1:1); and
   `eda_rate_series`, the destination of the K29 rows, **has no `run_id` column at all**. 563
   `ingest_log` rows already carry NULL `run_id` for exactly this reason.
2. **5 rows of legacy kind K35** (no longer registered in `main.py`) — replay `*.log` files labelled
   from the log's own stem instead of the run they describe (`srcbuild:run_aic` vs the actual spine run
   `srcbuild:llm_head2k_aic_src`). This *is* a real labelling defect, but no measurement is missing:
   both spine runs exist.

The check is left failing rather than taught to exempt kinds, because exempting would narrow the
population and would also hide (2). **Do not "fix" this by deleting `ingest_log` rows** — the old
text's advice to do so predates this diagnosis and would destroy load provenance.

### 6.6 RESOLVED — no rows remain in any default partition

The old text reported `composed_request_default` at 15.2 M rows (44 % of the table) and 369 `misc`
runs. The partition migration (`schema/27_partition_migration.sql`, applied 2026-07-20) created the
missing `a16`/`a16_ft`/`g2`/`g4` partitions and moved every row by `DELETE ... RETURNING` into the
parent so the partition key did the routing. **All three default partitions are now 0 rows**
(`C601`, `C306`, `C603` all pass), and row-count conservation was gated inside the transaction against
the durable snapshot `partition_migration_baseline` — re-provable at any time:

```sql
SELECT tbl, sum(n) FROM provenance.partition_migration_baseline GROUP BY 1;
-- composed_request 41,106,599 | llm_request 18,869,922 | encoder_series 10,342,685
-- ... identical to the live counts today: delta 0 on all three.
```

### 6.7 RESOLVED — `window_name` is closed over the `windows` dimension

`C209` passes: **0** runs carry a `window_name` absent from `windows`. `week` and `steady` were
normalised in the base tables, and `head2k` was registered in `windows()` (so `sweep_*` cost ratios
are now computable). `v_window_alias` is retained as a defensive no-op and still documents which names
are aliases and which — `head2k`, `fulltrace` — are **genuinely distinct and must not be folded**.

### 6.8 The retraction machinery is partially live, and there are two of them

Improved but still a trap. `runs`: 3,147 total, 2,461 `is_current`, so 686 rows *are* retracted — the
`current_*` views are no longer pass-throughs. But only 4 rows carry `supersedes`/`superseded_by`, and
**two supersession mechanisms coexist**: the spine flags, and `grid_window.is_superseded` +
`grid_correction` (15 rows) + `metric_supersession` (12 rows) + the `*_effective` views. See §4.3 —
always read the `*_effective` view for grid quantities rather than the base table.

### 6.9 RESOLVED — all three EWMA calibration variants are present and identifiable

The old text said two of three variants were destroyed and the survivor unidentifiable because
`forecast` had no identity column. `forecast` now carries **`source_tag`** (the source parquet path),
non-NULL on all 22,003,500 rows, and all three arms are present at 38,388 rows each:

```
 /home/gio/tese/predictors/results/ewma_cal_add_images.parquet   | 38388
 /home/gio/tese/predictors/results/ewma_cal_mult_images.parquet  | 38388
 /home/gio/tese/predictors/results/ewma_cal_wsc_images.parquet   | 38388
```

`C010` confirms they are point-identical and differ only in `p90` (0 point disagreements, 0 ties).
Claims resting on the EWMA calibration ablation are verifiable again — **filter on `source_tag`**, not
on `mode IS NULL`.

### 6.10 RESOLVED — `forecast` is fully ingested

The old text reported ~16.7 M rows loaded against ~21.6–22.0 M on disk, with the covariate-mode
partitions missing. `forecast` now holds **22,003,500** rows (`cov` 5,269,200 / `uni` 16,135,440 /
NULL-mode 598,860), and `C009` verifies the covariate archive **partition by partition** against
on-disk counts: 0 of 10 disagree, 5,269,200 of 5,269,200 expected. Row-count questions can now be
answered from the DB.

### 6.11 Six `rerun_verify:react_p90_*` runs carry a worker schedule from a different simulation

**PERMANENTLY UNRECOVERABLE.** (These were `misc:react_p90_*` before the family was registered; the
prefix changed, the defect did not.) 9,177 `worker_schedule` rows across six runs
(`rerun_verify:react_p90_W{120,240,480}_burst1_L{30,300}`) hold the *aggregate* run's schedule: the
file is byte-identical by sha256 to `react_p90_W<W>_aggregate_L<L>.sched.json` and its sibling log
self-labels "aggregate". Schedule span 483,660 s vs the run's own `sim_horizon_s` 29,939.313 s —
16.15×. The true burst1 schedules were never generated and are not on disk; only re-running the
simulation can fix this.

Flagged in `worker_schedule.invalid_reason` (reason `C-02`) and excluded by
`v_worker_schedule_integrity.unexplained_mismatch`. **The stored `provisioned_worker_seconds` for
these runs is CORRECT** — it comes from `*.jsonl.stats.json`, not from the schedule. `check_run()` and
`C005` respect `is_valid IS NOT FALSE`, so the worker-seconds integral is safe; a hand-written
`SUM(worker_count*dt)` over `worker_schedule` is **not**.

### 6.12 Most projection tables carry no `run_id`

Nine of the thirteen original projection tables have no `run_id`; six have no spine key of any kind
(`eda_rate_series` is the canonical example — it is keyed by script/metric path). The "every summary
is recomputable from raw" guarantee is therefore structurally false for the majority of projections.
`C208` verifies only those that *do* have a key (`llm_run_summary`, `encoder_run_summary`,
`factorial_cell` — all 0 orphans). This is also the root cause of half of §6.5: a loader writing into
a keyless dimension table has nothing meaningful to put in `ingest_log.run_id`.

### 6.13 File coverage — 27.1 % of result-like files on disk are not ingested

Census 2026-07-20 over `simulation/results`, `defense/anim/data`, `collector_artifacts`,
`vllm_trace_analysis`, `predictors/results{,_dynamo}`, `analysis/trace_eda`, `verification/results`,
counting `.json/.jsonl/.csv/.parquet/.log` and excluding worktrees/parts/venv:

```
 disk result-like files : 5,673
 ingest_log distinct    : 4,149   (every one still exists on disk -- 0 dangling)
 on disk, not ingested  : 1,536   (27.1%)
```

That headline number is **not** 1,497 missing measurements. It decomposes as:

- **~1,202 secondary artifacts of runs that ARE in the store** — `.log` consoles, `points/*.json` and
  `logs/*.log` siblings under a family whose `reports/*.report.json` is ingested (all 232 g3_32b runs
  are loaded from `reports/`; its `points/` + `logs/` account for 465 of the "missing"), `sched_*.json`,
  `.conv.log`, `.ledger.json`.
- **295 with no representation at all**, of which the substantive ones are: `g4_folds` ledger/conv
  artifacts (115), `g6_runs` schedules (50), `a16_ft`/`a16` (36), and the
  `vllm_trace_analysis/model/*` files — which are **trained model weights and scalers, not
  measurements**, and correctly not modelled as runs.

Coverage by area (re-censused 2026-07-20): `simulation/results` 96.9 %, `predictors/results_dynamo`
and `verification/results` 100 %, `analysis/trace_eda` 95.2 %, `predictors/results` 88.7 %,
`defense/anim/data` 62.4 %, `vllm_trace_analysis` 57.4 %, `collector_artifacts` 35.5 %. The
`collector_artifacts` figure fell from 54.9 % because 39 more secondary artifacts landed on disk
(30 `phase9_two_pool/*.csv`, 15 `phaseE_physical_anchor/*.log`, 12 `phaseE .json`) — none of them a
lost measurement; the ingested collector count is unchanged.

**One clean flagged gap:** `simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` have never
been ingested — zero `ingest_log` rows, zero spine runs, experiment `m235b` absent from `runs`. Only
their `.log` siblings were ever read. `runid.py` maps `/235b/` to experiment `m235b`, so the family is
declared but unloaded. Closing it needs a loader for that report shape. Nothing in the store is wrong;
something is simply absent.

### 6.14 Three loader passes are not file-gated, so `main.py` never reports 0/0

Idempotency re-verified 2026-07-20 (final certification): re-running `main.py` end to end changes
**nothing** — `ingest_log` 4,149, `runs` 3,147, and `composed_request`/`llm_request`/`encoder_series`/
`forecast` counts all identical, with a `md5(string_agg(...))` content digest over `ingest_log` (path,
sha, n_rows, run_id), the annotated `runs` columns, and the six raw/summary tables **byte-identical
across three consecutive passes**. `verify_all.sh`'s idempotency gate now judges by that digest, not by
the stdout counter, so it passes truthfully (the stdout `files>0` proxy this section warns against was
retired in favour of the digest it always said to use).

But three passes still *print* nonzero counters, and that is expected, not a regression:

| Pass | Reports each run | Why |
|---|---|---|
| `K40` srcbuild | `files=2 rows=2` | Deliberately **not** `ingest_log`-gated: those two files are already claimed by K26, and `ingest_log` is keyed by `file_path` with one owning `kind`. Idempotent by construction — every write is an upsert of deterministically-read values. |
| `K34` config_backfill | `files=944 rows=2,204` | POST annotation pass; re-reads logs and `COALESCE`s into existing rows. (Was 943/2,108; grew as post-manuscript defence artifacts landed on disk — inspected, not changed.) |
| `K41` runtime_build | `files=1219 rows=618` | POST annotation pass; same COALESCE discipline. |

`K13` ledger reports `files=1 rows=<n>` **once** after `progress/results-ledger.md` is edited (its
sha256 changed, so it legitimately reloads); it settles to 0 on the next run, and `ledger_entry` is
*replaced*, not appended to — its row count tracks the number of entries in the file (88 as of
2026-07-20). **Judge idempotency by row counts and content hashes, not by these counters.**

### 6.15 Whole result families are not in the DB at all

`audit/ADJUDICATION.md §5` catalogues **125 thesis claims that remain unverifiable from this store**:
architecture/analytic facts (~35), collector/profiler artifacts not modelled here (~45), software and
hardware versions (~15), external citations (~15), derived analyses with no provenance column (~15).
Per-tick planner decisions live in archived logs under `simulation/results/live51/live_runs/`, not in
any table. **The absence of a number from this store is not evidence against it.**

---

## Appendix — relation quick index

**Start here:** `v_dim` · `v_pool_latency` · `v_pool_cost` · `v_cost_ratio` · `v_infraction` ·
`v_joint_e2e` · `v_sla_bound` · `grid_window_effective`

**Trust / audit:** `check_all()` · `check_failures()` · `check_run()` · `recompute_p99()` ·
`recompute_quantile()` · `v_orphan_audit` · `v_id_collision` · `v_mv_freshness` ·
`v_mv_freshness_all` · `v_mv_stale` · `v_llm_p99_check_freshness` · `v_llm_summary_backing` ·
`v_llm_raw_backing` · `v_llm_drift` · `v_run_status` · `v_retractions` · `v_verification_resolved` ·
`v_corroboration` · `v_ingest_orphan` · `v_worker_schedule_integrity` · `v_window_alias` ·
`v_dim_synonym` · `v_config_coverage` · `grid_correction` · `metric_supersession` ·
`artifact_quarantine`

**Audit records — provenance of corrections, not measurements:**
`partition_migration_baseline` (pre-migration per-family row counts; conservation stays re-provable) ·
`verification_resolution_backfill` (the 66 `resolved_run_id` fills, 2026-07-20) ·
`runs_config_backfill` (12 NULL→value config fills, guarded by `C405`) · `ingest_correction`

**Domain:** `forecast_metrics` / `v_forecast_best` (accuracy) · `collector_*` (silicon) ·
`eda_*` (trace) · `vllm_*` / `measured_request` (measured) · `coverage` / `v_coverage` ·
`grid_*` / `v_grid_*` (static grid) · `factorial_cell` / `sweep_*` / `ewma_ablation_cell` (sweeps)

**Raw facts (partitioned by `experiment`):** `llm_request` · `composed_request` · `encoder_series` ·
`forecast` · `worker_schedule`

### Experiment families — what each partition is

Registered families as of 2026-07-20. The `a1x`/`gx` families are the ones added since the guide was
first written; all are fully ingested and partitioned (no `misc` remains).

| Family | Runs | What it is |
|---|---|---|
| `factorial` | 1284 | the main factorial sweep (window × model × L × ρ × quantile × readiness) |
| `g6` | 456 | escalation / fc-aware mixed-policy defence runs (`sched_*`, `*mix*`) |
| `g3_32b` | 232 | served-model sweep at 32B/30BA3B/235B across TP — the served-LLM family |
| `g4` | 165 | fold / cross-validation runs (`F*`, `FULL`) |
| `grid` | 142 | the static-optimal capacity grid (C* per window) |
| `a2x`, `a2`, `a2t`, `a2tf` | 100/40/36/36 | encoder-pool arrival + threshold variants |
| `a11`, `a12`, `a13`, `a14`, `a15` | 52/21/5/9/9 | per-burst and full-week forecast/reactive fleets |
| `a16`, `a16_ft` | 51/48 | controller-cost / fine-tuning sweeps (per-run subdirectories, `scoped=True`) |
| `rerun_verify` | 47 | stability re-runs — **includes the 6 defective schedules of §6.11** |
| `g1` | 42 | per-burst encoder+language arm matrix |
| `predictors` | 41 | predictor/EWMA ablation |
| `sweeps` | 33 | batch-size / concurrency sweeps (`head2k`, `burst1`) |
| `g2` | 32 | closed-loop repeat runs |
| `reactive` | 32 | reactive-policy baselines |
| `ctmatrix`, `riders` | 20/20 | cost-time matrix; rider/ladder detection |
| `aggregate44{,_rho,_strict}` | 18/17/7 | aggregate-window re-analyses |
| `eda` | 16 | trace characterization **plus the two hand-named `measured:vllm_*` runs** (`C302`) |
| `planner`, `live` | 12/10 | planner tick logs; the live deployment arm |
| `episode`, `a6`, `closedloop_v2`, `srcbuild`, `cap_sensitivity` | 6/5/3/2/2 | episode slices; source-vs-wheel runtime build; capacity sensitivity |

**Reference docs:** `provenance/audit/DB_STRUCTURE_PLAN.md` (structural defects, remediation plan,
pre-ingest checklist) · `provenance/audit/ADJUDICATION.md` (claim-by-claim verification ledger; §0.4 is
the list of 44 **rejected** "corrections" and is the single most useful section for an agent tempted to
propose a fix) · `provenance/schema/20_semantic.sql` (semantic layer, heavily commented) ·
`provenance/schema/21_checks.sql` (the check suite).
