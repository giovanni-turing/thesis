# THE STRUCTURE REMEDIATION PLAN — schema `provenance`

Basis: five read-only audit lenses (A referential integrity, B naming/typing/units, C cross-table
semantic identities, D schema hygiene, E). All numbers below were re-verified live against
`postgres@localhost:5433` on 2026-07-19. Nothing was modified while producing this plan.

Standing constraint: **a16 / g2 / g3_32b / g6 are still being written to disk and not yet ingested.**
Nothing in §3 imposes a measurable cost on that bulk load. Everything with a scan, rewrite or lock
cost is in §4 and is explicitly marked DO NOT RUN.

---

## 1. VERDICT

**The store is arithmetically sound and structurally broken at the joins.**

Those are separate statements and both are true.

### What is correct

The numbers are trustworthy where they can be recomputed. Lens C tested twelve independent
projection-vs-raw identities and eight reproduce **exactly**:

- `llm_run_summary.completed_requests` = `count(*) llm_request` for 101/101 runs that have raw rows;
  `median_ttft_ms` reproduces `percentile_cont(0.5)` for 101/101.
- `encoder_run_summary.provisioned_worker_seconds` = `SUM(worker_count·dt)` over `worker_schedule`
  (last step extended to `sim_horizon_s`) for 328/334 runs, median relative error 0.000000.
- `encoder_run_summary.requests` = `count(*) composed_request` — 366/366 exact.
- `forecast_metrics` WAPE/MAE/RMSE reproduce from raw `forecast` to 6 dp for all 6 models × {point,p50,p90} × h ∈ {1,4,12}.
- `coverage` / `coverage_meta` fully corroborated (749601 + 250399 = 1000000, exact).
- `cost_accounting.total_from_order_ws = provisioned_ws + warmup_ws` — 40/40 exact.
- `ewma_ablation_cell.ratio_vs_static` — 48/48 to storage rounding.
- `eda_metric` reproduces from `eda_rate_series` exactly; the vLLM ETL reconciles to the token
  (1,354,025 ITL rows = SUM(gen_tokens)).

Supersession pointers are internally consistent (0 dangling), the grid correction chain is coherent
and machine-readable, partition keys never disagree with `runs.experiment` (0 mismatches), no rows
are misfiled in any `*_default` partition, every table has ≥1 row, all 20 views execute, there are no
duplicate indexes, and every raw partition already carries a `run_id` index.

### What is not correct

Four things, in descending order of severity. None of these are cosmetic.

1. **Data was silently destroyed by the loader and the arithmetic proves it.** `run_id` collisions
   under the `misc` fallback caused delete-then-insert to overwrite prior loads: 29,311 `llm_request`
   rows, 16,939 `composed_request` rows, 1,793 `encoder_series` rows, 76,776 `forecast` rows. The
   per-run shortfalls sum *exactly* to the global shortfalls, so attribution is certain. Two of three
   EWMA calibration variants are gone **and the surviving 38,388 rows cannot be identified** — the
   `forecast` table has no variant, `run_id` or `source_path` column. Any claim resting on
   `forecast WHERE model='ewma' AND mode IS NULL` is currently unverifiable.

2. **`runs` is not the universal join key the design intent claims.** 118,861 of 215,030
   `worker_schedule` rows (55%) reference `run_id`s that do not exist in `runs`; all 320
   `verification` rows are unjoinable (bare, unprefixed ids); 525 of 2,754 `ingest_log` rows point at
   a spine row that was never created; and 9 of the 13 core projection tables carry **no `run_id`
   column at all**, six of them no spine key of any kind. The recomputability guarantee is therefore
   structurally false for the majority of projections.

3. **394 of 495 `llm_run_summary` rows — 9,328,107 requests — have zero backing raw rows**, and all
   394 are flagged `is_current = true`. Their percentiles cannot be audited against evidence.

4. **The retraction machinery is inert.** `is_current` is `true` for all 2,206 rows, `supersedes` and
   `superseded_by` are empty everywhere, so `current_runs` / `current_llm_summary` /
   `current_encoder_summary` are pass-through views that filter nothing while *reading* as the clean
   set. Actual retraction is being expressed through two ad-hoc channels instead (`grid_window.is_superseded`
   plus the `grid_correction` prose table, and silent overwrite). `mv_llm_p99_check` is stale
   (80 rows vs 101 live), so `v_llm_drift` — a correctness guard — silently checks only 79% of runs.

Naming and unit drift (lens B, 18 findings) is real but secondary: it misleads readers rather than
corrupting data. The one genuinely dangerous case is `verification`, whose four latency columns
(`enc_p99`, `enc_max`, `ttft_p99`, `itl_p99`) carry no unit in the name and **zero column comments** —
and `verification` is precisely the table an analyst opens to confirm a thesis number.

### Bottom line

The store is fit to publish from **for the 101 fully-backed language runs, the grid family, the
forecast-metrics family and the vLLM ETL**. It is not fit to publish from for the EWMA calibration
ablation, for anything integrating `worker_schedule` on the six `misc:react_p90_*` runs, or for any
number sourced from the 394 unbacked summaries — until §2 is worked through. The single urgent item
before the next ingest is **DEF-3**: a16 will collide on `runs_pkey` the moment a second config
directory is loaded.

---

## 2. CRITICAL / HIGH DEFECTS

Deduplicated across lenses. Lens ids in brackets.

---

### DEF-1 — `worker_schedule`: 55% of rows unjoinable to the spine [A-01, D1]

**Severity: CRITICAL.** 118,861 of 215,030 rows across 112 `run_id`s.

The 112 ids use a *compact* encoding (`factorial:react_rho10_L30`,
`factorial:forecast_p50_chronos_rho10_L15`) while `runs` uses the long form
(`factorial:issue-time:burst3:toto:L45:None:res15s:rho10:cs45:hy3:forecast:p90`). They are **not**
recoverable by prefix-stripping (0 of 112 match), and the compact form **omits the window**, so one
compact id maps to several `runs` rows — the mapping is genuinely ambiguous and cannot be repaired in SQL.

The FK asymmetry is the diagnostic: `worker_schedule` has no FK so its rows persisted;
`llm_run_summary` *does* have an FK to `runs`, so the 112 corresponding K3 `.stats.json` summaries
were **silently rejected** and `llm_run_summary` holds 0 rows for these ids.

```sql
SELECT count(*) total, count(DISTINCT run_id) d_runs,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)) matched
FROM provenance.worker_schedule x;
-- verified: total=215030 | d_runs=460 | matched=96169   => 118,861 orphaned

SELECT count(DISTINCT x.run_id) FILTER (WHERE EXISTS (
         SELECT 1 FROM provenance.runs r WHERE r.run_id=split_part(x.run_id,':',2))) AS match_stripped,
       count(DISTINCT x.run_id) AS orphan_ids
FROM provenance.worker_schedule x
WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id);
-- verified: match_stripped=0 | orphan_ids=112
```

**Impact.** An `INNER JOIN worker_schedule → runs` silently loses over half the table and returns a
*biased* subset — the surviving 348 ids are a different experiment family from the 112 lost ones. No
error is raised. Every provisioned-cost integral computed over the joined set is computed over the
wrong population.

**Remediation.** No DDL fix exists; the mapping must be re-minted by the loader. Required steps:
(a) reconcile `loader/runid.py`'s worker-schedule id policy with `load_factorial`'s; (b) if the
compact id is genuinely window-agnostic then `worker_schedule` is at a *coarser grain* than `runs`
and needs a bridge table, not an FK; (c) backfill the 112 `runs` rows from the K3/K4 `ingest_log`
paths, then re-ingest the 112 K3 files so `llm_run_summary` populates.

Safe-now mitigation (§3, item 3.5): a warning `COMMENT` on the column plus a standing orphan-audit view.

---

### DEF-2 — `verification.run_id` is 100% orphaned [A-02, D2]

**Severity: CRITICAL** (by consequence, not by volume). All 320 rows.

```sql
SELECT count(*) total,
       count(*) FILTER (WHERE run_id LIKE '%:%') prefixed,
       count(*) FILTER (WHERE run_id NOT LIKE '%:%') bare
FROM provenance.verification;
-- verified: total=320 | prefixed=0 | bare=320

SELECT count(*) FROM provenance.verification x
WHERE x.run_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id);
-- verified: 320

-- resolvable by suffix, and the ambiguous ones
SELECT count(*) FROM (
  SELECT x.run_id FROM provenance.verification x
  JOIN provenance.runs r ON r.run_id LIKE '%:'||x.run_id
  GROUP BY 1 HAVING count(*)>1) z;
-- verified: 2 ambiguous  (react_L30 -> {a6:,misc:}; static_C2 -> {a6:,misc:})
```

313 of 320 resolve unambiguously by suffix; 2 are ambiguous; 7 resolve to nothing.

**Impact.** `verification` is the trust table. Any `JOIN runs USING(run_id)` drops verification
status entirely, so a *verified* run reads as **unverified** rather than raising an error. This is a
false-negative on the store's own evidence of correctness.

**Remediation.** Fix the loader (`load_verification`, kind K8b) to mint the namespaced id, then
reload — it is 320 rows, trivially cheap. Do **not** blind-`UPDATE` in place: the PK is
`(source_path, run_id)`, the loader is the source of truth and would reintroduce the bare form on the
next ingest, and 9 ids cannot be resolved mechanically. Gate the reload on this returning 0:

```sql
SELECT x.run_id, count(*) FROM provenance.verification x
JOIN provenance.runs r ON r.run_id LIKE '%:'||x.run_id
GROUP BY 1 HAVING count(*)>1;   -- must be empty before any rewrite
```

Safe-now bridge (§3, item 3.6): `v_verification_resolved`, which resolves the 313 and exposes
`n_candidates` so ambiguity is visible rather than silent.

---

### DEF-3 — a16 `run_id`s drop the sweep config: 47,043 rows already destroyed, next load collides [A-03, A-06, C-03]

**Severity: CRITICAL. This is the only item that is urgent *before* the next ingest.**

`a16` is absent from the loader's dir→experiment map, so runs fall through to the `misc`/`reactive`
default and collapse onto generic ids (`misc:iter0`, `reactive:iter1`, `misc:enc`, `misc:e2e`,
`misc:composed`). The loader clears existing rows for a `run_id` before inserting, so the second
file's load **destroyed** the first's.

```sql
-- genuine collisions: one run_id fed from more than one directory
SELECT run_id,
       count(DISTINCT regexp_replace(file_path,'/[^/]+$','')) ndir,
       array_agg(DISTINCT regexp_replace(file_path,'/[^/]+$','')) dirs, count(*) nfiles
FROM provenance.ingest_log WHERE run_id IS NOT NULL
GROUP BY 1 HAVING count(DISTINCT regexp_replace(file_path,'/[^/]+$','')) > 1;

-- quantify the loss (K2 -> llm_request)
SELECT i.run_id, i.n_rows expected, coalesce(c.n,0) actual, i.n_rows-coalesce(c.n,0) missing
FROM (SELECT run_id, sum(n_rows) n_rows FROM provenance.ingest_log WHERE kind='K2' GROUP BY 1) i
LEFT JOIN (SELECT run_id, count(*) n FROM provenance.llm_request GROUP BY 1) c USING (run_id)
WHERE i.n_rows IS DISTINCT FROM coalesce(c.n,0) ORDER BY 4 DESC;
```

Verified losses, and the arithmetic closes to the row:

| table | per-run shortfalls | total | global shortfall |
|---|---|---|---|
| `llm_request` | 6186+6186+6182+3093+3091+2921+1652 | **29,311** | 15,376,456 − 15,347,145 = 29,311 |
| `composed_request` | 6182+3093+3091+2921+1652 | **16,939** | 34,967,693 − 34,950,754 = 16,939 |
| `encoder_series` | 1793 | **1,793** | 10,184,188 − 10,182,395 = 1,793 |

The worst cases are *scientifically* colliding arms: `misc:composed`/`misc:e2e`/`misc:enc` collide
across `a16_ft/runs/e13_ft` and `a16_ft/runs/e13_zs` — the fine-tuned and zero-shot arms of the same
experiment. **The fine-tuned arm's raw data is gone; only e13_zs survives.** Likewise `misc:iter3`
collides across `burst3_fc_chronos_ondemand_P5000.0` and `burst3_fc_chronos_P5000.0`, and
`misc:arima`/`kalman`/`prophet` collide across `predictor_closedloop_v2/burst4` and `.../steady24h`.

`runs` has `PRIMARY KEY (run_id)` and 9 rows already occupy `misc:iter0..3` / `reactive:iter0..4`
with all comparison dimensions NULL. 48 a16 files are in `ingest_log` against those 9 rows. The very
next a16 config directory containing an `iter0.requests.jsonl` either aborts the load or overwrites a
distinct experiment.

**Remediation (loader, before the a16 bulk load):**
1. Add `a16` (and `a16_ft`) to the dir→experiment map so `experiment='a16'`.
2. Mint `run_id` from the *config directory*, not the iteration stem:
   `a16:burst3_reactive_P5000_q0.3:iter0`.
3. Populate `window_name` / `policy` / `model` / `rho` from the directory name.
4. Add a pre-flight guard that **refuses** to load when a `run_id` would receive files from a second
   directory (see `v_id_collision`, §3 item 3.4).
5. Create the `a16` partitions (§6).
6. Re-ingest all of `defense/anim/data/a16_runs` and `a16_ft` — the destroyed rows only come back
   from disk.

---

### DEF-4 — `forecast`: two of three EWMA calibration variants destroyed, survivor unidentifiable [A-04, A-09]

**Severity: CRITICAL.**

`forecast` is LIST-partitioned by `model` and carries **no `run_id`, no `source_path`, no variant
column**. The three calibration files — `ewma_cal_add_images.parquet`, `ewma_cal_mult_images.parquet`,
`ewma_cal_wsc_images.parquet`, 38,388 rows each — all land on the identical key
`(model='ewma', mode=NULL, variate='images')`.

```sql
SELECT (SELECT sum(n_rows) FROM provenance.ingest_log WHERE kind='K10') expected,
       (SELECT count(*) FROM provenance.forecast) actual;
-- verified: 16,734,300 vs 16,657,524  => missing 76,776

SELECT file_path, n_rows FROM provenance.ingest_log
WHERE file_path LIKE '%ewma_cal_%images.parquet' ORDER BY 1;   -- 3 files x 38,388

SELECT model, mode, variate, count(*) FROM provenance.forecast
WHERE model='ewma' AND mode IS NULL GROUP BY 1,2,3;             -- exactly 38,388 survive

SELECT column_name FROM information_schema.columns
WHERE table_schema='provenance' AND table_name='forecast';      -- no run_id, no source_path, no variant
```

115,164 − 38,388 = 76,776 = the global shortfall exactly.

**Impact.** Worse than the row loss: the surviving arm **cannot be identified**. Any analysis of the
EWMA calibration ablation drawn from `forecast` is reading one unknown arm of three and reporting it
as the answer.

**Remediation.** Schema change + re-ingest, both before the next load (adding a nullable column in
PG16 is a catalog-only operation, no rewrite, no ingest penalty):

```sql
-- DO NOT RUN in the current read-only phase; run immediately before the next bulk ingest
ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS run_id text;
ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS variant text;
COMMENT ON COLUMN provenance.forecast.variant IS
  'Calibration/ablation variant discriminator (cal_add | cal_mult | cal_wsc | NULL). '
  'Added 2026-07 after three ewma_cal_*_images.parquet files collapsed onto one key.';
```
Then re-ingest the three files. Interim: cross-check against `provenance.ewma_cal_coverage` /
`ewma_cal_param`, which are keyed on `(manifest_id, method, split)` and **do** preserve the method
distinction. Treat every current claim on `forecast WHERE model='ewma' AND mode IS NULL` as
unverified until then.

---

### DEF-5 — six `misc:react_p90_*` runs carry a `worker_schedule` from a different simulation [C-02]

**Severity: CRITICAL** (silent 5.5–6.4× cost error, small blast radius).

For 328/334 runs the integral identity holds to 1e-3. Six fail catastrophically: the summary's
metrics blob records 109–173 schedule steps over `sim_horizon_s = 29,939.3 s`, but `worker_schedule`
holds 1,046–2,278 rows spanning `t_s` out to 483,645 s — a ~16× longer horizon. Each has exactly one
distinct `source_path` (a `.sched.json` under `simulation/results/rerun_verify/`), so this is not
double-ingestion: **the `.sched.json` artifact and the `.stats.json` summary describe different runs.**

```sql
WITH e AS (SELECT run_id, provisioned_worker_seconds pws, (metrics->>'sim_horizon_s')::float hz
           FROM provenance.encoder_run_summary WHERE provisioned_worker_seconds IS NOT NULL),
     s AS (SELECT w.run_id, w.t_s, w.worker_count,
                  coalesce(lead(w.t_s) OVER (PARTITION BY w.run_id ORDER BY w.step_index), e.hz) tn
           FROM provenance.worker_schedule w JOIN e ON e.run_id = w.run_id),
     i AS (SELECT run_id, sum(worker_count*greatest(tn-t_s,0)) integ, count(*) n_tbl FROM s GROUP BY 1)
SELECT i.run_id, i.n_tbl, round(i.integ::numeric,1) integ, round(e.pws::numeric,1) pws,
       round((i.integ/e.pws)::numeric,3) ratio
FROM i JOIN e USING (run_id)
WHERE abs(i.integ-e.pws)/nullif(e.pws,0) > 0.01 ORDER BY 5 DESC;
-- verified: 6 rows, ratios 6.441, 6.004, 5.917, 5.635, 5.601, 5.494
--           (react_p90_W{120,240,480}_burst1_L{30,300})
```

**Impact.** Any cost / worker-second / utilization figure obtained by integrating `worker_schedule`
for these six ids is wrong by 5.5–6.4×. The stored `provisioned_worker_seconds` values are
internally consistent with their own metrics blob and can stay.

**Remediation.** Do not integrate `worker_schedule` for these six anywhere. Ship the guard view
`v_worker_schedule_integrity` now (§3 item 3.7). At the final load, re-derive the schedules from the
correct artifact or drop the six `worker_schedule` sets.

---

### DEF-6 — 525 `ingest_log` rows have no spine row, and the gap is self-perpetuating [A-05]

**Severity: HIGH.**

```sql
SELECT kind, count(*) nfiles FROM provenance.ingest_log x
WHERE x.run_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)
GROUP BY 1 ORDER BY 2 DESC;
-- verified total 525: K20=257, K3=112, K4=112, K25=31, K26=6, K29=5, K27=1, K28=1
```

19% of all 2,754 ingested files were recorded as loaded while their spine row does not exist — the
load half-succeeded and nothing flagged it. Because `ingest_log` *is* the idempotency mechanism,
these files will be skipped as "already loaded" on any future re-run.

**Impact.** Permanent, self-healing-proof provenance holes.

**Remediation.** Most of K20/K25/K26/K27/K28/K29 write into path-keyed tables (`grid_*`, `sweep_*`,
`eda_rate_series`, `ewma_cal_*`, `rerun_b1_*`) that do not depend on `runs`, so the *data* is present
and only the spine row is missing — backfill `runs` from `ingest_log.file_path`. K3/K4 is DEF-1 and
needs the naming decision first. Ship `v_ingest_orphan` now (§3 item 3.3) and check it after every load.

---

### DEF-7 — `misc` is a dumping ground and `composed_request_default` is 44% of the largest table [A-06, A-07]

**Severity: HIGH.**

```sql
SELECT regexp_replace(source_path,'/[^/]+$','') dir, count(*) n
FROM provenance.runs WHERE experiment='misc' GROUP BY 1 ORDER BY 2 DESC;
-- verified: 369 runs over 14 directories.
-- g3_32b/reports=215, rerun_verify=47, g6_runs=20, g4_folds=18, aggregate44=18,
-- aggregate44_rho=17, aggregate44_strict=7, g2_runs=6, g2_runs/traces=6, a16_*=7,
-- predictor_closedloop_v2/steady24h=3, cap_sensitivity=2

SELECT 'composed_request' t, experiment, count(*) FROM provenance.composed_request_default GROUP BY 1,2
UNION ALL SELECT 'llm_request', experiment, count(*) FROM provenance.llm_request_default GROUP BY 1,2
UNION ALL SELECT 'encoder_series', experiment, count(*) FROM provenance.encoder_series_default GROUP BY 1,2;
-- verified: composed_request_default misc=15,238,525 (43.6%);
--           llm_request_default misc=94,731; encoder_series_default misc=1,793.
-- Misfiled rows in any default partition: 0 (only 'misc' occurs, and no misc partition exists).
```

`misc` has no named partition on any of the three experiment-partitioned tables, so partition pruning
is defeated for nearly half the largest table — and every future a16/g2/g3_32b/g6 row lands there too,
because all four families currently classify as `misc`. This is the same mechanism that produced the
a2t/a2tf conflation and it is **actively producing new damage right now**.

**Remediation.** Extend the dir→experiment map (§6), create the empty named partitions **before** the
next load (instant, no ingest penalty, actually speeds bulk load), and make `misc` a hard load error
rather than a silent default. Do **not** try to split the existing 15.2M default rows now —
detach/redistribute requires a full scan and rewrite; that is §4.

---

### DEF-8 — 394 of 495 `llm_run_summary` rows have no backing raw rows [C-01]

**Severity: HIGH.**

```sql
SELECT split_part(s.run_id,':',1) fam, count(*) n_no_raw, sum(s.completed_requests) lost_requests,
       count(*) FILTER (WHERE r.is_current) n_current
FROM provenance.llm_run_summary s
LEFT JOIN provenance.runs r USING (run_id)
WHERE NOT EXISTS (SELECT 1 FROM provenance.llm_request l WHERE l.run_id = s.run_id)
GROUP BY 1 ORDER BY 2 DESC;
-- verified: misc 222/707092; grid 93/2368461; riders 20/1100255; sweeps 19/477628;
--           reactive 14/428940; planner 12/4015407; live 7/21651; episode 6/198852; g1 1/9821
--           => 394 rows, 9,328,107 requests, ALL flagged is_current
```

The converse is clean: zero runs have raw rows but no summary.

**Impact.** Any p50/p90/p99 quoted from these 394 runs cannot be audited against evidence — exactly
the property the star schema exists to guarantee. `planner` (4.0M requests) and `grid` (2.4M) are the
two families where the volume most justifies a backfill.

**Remediation.** Ship `v_llm_summary_backing` now (§3 item 3.8) so every claim can be labelled
*recomputable* vs *summary-only*. Then decide per family whether the `.requests.jsonl` files still
exist on disk and should be loaded at the final ingest.

---

### DEF-9 — 9 of 13 projections carry no `run_id`; 6 have no spine key at all [D3, C-10, A-09]

**Severity: HIGH.**

```sql
SELECT c.relname projection_table,
       bool_or(a.attname='run_id') has_run_id,
       bool_or(a.attname='window_name') has_window_name
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
WHERE n.nspname='provenance' AND c.relkind='r'
  AND c.relname IN ('llm_run_summary','encoder_run_summary','factorial_cell','composed_e2e',
                    'cost_accounting','coverage','coverage_meta','verification','forecast_metrics',
                    'quantile_coverage','collector_fn','forecast_eval','ewma_ablation_cell')
GROUP BY 1 ORDER BY 2, 1;
```

Verified: only `llm_run_summary`, `encoder_run_summary`, `factorial_cell`, `verification` carry
`run_id`. **No spine key whatsoever:** `collector_fn`, `coverage`, `coverage_meta`, `forecast_eval`,
`forecast_metrics`, `quantile_coverage`. **`window_name` only** (a coarser grain than a run):
`composed_e2e`, `cost_accounting`, `ewma_ablation_cell`.

`composed_e2e` is the sharpest case. The language side is recoverable by string reconstruction —
joining on `'a12:'||window_name||'_'||arm` reproduces `ttft_p99_ms` and `requests` exactly for all 20
rows. The **encoder side is not**: 19 of 20 rows carry `enc_p99_ms = 588.4`, the SLA-saturated flat
p99 shared by ≥12 different encoder runs, so which run produced each figure is genuinely ambiguous.

**Impact.** A headline number read out of `forecast_metrics` or `coverage` cannot be attributed to a
run, cannot be filtered by `is_current`, and cannot be recomputed. This is also why the retraction
mechanism cannot protect these tables.

**Remediation.** Per table, decide the grain: per-run → add and populate `run_id`; per-window →
document and FK to `windows`; cross-run rollup → needs a run-set manifest table, not a scalar column.
For `composed_e2e` specifically, add nullable `llm_run_id` and `encoder_run_id` populated from the
`composed_trace`/`source_path` already on the row. Nullable text columns are catalog-only and cost
nothing at ingest. Safe-now: `COMMENT ON TABLE` recording the actual grain (§3 item 3.9) so nobody —
human or LLM — invents a join that cannot exist.

---

### DEF-10 — `mv_llm_p99_check` is stale; `v_llm_drift` silently checks 79% of runs [D4]

**Severity: HIGH** (a correctness guard that is quietly not guarding).

```sql
SELECT (SELECT count(*) FROM provenance.mv_llm_p99_check) mv_rows,
       (SELECT count(*) FROM (SELECT l.run_id FROM provenance.llm_request l GROUP BY 1) q
        JOIN provenance.llm_run_summary s USING (run_id)) live_rows;
-- verified: mv_rows=80 | live_rows=101   => 21 eligible runs (20.8%) missing
```

`v_llm_drift` reads exclusively from this matview and returns rows, so it *looks* healthy.

**Remediation.** `REFRESH MATERIALIZED VIEW` after the a16/g2/g3_32b/g6 loads (§4 — it is a write and
would be immediately stale again if run now), and make the refresh unconditional at the tail of
`loader/main.py` rather than a README note. Ship the freshness guard now (§3 item 3.10).

---

### DEF-11 — `is_current` is universally true; retraction is happening through side channels [A-11, C-06]

**Severity: HIGH** (false assurance).

```sql
SELECT count(*) total, count(*) FILTER (WHERE is_current) cur,
       count(supersedes) n_supersedes, count(superseded_by) n_superseded_by
FROM provenance.runs;
-- verified: 2206 | 2206 | 0 | 0

SELECT window_name, is_superseded, is_valid FROM provenance.grid_window WHERE is_superseded;
-- verified: burst5 is_superseded=t AND is_valid=t simultaneously
```

Retraction demonstrably has occurred (the burst5 `c_star` supersession, formally recorded in
`grid_correction`; and the DEF-3 collisions retired earlier results by destroying them), but the
spine's own mechanism is idle. `current_runs` / `current_llm_summary` / `current_encoder_summary` are
therefore indistinguishable from their base tables — an analyst who trusts them to be "the clean set"
gets everything, including the 394 unbacked summaries of DEF-8 and the six broken schedules of DEF-5.

**Remediation.** Decide which mechanism is authoritative (§5, DEC-6). Safe-now: `v_run_status`,
unioning the per-table supersession signals into one status column (§3 item 3.11), and a
`COMMENT ON COLUMN runs.is_current` stating it is not yet populated.

---

### DEF-12 — `window_name` values outside the `windows` dimension; `steady` vs `steady24h` is a typo-class split [D5]

**Severity: HIGH** (73 rows, 9 tables, including 18 rows of the spine itself).

```sql
SELECT 'runs' t, window_name, count(*) FROM provenance.runs x
 WHERE window_name IS NOT NULL AND NOT EXISTS (SELECT 1 FROM provenance.windows w WHERE w.window_name=x.window_name)
 GROUP BY 1,2;
-- verified: runs|week|18
```
Three unregistered values: `week` (22 rows: runs 18, composed_e2e 4), `head2k` (30 rows: sweep_point 18,
sweep_curve 3, sweep_decoupling 2, sweep_window 1, cost_model_variant 6), `steady` (21 rows: rerun_b1_curve_point 20, rerun_b1_window 1).

**Resolved during this plan's verification:**
- **`week` is an alias for the registered `aggregate`.** `windows.aggregate.requests = 749601`, and
  every `composed_e2e` row with `window_name='week'` has `requests = 749601`. Confirmed identical span.
- **`steady` is almost certainly `steady24h`.** `rerun_b1_*` uses `burst1..burst6` + `steady`, exactly
  mirroring the registered `burst1..6` + `steady24h` vocabulary.
- **`head2k` is a real, unregistered window** (a 2,000-request head slice used by the sweeps).

**Impact.** A `GROUP BY window_name` reports `steady` and `steady24h`, and `week` and `aggregate`, as
four distinct windows. `INNER JOIN runs → windows` drops 18 spine rows.

**Remediation.** `week`→`aggregate` and `steady`→`steady24h` are loader normalizations (§5, DEC-7) —
do not `UPDATE` measurements in place. `head2k` needs a real dimension row once its span and source
trace are confirmed. Safe-now: an alias view (§3 item 3.12). Do not add the `windows` FK until all
three resolve; gate it on:

```sql
SELECT count(*) FROM provenance.runs x WHERE window_name IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM provenance.windows w WHERE w.window_name=x.window_name);  -- must be 0
```

---

### DEF-13 — `verification` latency columns carry no unit and no comment [B-03, B-04]

**Severity: HIGH** (cheapest fix in this document; highest exposure per unit of effort).

```sql
SELECT min(enc_p99),max(enc_p99),min(ttft_p99),max(ttft_p99),min(itl_p99),max(itl_p99)
FROM provenance.verification;
-- verified ms magnitudes: enc_p99 588.4..2904.6 | ttft_p99 651.1..46238.5 | itl_p99 5.1..349.3

SELECT count(*) FROM information_schema.columns c
WHERE c.table_schema='provenance' AND c.table_name='verification'
  AND col_description('provenance.verification'::regclass, c.ordinal_position) IS NOT NULL;
-- verified: 0 of 12 columns documented
```

Every sibling table spells these `enc_p99_ms` / `ttft_p99_ms` / `itl_p99_ms`. Compounding this,
`measured_request` stores TTFT **twice** — `client_ttft` (seconds, 0.0735..4.9696) alongside
`ttft_client_ms` (73.5..4969.6) — so `WHERE client_ttft > 1000`, written by anyone who assumed the
schema-wide ms convention, silently returns zero rows and reads as "no slow requests".

**Remediation:** §3 items 3.13–3.15. Pure `COMMENT ON`, zero cost, do it first.

---

## 3. SAFE-NOW FIX LIST

Ordered, idempotent, non-destructive. Nothing here locks a big table, rewrites a heap, or slows bulk
ingest. Contents: `COMMENT ON` (catalog-only), `CREATE OR REPLACE VIEW` (catalog-only), one
`CREATE INDEX CONCURRENTLY` on a 2,206-row table, and `ANALYZE` on small tables only.

Run as one script; every statement is re-runnable.

```sql
-- =====================================================================
-- provenance: SAFE-NOW REMEDIATION  (safe to run during ongoing ingest)
-- Verified against the live store 2026-07-19.
-- =====================================================================
\set ON_ERROR_STOP on
BEGIN;

-- ---------------------------------------------------------------------
-- 3.1  Schema-level provenance of this audit
-- ---------------------------------------------------------------------
COMMENT ON SCHEMA provenance IS
  'Star schema: runs() is the spine; projections + raw facts reference runs.run_id. '
  'Structural audit 2026-07-19 -> provenance/audit/DB_STRUCTURE_PLAN.md. '
  'KNOWN BREAKS: worker_schedule 55% unjoinable (DEF-1); verification.run_id unprefixed (DEF-2); '
  'a16 run_id collisions destroyed 47k raw rows (DEF-3); forecast EWMA variants collapsed (DEF-4); '
  '9 of 13 projections carry no run_id (DEF-9); runs.is_current is inert (DEF-11). '
  'Consult the v_* audit views below before trusting any join.';

-- ---------------------------------------------------------------------
-- 3.2  Standing orphan audit  (DEF-1, DEF-2, DEF-6)
--      Run after EVERY load. Expected today: 118861 / 320 / 525.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_orphan_audit AS
SELECT 'worker_schedule'::text AS tbl, count(*) AS orphan_rows
  FROM provenance.worker_schedule x
 WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)
UNION ALL
SELECT 'verification', count(*)
  FROM provenance.verification x
 WHERE x.run_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)
UNION ALL
SELECT 'ingest_log', count(*)
  FROM provenance.ingest_log x
 WHERE x.run_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id);

COMMENT ON VIEW provenance.v_orphan_audit IS
  'Rows referencing a run_id absent from runs(). Baseline 2026-07-19: '
  'worker_schedule=118861, verification=320, ingest_log=525. Any INCREASE means a new load regressed.';

-- ---------------------------------------------------------------------
-- 3.3  Which ingested files never produced a spine row  (DEF-6)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_ingest_orphan AS
SELECT i.*
  FROM provenance.ingest_log i
 WHERE i.run_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = i.run_id);

COMMENT ON VIEW provenance.v_ingest_orphan IS
  'Files recorded as loaded whose spine row was never created (525 rows, 2026-07-19: '
  'K20=257 K3=112 K4=112 K25=31 K26=6 K29=5 K27=1 K28=1). Self-perpetuating: ingest_log '
  'idempotency will skip these files on any re-run.';

-- ---------------------------------------------------------------------
-- 3.4  run_id collision detector  (DEF-3) -- THE PRE-INGEST GATE
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_id_collision AS
SELECT run_id,
       count(DISTINCT regexp_replace(file_path,'/[^/]+$','')) AS ndir,
       array_agg(DISTINCT regexp_replace(file_path,'/[^/]+$','')) AS dirs,
       count(*) AS nfiles
  FROM provenance.ingest_log
 WHERE run_id IS NOT NULL
 GROUP BY 1
HAVING count(DISTINCT regexp_replace(file_path,'/[^/]+$','')) > 1;

COMMENT ON VIEW provenance.v_id_collision IS
  'One run_id fed by files from MORE THAN ONE directory. Because the loader is delete-then-insert, '
  'every row here is a site where a later file DESTROYED an earlier file''s rows (see DEF-3: 29311 '
  'llm_request + 16939 composed_request + 1793 encoder_series rows lost). grid:grid_summary (256 files, '
  '3 dirs) is benign -- the grid_* tables key on grid_run_id, not run_id. THE LOADER MUST FAIL if this '
  'view gains a row after a load.';

-- ---------------------------------------------------------------------
-- 3.5  Warn at the point of use  (DEF-1)
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.worker_schedule.run_id IS
  'WARNING -- DOES NOT UNIFORMLY JOIN TO runs.run_id. 118861 of 215030 rows (55%, 112 ids) use a '
  'COMPACT encoding (factorial:react_rho10_L30) absent from runs(), which uses the long form '
  '(factorial:issue-time:burst3:toto:L45:None:res15s:rho10:cs45:hy3:forecast:p90). Not recoverable by '
  'prefix-strip (0 of 112 match) and the compact form OMITS the window, so the mapping is ambiguous. '
  'An INNER JOIN to runs silently drops a biased 55%. See DEF-1.';

-- ---------------------------------------------------------------------
-- 3.6  verification -> runs reconciliation bridge  (DEF-2)
--      Resolves 313 of 320; exposes ambiguity instead of hiding it.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_verification_resolved AS
SELECT v.*,
       (SELECT count(*) FROM provenance.runs q
         WHERE split_part(q.run_id,':',2) = v.run_id)              AS n_candidates,
       (SELECT min(q.run_id) FROM provenance.runs q
         WHERE split_part(q.run_id,':',2) = v.run_id
           AND (SELECT count(*) FROM provenance.runs z
                 WHERE split_part(z.run_id,':',2) = v.run_id) = 1) AS resolved_run_id
  FROM provenance.verification v;

COMMENT ON VIEW provenance.v_verification_resolved IS
  'verification.run_id is stored UNPREFIXED (burst3_fc_timesfm_L60) while runs.run_id is namespaced '
  '(a11:burst3_fc_timesfm_L60), so all 320 rows are orphans. This view resolves by suffix. '
  'resolved_run_id is NULL where n_candidates <> 1: n_candidates=0 for 7 unresolvable ids, '
  'n_candidates=2 for react_L30 and static_C2 (a6: vs misc:). Use resolved_run_id, never run_id, to '
  'join verification to the spine.';

COMMENT ON COLUMN provenance.verification.run_id IS
  'STORED UNPREFIXED, unlike runs.run_id. All 320 rows are orphans w.r.t. runs(). '
  'Join via provenance.v_verification_resolved.resolved_run_id. See DEF-2.';

-- ---------------------------------------------------------------------
-- 3.7  worker_schedule integrity guard  (DEF-5)
--      Convention CONFIRMED: last step extends to metrics->>'sim_horizon_s'.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_worker_schedule_integrity AS
WITH e AS (
  SELECT run_id, provisioned_worker_seconds AS pws,
         (metrics->>'sim_horizon_s')::float8 AS sim_horizon_s
    FROM provenance.encoder_run_summary
   WHERE provisioned_worker_seconds IS NOT NULL),
s AS (
  SELECT w.run_id, w.t_s, w.worker_count,
         coalesce(lead(w.t_s) OVER (PARTITION BY w.run_id ORDER BY w.step_index),
                  e.sim_horizon_s) AS t_next
    FROM provenance.worker_schedule w
    JOIN e ON e.run_id = w.run_id),
i AS (
  SELECT run_id, sum(worker_count * greatest(t_next - t_s, 0)) AS integrated_ws,
         count(*) AS n_schedule_rows
    FROM s GROUP BY 1)
SELECT i.run_id, i.n_schedule_rows, e.sim_horizon_s,
       i.integrated_ws, e.pws AS stored_provisioned_ws,
       i.integrated_ws / nullif(e.pws,0) AS ratio,
       (abs(i.integrated_ws - e.pws) / nullif(e.pws,0)) > 0.01 AS schedule_mismatch
  FROM i JOIN e USING (run_id);

COMMENT ON VIEW provenance.v_worker_schedule_integrity IS
  'Recomputes provisioned worker-seconds from worker_schedule and compares to the stored projection. '
  'Holds to 1e-3 for 328 of 334 runs (median rel. error 0.000000). schedule_mismatch=true for exactly '
  'six misc:react_p90_W{120,240,480}_burst1_L{30,300} runs whose .sched.json belongs to a different, '
  '~16x longer simulation (ratios 5.49-6.44). DO NOT integrate worker_schedule for those six. See DEF-5.';

-- ---------------------------------------------------------------------
-- 3.8  Recomputability classifier  (DEF-8)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_llm_summary_backing AS
SELECT s.run_id,
       s.completed_requests,
       EXISTS (SELECT 1 FROM provenance.llm_request l WHERE l.run_id = s.run_id) AS has_raw_rows,
       split_part(s.run_id, ':', 1) AS family
  FROM provenance.llm_run_summary s;

COMMENT ON VIEW provenance.v_llm_summary_backing IS
  'has_raw_rows=false for 394 of 495 llm_run_summary rows (9,328,107 requests), ALL flagged '
  'is_current=true: misc 222, grid 93, riders 20, sweeps 19, reactive 14, planner 12, live 7, '
  'episode 6, g1 1. Percentiles from those runs are NOT auditable against evidence. Label every '
  'claim recomputable vs summary-only using this view. See DEF-8.';

-- ---------------------------------------------------------------------
-- 3.9  Declare the true grain of the keyless projections  (DEF-9)
-- ---------------------------------------------------------------------
COMMENT ON TABLE provenance.forecast_metrics IS
  'GRAIN: cross-run rollup. Carries NO run_id and NO window_name -- cannot be traced to an execution '
  'nor filtered by runs.is_current. Verified to reproduce exactly from raw provenance.forecast for '
  'span=''full''. See DEF-9.';
COMMENT ON TABLE provenance.coverage IS
  'GRAIN: (fleet, run, pool) rollup; NO run_id, NO window_name. Corroborated against '
  'llm_run_summary.completed_requests (52 A11 + 20 A12 + 5 A13 + 3 A14 rows, all exact). See DEF-9.';
COMMENT ON TABLE provenance.coverage_meta IS
  'GRAIN: global rollup; NO spine key. Arithmetic verified exact (749601 + 250399 = 1000000). See DEF-9.';
COMMENT ON TABLE provenance.quantile_coverage IS
  'GRAIN: cross-run rollup; NO run_id, NO window_name. See DEF-9.';
COMMENT ON TABLE provenance.forecast_eval IS
  'GRAIN: cross-run rollup; NO run_id, NO window_name. See DEF-9.';
COMMENT ON TABLE provenance.collector_fn IS
  'GRAIN: cross-run rollup; NO run_id, NO window_name. See DEF-9.';
COMMENT ON TABLE provenance.composed_e2e IS
  'GRAIN: (window_name, arm) -- COARSER than a run, and no run_id column. The LANGUAGE side is '
  'recoverable: joining llm_run_summary on ''a12:''||window_name||''_''||arm reproduces ttft_p99_ms '
  'and requests exactly for all 20 rows. The ENCODER side is NOT: 19 of 20 rows carry the '
  'SLA-saturated enc_p99_ms=588.4 shared by >=12 encoder runs. See DEF-9.';
COMMENT ON TABLE provenance.cost_accounting IS
  'GRAIN: (window_name, policy, lead_s) -- coarser than a run, no run_id. '
  'total_from_order_ws = provisioned_ws + warmup_ws verified exact for 40/40 rows.';

-- ---------------------------------------------------------------------
-- 3.10  Matview freshness guard  (DEF-10)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_mv_freshness AS
SELECT (SELECT count(*) FROM provenance.mv_llm_p99_check) AS materialized_rows,
       (SELECT count(*) FROM (SELECT l.run_id FROM provenance.llm_request l GROUP BY 1) q
          JOIN provenance.llm_run_summary s USING (run_id))  AS live_eligible_rows,
       (SELECT count(*) FROM provenance.mv_llm_p99_check) =
       (SELECT count(*) FROM (SELECT l.run_id FROM provenance.llm_request l GROUP BY 1) q
          JOIN provenance.llm_run_summary s USING (run_id))  AS is_fresh;

COMMENT ON VIEW provenance.v_mv_freshness IS
  'is_fresh=false as of 2026-07-19 (80 materialized vs 101 live) -- v_llm_drift, a correctness guard, '
  'is silently checking only 79% of eligible runs. REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check '
  'after every K1/K2 load. See DEF-10.';

-- ---------------------------------------------------------------------
-- 3.11  Unified run status  (DEF-11)
--       Surfaces the retraction signals that runs.is_current does not carry.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_run_status AS
SELECT r.run_id, r.experiment, r.pool, r.window_name, r.policy, r.model,
       r.is_current,
       EXISTS (SELECT 1 FROM provenance.llm_request l WHERE l.run_id = r.run_id)      AS has_llm_raw,
       EXISTS (SELECT 1 FROM provenance.encoder_series e WHERE e.run_id = r.run_id)   AS has_encoder_raw,
       EXISTS (SELECT 1 FROM provenance.worker_schedule w WHERE w.run_id = r.run_id)  AS has_schedule,
       r.run_id IN ('misc:react_p90_W120_burst1_L30','misc:react_p90_W120_burst1_L300',
                    'misc:react_p90_W240_burst1_L30','misc:react_p90_W240_burst1_L300',
                    'misc:react_p90_W480_burst1_L30','misc:react_p90_W480_burst1_L300')
                                                                                      AS schedule_suspect,
       r.experiment = 'misc'                                                          AS unclassified_family
  FROM provenance.runs r;

COMMENT ON VIEW provenance.v_run_status IS
  'runs.is_current is TRUE for all 2206 rows and supersedes/superseded_by are empty, so the current_* '
  'views filter NOTHING and are identical to their base tables. Meanwhile real retraction is recorded '
  'in grid_window.is_superseded + grid_correction. This view exposes the signals that actually '
  'discriminate: raw backing, schedule integrity, and unclassified family. See DEF-11.';

COMMENT ON COLUMN provenance.runs.is_current IS
  'NOT YET POPULATED AS A RETRACTION FLAG: true for all 2206 rows as of 2026-07-19, and '
  'supersedes/superseded_by are NULL everywhere. current_runs / current_llm_summary / '
  'current_encoder_summary therefore filter nothing. Authoritative retraction currently lives in '
  'grid_window.is_superseded and provenance.grid_correction. See DEF-11.';

-- ---------------------------------------------------------------------
-- 3.12  window_name alias reconciliation  (DEF-12)
--       week==aggregate confirmed via requests=749601 on both sides.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_window_alias AS
SELECT * FROM (VALUES
  ('week',      'aggregate', 'CONFIRMED: windows.aggregate.requests=749601 matches every composed_e2e week row.'),
  ('steady',    'steady24h', 'PROBABLE: rerun_b1_* uses burst1..burst6 + steady, mirroring the registered burst1..6 + steady24h.'),
  ('head2k',    NULL,        'UNREGISTERED, genuinely distinct: 2000-request head slice used by the sweeps. Needs a windows() row.')
) AS t(alias, canonical_window, note);

COMMENT ON VIEW provenance.v_window_alias IS
  'Unregistered window_name values (73 rows over 9 tables: week 22, head2k 30, steady 21) and their '
  'canonical equivalents. Normalize via this view until the loader is fixed. GROUP BY window_name '
  'currently reports week/aggregate and steady/steady24h as four distinct windows. See DEF-12.';

-- ---------------------------------------------------------------------
-- 3.13  UNITS: verification (DEF-13). Highest value per keystroke in this file.
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.verification.enc_p99 IS
  'Encoder-delay p99 in MILLISECONDS (observed 588.4..2904.6). Same quantity as '
  'encoder_run_summary.encoder_delay_p99_ms; the _ms suffix is missing from the name.';
COMMENT ON COLUMN provenance.verification.enc_max IS 'Encoder-delay max in MILLISECONDS.';
COMMENT ON COLUMN provenance.verification.ttft_p99 IS
  'TTFT p99 in MILLISECONDS (observed 651.1..46238.5) = llm_run_summary.p99_ttft_ms.';
COMMENT ON COLUMN provenance.verification.itl_p99 IS
  'Inter-token latency p99 in MILLISECONDS (observed 5.1..349.3) = llm_run_summary.p99_itl_ms.';
COMMENT ON COLUMN provenance.verification.gpu_h IS
  'GPU-HOURS (= llm_run_summary.gpu_hours; max 776.85 agrees exactly on both sides).';
COMMENT ON COLUMN provenance.verification.provisioned_ws IS
  'Provisioned WORKER-SECONDS (= factorial_cell.provisioned_ws / encoder_run_summary.provisioned_worker_seconds).';

-- ---------------------------------------------------------------------
-- 3.14  UNITS: measured_request duplicate seconds/ms pairs  (DEF-13)
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.measured_request.client_ttft IS
  'SECONDS (0.0735..4.9696). Duplicate of ttft_client_ms/1000 -- PREFER ttft_client_ms. '
  'WHERE client_ttft > 1000 silently returns zero rows.';
COMMENT ON COLUMN provenance.measured_request.ttft_server IS
  'SECONDS (0.0563..3.8497). Duplicate of ttft_server_ms/1000 -- PREFER ttft_server_ms.';
COMMENT ON COLUMN provenance.measured_request.itl_mean IS
  'MILLISECONDS despite the missing suffix (5.34..174.66). Same for itl_max, itl_median, itl_p95, itl_std.';

-- ---------------------------------------------------------------------
-- 3.15  UNITS + SYNONYMS: the remaining lens-B traps
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.ewma_ablation_cell.ws IS
  'PROVISIONED worker-seconds (synonym of factorial_cell.provisioned_ws) -- NOT busy worker-seconds. '
  'Verified by magnitude: ws ranges 16166..5101108 while factorial_cell.busy_ws ranges 710..17328.';
COMMENT ON COLUMN provenance.ewma_cal_param.horizon IS
  'Forecast horizon in STEPS (1..12) at the manifest resolution (15 s) -- NOT hours and NOT seconds. '
  '12 steps = 180 s. Contrast forecast_eval.horizon_h (hours) and sweep_point.horizon_s (seconds).';
COMMENT ON COLUMN provenance.cost_accounting.warmup_frac IS
  'Normalized by provisioned_ws, NOT by the adjacent total_from_order_ws. Verified 40/40 against '
  'warmup_ws/provisioned_ws and only 2/40 against warmup_ws/total_from_order_ws. Material at long lead: '
  'burst1/reactive/L165 stores 0.2272 (=106755/469903.9); the share of TOTAL ordered cost is 0.185127.';
COMMENT ON TABLE provenance.eda_rate_series IS
  'Values are PER-BIN COUNTS at the stated resolution. provenance.eda_metric stores the SAME statistics '
  'as PER-SECOND RATES (they differ by exactly the bin width: 22211/60 = 370.183). cv2 is scale-invariant '
  'and so agrees WITHOUT conversion -- which makes the 60x difference in the dimensional statistics easy to miss.';
COMMENT ON COLUMN provenance.eda_metric.value_num IS
  'Metric paths ending _per_s are PER-SECOND RATES regardless of the window_* prefix in metric_path. '
  'The corresponding eda_rate_series values are per-bin counts.';
COMMENT ON COLUMN provenance.collector_encoder_fn.engine IS
  'OVERLOADED: rows with engine in (''sdpa'',''flash_attention_2'') are ATTENTION-BACKEND variants, not '
  'engine modes. Genuine engines are aic/eager/compiled/vllm. GROUP BY engine mixes the two concepts.';
COMMENT ON COLUMN provenance.collector_closedloop_window.policy IS
  'COMPOSITE free-text label, NOT joinable to runs.policy. The single value ''p90/rho15/L30 (chronos)'' '
  'decodes to policy=forecast, quantile=p90, rho=15, lead_s=30, model=chronos.';
COMMENT ON COLUMN provenance.forecast_metrics.candidate IS
  'Quantile level p10..p90, or the literal ''point'' for the point forecast. Same role as runs.quantile, '
  'whose non-quantile member is ''obs''.';

-- runs.rho already documents "percent"; make the 1.15x trap explicit and mirror it to the siblings.
COMMENT ON COLUMN provenance.runs.rho IS
  'Headroom / utilization target in PERCENT, integer-valued {10,15,20,25}. rho=15 means a 1.15x '
  'provisioning factor -- NOT 15x, NOT 0.15. (ewma_cal_manifest.nominal stores the sibling concept '
  'as a FRACTION, e.g. 0.9 -- both conventions exist in this database.)';
COMMENT ON COLUMN provenance.factorial_cell.rho IS
  'Headroom in PERCENT, integer-valued {10,15,20,25}. See runs.rho.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.rho IS
  'Headroom in PERCENT, integer-valued {10,15,20,25}. See runs.rho.';

-- ---------------------------------------------------------------------
-- 3.16  Sparse spine dimensions: stop them reading as real filters  (D6)
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.runs.engine IS
  'SPARSE -- populated for only 2 of 2206 runs (0.09%), and as ''vLLM'' while every collector_* table '
  'spells it ''vllm''. DO NOT FILTER ON THIS COLUMN: WHERE engine=... returns almost nothing and looks '
  'like a legitimate result. Engine identity is implied by runs.experiment or recoverable from collector_*.';
COMMENT ON COLUMN provenance.runs.mode IS
  'SPARSE -- populated for only 24 of 2206 runs (1.1%). Not a reliable filter.';
COMMENT ON COLUMN provenance.runs.converter IS
  'SPARSE -- populated for only 77 of 2206 runs (3.5%). Not a reliable filter.';
COMMENT ON COLUMN provenance.runs.commit_sha IS
  'RESERVED, 100% NULL across all 2206 rows. NULL means NOT RECORDED, not "no commit". '
  'Same for runs.run_utc, runs.command, runs.artifact_paths, runs.horizon_h.';

-- ---------------------------------------------------------------------
-- 3.17  Disaggregated-routing fields are never emitted -- NULL != zero
-- ---------------------------------------------------------------------
COMMENT ON COLUMN provenance.llm_request.prefill_admit_ms IS
  'Disaggregated-routing field: NEVER emitted by the simulator -- 100% NULL across all 15.3M rows on '
  'every partition (2026-07). NULL means NOT MEASURED, not zero. Same for decode_admit_ms, '
  'decode_reused_input_tokens, decode_route_overlap_tokens, destination_activated_ms, '
  'destination_reserved_ms, prefill_route_overlap_tokens, prefill_worker_idx, source_held_ms, '
  'source_released_ms. The projection-level counterpart llm_run_summary.prefill_worker_seconds is '
  'present and always exactly 0.';
COMMENT ON COLUMN provenance.llm_request.decode_admit_ms IS
  'Disaggregated-routing field, 100% NULL. NULL means NOT MEASURED, not zero. See prefill_admit_ms.';

-- ---------------------------------------------------------------------
-- 3.18  Grid: corrected static baseline, derivable in SQL  (C-04, C-05)
--       Sourced from grid_correction, which is machine-readable -- no threshold guessing.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_grid_c_star_effective AS
SELECT w.grid_run_id, w.window_name, w.c_star,
       w.c_star_corrected,
       coalesce(w.c_star_corrected, c.corrected_value, w.c_star)::int AS c_star_effective,
       (c.correction_id IS NOT NULL OR w.is_superseded)              AS is_corrected,
       c.correction_id, c.rationale
  FROM provenance.grid_window w
  LEFT JOIN provenance.grid_correction c
         ON c.window_name = w.window_name
        AND c.field = 'c_star'
        AND c.correction_type = 'supersession';

CREATE OR REPLACE VIEW provenance.v_grid_static_effective AS
WITH e AS (SELECT window_name, c_star_effective FROM provenance.v_grid_c_star_effective)
SELECT max(c_star_effective)                                                   AS static_encoder_workers_effective,
       (array_agg(window_name ORDER BY c_star_effective DESC, window_name))[1] AS binding_window_effective,
       (SELECT static_encoder_workers FROM provenance.grid_run_summary LIMIT 1) AS static_as_ingested,
       (SELECT static_binding_window  FROM provenance.grid_run_summary LIMIT 1) AS binding_as_ingested
  FROM e;

COMMENT ON VIEW provenance.v_grid_static_effective IS
  'Verified 2026-07-19: effective static baseline = 8, binding window = burst2. grid_run_summary still '
  'records 16 / burst1 -- 16 comes from the SUPERSEDED burst5 c_star (corrected to 8 by '
  'grid_correction burst5:c_star:supersession, published value 8), and burst1''s c_star is 6, so the '
  'as-ingested pair is internally inconsistent under either regime. grid_run_summary is deliberately '
  'preserved as the pre-correction artifact; use THIS view for the corrected baseline.';

COMMENT ON COLUMN provenance.grid_vision_point.feasible IS
  'NOT corrected for burst5. MIN(encoder_workers) FILTER (WHERE feasible) returns 16 for burst5 forever, '
  'while the thesis publishes 8. The C=8 point is marked feasible=false on a queue-divergence heuristic '
  'later shown to be an endpoint artifact (see provenance.grid_correction.rationale). Use '
  'provenance.v_grid_c_star_effective for the corrected optimum. All six other windows reproduce c_star '
  'exactly as the cheapest feasible point.';

-- ---------------------------------------------------------------------
-- 3.19  Derived per-window cost ratio  (C-11)
--       160 of 208 rows have a NULL ratio although BOTH operands are present.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_ewma_ablation_ratio AS
SELECT a.*,
       coalesce(a.ratio_vs_static, a.ws / nullif(a.denom_static_c8_ws, 0)) AS ratio_vs_static_derived
  FROM provenance.ewma_ablation_cell a;

COMMENT ON VIEW provenance.v_ewma_ablation_ratio IS
  'ewma_ablation_cell.ratio_vs_static is populated ONLY for window_name=''aggregate'' (48/48) and never '
  'for burst1/burst3/burst4/burst5/steady24h (0/160), although ws is non-null on all 208 rows and '
  'denom_static_c8_ws is non-null and single-valued (3869278.4) on all 208. Any filter or average on '
  'ratio_vs_static silently sees only 23% of rows. Where stored, the value matches ws/denom to 5e-5. '
  'OPEN QUESTION: confirm the per-window denominator is intended to be the GLOBAL static-C8 figure.';

COMMIT;

-- ---------------------------------------------------------------------
-- 3.20  One index, outside the transaction. JUSTIFIED, and the ONLY one.
--       runs is 2,206 rows: the build is milliseconds and the per-INSERT
--       maintenance cost is one leaf update on a table that receives a few
--       hundred rows per load. Every audit view above and the entire
--       "which family is this" workflow scans runs by experiment, and the
--       existing indexes are (run_id), (is_current), (pool,window_name,policy,model)
--       -- none of which leads on experiment.
--       NOTE: no index is proposed on llm_request / composed_request /
--       encoder_series / forecast / measured_request. Verified 2026-07-19 that
--       EVERY partition of those already carries a run_id index; additional
--       composite indexes there would tax the remaining bulk loads. See section 4.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_experiment_idx
  ON provenance.runs (experiment);

-- ---------------------------------------------------------------------
-- 3.21  Refresh planner statistics on the SMALL tables only.
--       Deliberately excludes every partitioned raw fact table: a full
--       ANALYZE there is a large sample read that competes with ingest.
-- ---------------------------------------------------------------------
ANALYZE provenance.runs;
ANALYZE provenance.windows;
ANALYZE provenance.verification;
ANALYZE provenance.ingest_log;
ANALYZE provenance.llm_run_summary;
ANALYZE provenance.encoder_run_summary;
ANALYZE provenance.factorial_cell;
ANALYZE provenance.worker_schedule;
ANALYZE provenance.composed_e2e;
ANALYZE provenance.cost_accounting;
ANALYZE provenance.coverage;

-- ---------------------------------------------------------------------
-- 3.22  Post-run verification. Expected values stated inline.
-- ---------------------------------------------------------------------
SELECT * FROM provenance.v_orphan_audit;          -- 118861 / 320 / 525
SELECT count(*) FROM provenance.v_ingest_orphan;  -- 525
SELECT count(*) FROM provenance.v_id_collision;   -- collisions incl. grid:grid_summary (benign)
SELECT * FROM provenance.v_mv_freshness;          -- 80 / 101 / false
SELECT * FROM provenance.v_grid_static_effective; -- 8 | burst2 | 16 | burst1
SELECT count(*) FROM provenance.v_worker_schedule_integrity WHERE schedule_mismatch;  -- 6
SELECT count(*) FROM provenance.v_llm_summary_backing WHERE NOT has_raw_rows;         -- 394
SELECT count(*) FROM provenance.v_verification_resolved WHERE resolved_run_id IS NULL; -- 9 (7 + 2 ambiguous)
```

**Deliberately excluded from §3** and routed to §4/§5: every `DROP`, every `RENAME`, `ALTER TYPE` on
the `vllm_*` epoch columns, any `UPDATE` normalizing `'vLLM'`→`'vllm'` / `'week'`→`'aggregate'` /
`'1min'`→`'60s'` / `'AttentionBackendEnum.FLASH_ATTN'`, `REFRESH MATERIALIZED VIEW`, all FKs on the
partitioned raw tables, and all composite indexes on tables over ~1M rows.

---

## 4. DEFER-UNTIL-READ-ONLY PLAN

> ## ⛔ DO NOT RUN UNTIL INGEST IS COMPLETE
> Every statement below either rewrites a heap, takes an `ACCESS EXCLUSIVE` lock, or adds
> per-row write cost. Run only after a16, g2, g3_32b and g6 are fully loaded and the store is
> read-only for querying. Budget several hours and adequate `maintenance_work_mem`.

```sql
-- =====================================================================
-- POST-INGEST OPTIMIZATION -- DO NOT RUN DURING INGEST
-- =====================================================================
\set ON_ERROR_STOP on
SET maintenance_work_mem = '4GB';   -- session-local; 16 GB store, adjust to host RAM
SET max_parallel_maintenance_workers = 4;

-- ---------------------------------------------------------------------
-- 4.1  Referential integrity, added the cheap way.
--      NOT VALID first (catalog-only, instant), VALIDATE separately
--      (SHARE UPDATE EXCLUSIVE -- concurrent reads keep working).
--      PRECONDITION: DEF-1 and DEF-2 resolved, or these WILL fail.
-- ---------------------------------------------------------------------
-- Gate: all three must return 0.
SELECT count(*) FROM provenance.worker_schedule x
 WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id);
SELECT count(*) FROM provenance.verification x
 WHERE x.run_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id);
SELECT count(*) FROM provenance.runs x
 WHERE x.window_name IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM provenance.windows w WHERE w.window_name=x.window_name);

ALTER TABLE provenance.worker_schedule
  ADD CONSTRAINT worker_schedule_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.worker_schedule VALIDATE CONSTRAINT worker_schedule_run_fk;

ALTER TABLE provenance.runs
  ADD CONSTRAINT runs_window_fk FOREIGN KEY (window_name)
  REFERENCES provenance.windows(window_name) NOT VALID;
ALTER TABLE provenance.runs VALIDATE CONSTRAINT runs_window_fk;

-- The 15M-35M row raw facts. Verified orphan-free TODAY (0 orphans in llm_request,
-- composed_request, encoder_series), so these will validate -- but re-check first,
-- because a16/g2/g3_32b/g6 may introduce new ones.
SELECT 'llm_request' t, count(*) FROM provenance.llm_request x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)
UNION ALL SELECT 'composed_request', count(*) FROM provenance.composed_request x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id)
UNION ALL SELECT 'encoder_series', count(*) FROM provenance.encoder_series x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id=x.run_id);
-- all must be 0 before proceeding

ALTER TABLE provenance.llm_request
  ADD CONSTRAINT llm_request_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.llm_request VALIDATE CONSTRAINT llm_request_run_fk;
ALTER TABLE provenance.composed_request
  ADD CONSTRAINT composed_request_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.composed_request VALIDATE CONSTRAINT composed_request_run_fk;
ALTER TABLE provenance.encoder_series
  ADD CONSTRAINT encoder_series_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.encoder_series VALIDATE CONSTRAINT encoder_series_run_fk;

-- ---------------------------------------------------------------------
-- 4.2  Unique constraints on the vllm_* ETL family.
--      All seven natural keys were VERIFIED duplicate-free by lens D.
--      RATIONALE: without these, re-ingesting an already-loaded vLLM file
--      silently DOUBLES rows; idempotency currently rests entirely on the
--      ingest_log sha256 bookkeeping rather than on the schema.
--      Re-verify each with a HAVING count(*)>1 probe before creating.
-- ---------------------------------------------------------------------
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS vllm_token_itl_uq
  ON provenance.vllm_token_itl (request_id, token_index);
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS vllm_engine_step_uq
  ON provenance.vllm_engine_step (step_index);
-- vllm_prom_sample: key includes a NULLABLE label column -- use NULLS NOT DISTINCT (PG15+)
-- so NULL labels cannot slip past the constraint.
-- CREATE UNIQUE INDEX CONCURRENTLY vllm_prom_sample_uq
--   ON provenance.vllm_prom_sample (metric, labels, ts) NULLS NOT DISTINCT;

-- ---------------------------------------------------------------------
-- 4.3  Query indexes. Each justified; each too write-costly for §3.
-- ---------------------------------------------------------------------
-- (a) The dominant analytical access pattern on the raw facts is
--     "one run's rows, ordered in time". run_id alone is already indexed on
--     every partition; adding the time column turns the per-run percentile
--     and time-series scans into ordered index scans and removes the sorts.
--     Cost during ingest would be one extra index maintenance per row on
--     15-35M row tables -- which is exactly why it waits until now.
CREATE INDEX CONCURRENTLY IF NOT EXISTS llm_request_run_t_idx
  ON provenance.llm_request (run_id, arrival_ms);      -- adjust to the real time column
CREATE INDEX CONCURRENTLY IF NOT EXISTS composed_request_run_ts_idx
  ON provenance.composed_request (run_id, ts);
CREATE INDEX CONCURRENTLY IF NOT EXISTS encoder_series_run_t_idx
  ON provenance.encoder_series (run_id, t);

-- (b) forecast is queried as (model, variate, resolution, h, origin). The existing
--     per-partition index stops at h; adding origin covers the evaluation joins
--     that forecast_metrics reproduces. Do this only after the DEF-4 run_id/variant
--     columns land, so the index reflects the final shape.
CREATE INDEX CONCURRENTLY IF NOT EXISTS forecast_eval_key_idx
  ON provenance.forecast (model, variate, resolution, h, origin);

-- (c) Spine dimension lookups for the comparison matrices.
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_family_dims_idx
  ON provenance.runs (experiment, policy, model, lead_s, rho);

-- (d) Provenance lookups by file.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ingest_log_kind_idx ON provenance.ingest_log (kind);
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_source_path_idx ON provenance.runs (source_path);

-- ---------------------------------------------------------------------
-- 4.4  Split the misc default partitions.
--      composed_request_default holds 15,238,525 rows (43.6% of the table),
--      defeating partition pruning for nearly half the largest relation.
--      This is a DETACH + redistribute + ATTACH: full scan and rewrite.
--      It gets more expensive the longer it is left, which is why the
--      EMPTY partitions for the new families are created in section 6
--      BEFORE the load, not here.
-- ---------------------------------------------------------------------
BEGIN;
ALTER TABLE provenance.composed_request DETACH PARTITION provenance.composed_request_default;
CREATE TABLE provenance.composed_request_g3_32b PARTITION OF provenance.composed_request FOR VALUES IN ('g3_32b');
-- ... one per newly-mapped family ...
INSERT INTO provenance.composed_request SELECT * FROM provenance.composed_request_default;
DROP TABLE provenance.composed_request_default;
CREATE TABLE provenance.composed_request_default PARTITION OF provenance.composed_request DEFAULT;
COMMIT;
-- Repeat for llm_request (94,731 default rows) and encoder_series (1,793).

-- ---------------------------------------------------------------------
-- 4.5  Materialized views worth precomputing once the data stops moving.
-- ---------------------------------------------------------------------
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;   -- fixes DEF-10
SELECT * FROM provenance.v_mv_freshness;                 -- must show is_fresh = true

-- Per-run percentiles recomputed from raw rows: the evidence layer behind every
-- published latency number. Expensive (full scan + sort per run), read constantly,
-- and by definition stable once ingest ends.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_llm_percentiles AS
SELECT run_id, count(*) AS n,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY ttft_ms) AS p50_ttft_ms,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY ttft_ms) AS p90_ttft_ms,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS p99_ttft_ms
  FROM provenance.llm_request GROUP BY 1;
CREATE UNIQUE INDEX IF NOT EXISTS mv_llm_percentiles_pk ON provenance.mv_llm_percentiles (run_id);

-- Materialize the orphan/backing audits so the dashboards stop rescanning 35M rows.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_run_status AS
  SELECT * FROM provenance.v_run_status;
CREATE UNIQUE INDEX IF NOT EXISTS mv_run_status_pk ON provenance.mv_run_status (run_id);

-- ---------------------------------------------------------------------
-- 4.6  Physical ordering. Raw facts are ALWAYS read as "one run's rows in
--      time order", so clustering on (run_id, time) collapses each per-run
--      scan to a near-contiguous read. Rewrites the whole table under
--      ACCESS EXCLUSIVE -- catastrophic during ingest, ideal after it.
--      Do it PER PARTITION so each lock is short and it can be interrupted.
-- ---------------------------------------------------------------------
CLUSTER provenance.llm_request_a13      USING llm_request_a13_run_id_idx;
CLUSTER provenance.llm_request_a11      USING llm_request_a11_run_id_idx;
CLUSTER provenance.llm_request_a12      USING llm_request_a12_run_id_idx;
CLUSTER provenance.llm_request_a14      USING llm_request_a14_run_id_idx;
CLUSTER provenance.llm_request_a15      USING llm_request_a15_run_id_idx;
CLUSTER provenance.composed_request_a13 USING composed_request_a13_run_id_idx;
CLUSTER provenance.encoder_series_a13   USING encoder_series_a13_run_id_idx;
-- ... continue for the remaining large partitions ...

-- ---------------------------------------------------------------------
-- 4.7  FILLFACTOR. The store is append-only during ingest and read-only
--      after, so there is no reason to reserve free space for HOT updates.
--      100 maximizes tuples per page => fewer pages read per scan.
--      Takes effect on rewrite, so set it BEFORE the CLUSTER above if
--      running the whole script in order.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.llm_request      SET (fillfactor = 100);
ALTER TABLE provenance.composed_request SET (fillfactor = 100);
ALTER TABLE provenance.encoder_series   SET (fillfactor = 100);
ALTER TABLE provenance.forecast         SET (fillfactor = 100);
ALTER TABLE provenance.worker_schedule  SET (fillfactor = 100);
ALTER TABLE provenance.measured_request SET (fillfactor = 100);

-- ---------------------------------------------------------------------
-- 4.8  Statistics targets. Defaults (100 buckets) badly under-describe
--      run_id, which has hundreds-to-thousands of distinct values driving
--      every partition-pruning and join-order decision on the raw facts.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.llm_request      ALTER COLUMN run_id SET STATISTICS 1000;
ALTER TABLE provenance.composed_request ALTER COLUMN run_id SET STATISTICS 1000;
ALTER TABLE provenance.encoder_series   ALTER COLUMN run_id SET STATISTICS 1000;
ALTER TABLE provenance.worker_schedule  ALTER COLUMN run_id SET STATISTICS 1000;
ALTER TABLE provenance.forecast         ALTER COLUMN model  SET STATISTICS 500;
ALTER TABLE provenance.runs             ALTER COLUMN experiment SET STATISTICS 500;

-- Multivariate statistics: experiment and run_id are near-functionally dependent
-- (the prefix IS the experiment), which the planner cannot know without this.
CREATE STATISTICS IF NOT EXISTS provenance.llm_request_exp_run_stat (dependencies, ndistinct)
  ON experiment, run_id FROM provenance.llm_request;
CREATE STATISTICS IF NOT EXISTS provenance.composed_request_exp_run_stat (dependencies, ndistinct)
  ON experiment, run_id FROM provenance.composed_request;

-- ---------------------------------------------------------------------
-- 4.9  Partition-wise planning. Off by default in PG16; both are pure wins
--      on a star schema whose facts share a partition key, and they let
--      per-partition aggregates and joins run independently (and in parallel).
--      Set globally in postgresql.conf, not per-session, once verified.
-- ---------------------------------------------------------------------
ALTER SYSTEM SET enable_partitionwise_aggregate = on;
ALTER SYSTEM SET enable_partitionwise_join      = on;
SELECT pg_reload_conf();

-- ---------------------------------------------------------------------
-- 4.10  Final pass: reclaim the churn from the rewrites, refresh all stats.
--       VACUUM FULL is intentionally NOT used -- CLUSTER in 4.6 already
--       rewrote the large partitions compactly, so VACUUM FULL would only
--       repeat that work under the same exclusive lock.
-- ---------------------------------------------------------------------
VACUUM (ANALYZE, VERBOSE) provenance.llm_request;
VACUUM (ANALYZE, VERBOSE) provenance.composed_request;
VACUUM (ANALYZE, VERBOSE) provenance.encoder_series;
VACUUM (ANALYZE, VERBOSE) provenance.forecast;
VACUUM (ANALYZE, VERBOSE) provenance.worker_schedule;
VACUUM (ANALYZE, VERBOSE) provenance.measured_request;
VACUUM ANALYZE provenance.runs;
-- then, catching everything else:
VACUUM ANALYZE;

-- ---------------------------------------------------------------------
-- 4.11  Post-optimization acceptance
-- ---------------------------------------------------------------------
SELECT * FROM provenance.v_orphan_audit;          -- expect 0 / 0 / 0
SELECT * FROM provenance.v_mv_freshness;          -- expect is_fresh = true
SELECT count(*) FROM provenance.v_id_collision;   -- expect only benign path-keyed families
SELECT count(*) FROM provenance.runs WHERE experiment = 'misc';   -- expect 0
```

---

## 5. NEEDS-DECISION

Each of these changes semantics or requires a loader edit. Ordered by urgency.

---

### DEC-1 — a16 (and a16_ft) `run_id` policy — **BLOCKING, decide before the next load**

**Tradeoff.** Keeping the current scheme guarantees continued destruction: the loader is
delete-then-insert on a colliding key, and 47,043 rows are already gone. Changing it invalidates the
9 existing `misc:iter*` / `reactive:iter*` ids.

**Blast radius.** `loader/runid.py` + the a16 branch of `loader/loaders.py`; the 9 `runs` rows and
their `llm_request_reactive` / `llm_request_default` / `composed_request_default` rows; 48
`ingest_log` entries must be cleared so re-ingestion is not skipped as already-loaded. No view
references these ids. Small blast radius, catastrophic cost of inaction.

**Recommendation.** Adopt `a16:<config_dir>:<iter>` (e.g. `a16:burst3_reactive_P5000_q0.3:iter0`),
set `experiment='a16'`, populate `window_name`/`policy`/`model`/`rho` from the directory name, delete
the 9 stale rows and their `ingest_log` entries, create the `a16` partitions, re-ingest from disk.
Add the `v_id_collision` pre-flight as a hard gate. **Do this first.**

---

### DEC-2 — Add a discriminator to `forecast`, and a `run_id`

**Tradeoff.** `forecast` (16.7M rows) has no `run_id`, `source_path` or variant column, which is why
DEF-4's loss is unrecoverable *and* unattributable. Adding two nullable text columns in PG16 is a
catalog-only operation — no rewrite, no measurable ingest penalty. Not adding them guarantees the
same collapse for the incoming forecast output.

**Blast radius.** `forecast` and all 9 partitions inherit the columns automatically. `forecast_key_idx`
and the per-partition indexes are unaffected. No view selects `*` from `forecast`. The K10 loader
must populate them — the `run_id`s already exist in `ingest_log` (39 K10 files, all with a non-null
`run_id`) and are simply discarded on write.

**Recommendation.** Add `run_id text` and `variant text` **before the next ingest**; leave both
unindexed until §4. Backfill the existing 16.7M rows from `(model, variate, mode) → ingest_log.run_id`
in the post-load pass — derivable for every group except the collapsed EWMA case, which needs the
three files re-ingested.

---

### DEC-3 — Kill the `misc` fallback; extend the dir→experiment map

**Tradeoff.** `misc` currently absorbs 369 runs from 14 directories including four *entire families*
(g3_32b 215, rerun_verify 47, g6 20, g4_folds 18, aggregate44 ×3 = 42, g2 12, a16 ×2 = 10,
predictor_closedloop_v2 3, cap_sensitivity 2). It is the direct cause of DEF-3's collisions and
DEF-7's 15.2M-row default partition. Making `misc` a hard error means a load can now fail — which is
the point.

**Blast radius.** `loader/dirmap` (or equivalent) + every `WHERE experiment='misc'` filter and any
analysis that currently groups the misc bucket as one thing. Reclassifying moves rows between
partitions on re-ingest. `v_run_status.unclassified_family` (§3) makes the remaining set visible.

**Recommendation.** Map at minimum: `g2`, `g3_32b`, `g4`, `g6`, `a16`, `a16_ft`, `rerun_verify`,
`aggregate44` (+`_rho`, `_strict`), `predictor_closedloop_v2`, `cap_sensitivity`. Then make an
unclassifiable directory a **fatal** load error. Create the matching empty partitions first (§6) —
empty LIST partition creation is instantaneous and slightly *speeds* bulk load.

---

### DEC-4 — Reconcile the two `run_id` encodings for the factorial family (DEF-1)

**Tradeoff.** The compact `worker_schedule` form omits the window, so it may encode a genuinely
coarser object (one schedule reused across windows). If so, forcing it into `runs` is wrong and it
needs its own dimension plus a bridge table. If not, the long form must be minted at load.

**Blast radius.** 118,861 rows, 112 ids, plus the 112 K3 `.stats.json` files currently rejected by
the `llm_run_summary` FK (which is why that table has 0 rows for these ids). `worker_schedule_run_fk`
in §4.1 cannot be created until this resolves.

**Recommendation.** Determine the grain from the source `.sched.json` files first. If per-run: re-mint
long-form ids and re-ingest both K3 and K4. If coarser: create a `schedule_template` dimension and
have `runs` reference it. Do not guess — the ambiguity is real, not notational.

---

### DEC-5 — Prefix `verification.run_id` (DEF-2)

**Tradeoff.** A 320-row reload buys a joinable trust table. Doing nothing leaves verified runs
reading as unverified forever.

**Blast radius.** `load_verification` (K8b); the PK is `(source_path, run_id)` so the rewrite changes
the key; 2 ids are ambiguous (`react_L30`, `static_C2` across `a6:` and `misc:`) and 7 unresolvable —
those 9 need manual triage. `v_verification_resolved` (§3) becomes redundant afterwards but harmless.
Also fix the 6 duplicate `(run_id, stage)` rows with `stage IS NULL` (`timesfm`, `chronos`, `toto`,
two each) while there — they double-count in any `GROUP BY run_id`.

**Recommendation.** Do it. Resolve the 9 by hand first; gate the reload on the ambiguity query in DEF-2.

---

### DEC-6 — Choose one supersession mechanism (DEF-11)

**Tradeoff.** Today there are two: an inert spine (`is_current`/`supersedes`/`superseded_by`, plus
`runs_supersedes_idx` and four `current_*` views) and an active ad-hoc channel
(`grid_window.is_superseded` + `grid_correction` prose + silent overwrite). Keeping both means the
`current_*` views provide **false assurance**.

**Blast radius.** If the spine wins: the loader must switch from delete-and-overwrite to
UPDATE-then-INSERT-new-`run_id` so retractions leave an audit trail instead of a hole, and the known
retractions must be backfilled. If it loses: drop 3 columns, 1 index and 4 views, and every consumer
of `current_*` must be repointed.

**Recommendation.** Keep the spine and populate it — the store already *needs* retraction semantics
(the burst5 supersession and the DEF-3 overwrites both happened) and having the mechanism sit idle
while retraction happens through overwrite is precisely how DEF-3 destroyed data unnoticed. In the
interim, `v_run_status` (§3) carries the real signal.

---

### DEC-7 — Canonicalize the window vocabulary (DEF-12)

**Tradeoff.** `week` → `aggregate` and `steady` → `steady24h` are `UPDATE`s of a dimension key on 43
rows across 3 tables, which is an in-place semantic edit — hence not in §3. `head2k` needs a real
`windows` row, which requires confirming its span and source trace.

**Blast radius.** `runs` (18), `composed_e2e` (4), `rerun_b1_window` (1), `rerun_b1_curve_point` (20),
plus the sweep family for `head2k` (30). Any saved query or figure script that literally selects
`window_name='week'` breaks. `runs_window_fk` in §4.1 is blocked until this resolves.

**Recommendation.** Confirm `week ≡ aggregate` (already strongly evidenced: `requests = 749601` on
both sides) and `steady ≡ steady24h`, then normalize **at the loader** and reload the affected kinds.
Insert the `head2k` dimension row once its span is measured. Use `v_window_alias` (§3) meanwhile.

---

### DEC-8 — Naming unification (lens B, low urgency, high annoyance)

Seven spellings of encoder-worker-count (`encoder_workers`, `config_c`, `c_star`, `c_star_corrected`,
`c_star_as_ingested`, `c_star_effective`, `cstar`, `n_workers`, `worker_count`,
`static_encoder_workers`, `optimal_encoder_workers`); six of provisioned worker-seconds; two opposite
word orders for p99 (`ttft_p99_ms` vs `p99_ttft_ms`); `divergent` vs `queue_divergent`; `vLLM` vs
`vllm`; `vision`/`llm` vs `encoder`/`language`/`both` vs `'both (E2E)'`; `1min` vs `60s`;
`AttentionBackendEnum.FLASH_ATTN` vs `flash_attention_2`; `p50` vs `0.5` in `eda_metric.stat`;
`ctx`/`ContextTokens`/`ctx_tokens_per_s` in `eda_metric.signal`.

**Tradeoff.** Renaming is a loader + view + query rewrite for zero data-correctness gain. Leaving it
costs every future reader a lookup and occasionally a silently-empty filter (case-sensitive `vLLM`;
`'both (E2E)'` dropping 3 coverage rows against 393 `runs` rows).

**Blast radius.** Wide and shallow — many call sites, none load-bearing.

**Recommendation.** **Do not rename now.** §3 documents every synonym via `COMMENT`, which makes them
discoverable from `\d+` at zero risk. Apply value normalizations (`vLLM`→`vllm`, `1min`→`60s`,
`'both (E2E)'`→`both`, the enum repr) as `UPDATE`s in the post-ingest pass, and defer column renames
to a future schema cut. Canonical names to record now: `config_c`, `provisioned_worker_seconds`,
`queue_divergent`, metric-first `ttft_p99_ms`.

---

### DEC-9 — Type unification for `vllm_*` timestamps

`ts` is `timestamptz` in `eda_rate_series`, `forecast` and `collector_bench_run` but
`double precision` epoch-seconds in `vllm_prom_sample` (2.2M rows), `vllm_detok`, `vllm_sys_sample`,
`vllm_vision_encode`. `eda_burst_episode.start_ts/end_ts` are the only naive `timestamp` in the schema.
(`composed_request.ts` and `encoder_series.t` are simulation-relative offsets — legitimately numeric.)

**Recommendation.** `ALTER TYPE ... USING to_timestamp(ts)` rewrites a 2.2M-row table and breaks the
`v_vllm_prom_*` views — not worth it. Document via `COMMENT` (add to §3 if desired) and leave the
types alone. Revisit only if cross-family time joins become common.

---

### DEC-10 — Populate the reproducibility block on `runs`

`commit_sha`, `run_utc`, `command`, `artifact_paths` are 100% NULL across all 2,206 rows — exactly
the fields that would make a run reproducible. `horizon_h` is simply dead (live copies are in
`forecast_eval`).

**Recommendation.** The incoming a16/g2/g3_32b/g6 load is the cheapest possible moment to start
populating them; retrofitting 2,206 historical rows is not worth it. Until then §3 comments them as
*reserved and unpopulated* so a NULL is not read as "not applicable". Drop `runs.horizon_h` in the
post-ingest schema cut.

---

## 6. PRE-INGEST CHECKLIST — a16, g2, g3_32b, g6

The a2t/a2tf conflation and the a16 collision have the **same root cause**: a family reaching the
loader without a dir→experiment mapping, falling through to `misc`, and colliding on a generic
`run_id` that the delete-then-insert loader then resolves by destroying the earlier rows. Every item
below exists to break that chain. **Work top to bottom; do not start the load until §6.8 passes.**

### 6.1 Register the families in the dir→experiment map — **blocking**
```
defense/anim/data/a16_runs                -> a16
defense/anim/data/a16_ft/runs             -> a16_ft   (or a16, per DEC-1)
defense/anim/data/g2_runs                 -> g2
defense/anim/data/g2_runs/traces          -> g2
defense/anim/data/g3_32b/reports          -> g3_32b
defense/anim/data/g6_runs                 -> g6
defense/anim/data/g4_folds                -> g4
simulation/results/rerun_verify           -> rerun_verify
.../aggregate44, aggregate44_rho, aggregate44_strict -> aggregate44
.../predictor_closedloop_v2               -> predictor_cl2
.../cap_sensitivity                       -> cap_sensitivity
```
Then make an unmapped directory a **fatal error**, not a silent `misc`.

### 6.2 Create the empty partitions — **blocking**, instant, zero ingest cost
Empty LIST partitions are catalog-only and slightly *accelerate* bulk load by routing rows away from
the 15.2M-row default. Existing partition set is `a2, a2t, a2tf, a2x, a6, a11, a12, a13, a14, a15,
ctmatrix, eda, episode, ewma, factorial, g1, grid, live, phasee, planner, predictors, reactive,
riders, sweeps, default` (verified 2026-07-19).

```sql
-- Run BEFORE the load. Idempotent by inspection; re-running errors harmlessly on "already exists".
DO $$
DECLARE fam text; tbl text;
BEGIN
  FOREACH fam IN ARRAY ARRAY['a16','a16_ft','g2','g3_32b','g4','g6',
                             'rerun_verify','aggregate44','predictor_cl2','cap_sensitivity'] LOOP
    FOREACH tbl IN ARRAY ARRAY['llm_request','composed_request','encoder_series'] LOOP
      IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                      WHERE n.nspname='provenance' AND c.relname = tbl||'_'||fam) THEN
        EXECUTE format('CREATE TABLE provenance.%I PARTITION OF provenance.%I FOR VALUES IN (%L)',
                       tbl||'_'||fam, tbl, fam);
        EXECUTE format('CREATE INDEX ON provenance.%I (run_id)', tbl||'_'||fam);
      END IF;
    END LOOP;
  END LOOP;
END $$;

-- Verify: every new family has 3 partitions, each with a run_id index.
SELECT c.relname, count(i.indexrelid) idx
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  LEFT JOIN pg_index i ON i.indrelid=c.oid
 WHERE n.nspname='provenance'
   AND c.relname ~ '_(a16|a16_ft|g2|g3_32b|g4|g6|rerun_verify|aggregate44|predictor_cl2|cap_sensitivity)$'
 GROUP BY 1 ORDER BY 1;
```
If a forecast model outside `{arima, chronos, ewma, holt_winters, moirai, naive, timesfm, toto}`
arrives, add its `forecast` partition the same way.

### 6.3 `run_id` uniqueness — **blocking**
`runs` has `PRIMARY KEY (run_id)`, so a collision either aborts the load or (worse, under the current
loader) silently overwrites. The minting rule must include **every dimension that distinguishes two
directories**: family, config directory, and iteration. `a16:burst3_reactive_P5000_q0.3:iter0`, never
`misc:iter0`.

Pre-flight gate — must return **zero new rows** relative to the recorded baseline:
```sql
SELECT * FROM provenance.v_id_collision;
```
Wire this into `loader/main.py` as a hard abort, not an advisory.

### 6.4 Kind codes
Register the kind code for every new artifact shape *before* the load. Unregistered kinds are the
mechanism by which files enter `ingest_log` without producing a spine row (525 such rows today,
DEF-6). Confirm coverage after a dry run:
```sql
SELECT kind, count(*) FROM provenance.ingest_log
 WHERE file_path LIKE '%a16%' OR file_path LIKE '%g2_runs%'
    OR file_path LIKE '%g3_32b%' OR file_path LIKE '%g6_runs%'
 GROUP BY 1 ORDER BY 1;
```

### 6.5 Loader registration
Confirm each new family has a registered loader for each artifact kind it emits, and that the
spine-row writer runs **before** the FK-protected projection writers. DEF-1 is exactly what happens
when it does not: `worker_schedule` (no FK) kept 118,861 rows while `llm_run_summary` (FK) silently
rejected the matching 112 summaries.

### 6.6 Schema prerequisites — apply before the load
- `ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS run_id text;` (DEC-2)
- `ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS variant text;` (DEC-2)
- optionally `composed_e2e.llm_run_id` / `encoder_run_id` (DEF-9)

All are nullable-column adds: catalog-only in PG16, no rewrite, no ingest penalty.

### 6.7 Spine field population
For the new families, populate `window_name`, `policy`, `model`, `quantile`, `rho`, `lead_s` from the
directory name rather than leaving them NULL (all 9 current a16 rows have them NULL, which is why
those runs are indistinguishable). This is also the cheapest moment to start filling `commit_sha`,
`run_utc`, `command` and `artifact_paths` (DEC-10). Register any new `window_name` in `windows`
**first** — do not create a fourth unregistered value.

### 6.8 Go/no-go gate

Record the baseline, load, then re-run. **Any increase is a stop.**
```sql
-- BEFORE (baseline verified 2026-07-19)
SELECT * FROM provenance.v_orphan_audit;         -- 118861 / 320 / 525
SELECT count(*) FROM provenance.v_id_collision;
SELECT count(*) FROM provenance.runs WHERE experiment='misc';   -- 369
SELECT count(*) FROM provenance.composed_request_default;       -- 15,238,525

-- AFTER: v_orphan_audit must not increase; v_id_collision must gain NO new run_id;
-- misc must not increase (target: it decreases to 0);
-- composed_request_default must not grow.

-- Row-level reconciliation: expected vs actual, per run
SELECT i.run_id, i.n_rows AS expected, coalesce(c.n,0) AS actual, i.n_rows-coalesce(c.n,0) AS missing
  FROM (SELECT run_id, sum(n_rows) n_rows FROM provenance.ingest_log WHERE kind='K2' GROUP BY 1) i
  LEFT JOIN (SELECT run_id, count(*) n FROM provenance.llm_request GROUP BY 1) c USING (run_id)
 WHERE i.n_rows IS DISTINCT FROM coalesce(c.n,0) ORDER BY 4 DESC;
-- must be EMPTY for every newly loaded run. A non-empty result is DEF-3 recurring.
```

### 6.9 Immediately after the load
```sql
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;   -- DEF-10; wire into loader/main.py
SELECT * FROM provenance.v_mv_freshness;                 -- is_fresh must be true
ANALYZE provenance.runs;
```

Then, and only then, §4 becomes eligible.

---

*Generated 2026-07-19 from the five-lens read-only audit. Every count and identity in this document
was re-verified against the live store while writing it. No statement in §1–§3 modifies data; §4 and
§5 are explicitly gated.*
