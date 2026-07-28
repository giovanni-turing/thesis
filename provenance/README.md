# provenance — thesis execution results in Postgres

A single structured store for the thesis's execution results: **raw traces as the source of
truth + derived projections that are traceable back to them, row for row**, queryable in natural
language. Replaces the flat-file + Markdown-ledger workflow (`progress/results-ledger.md`) with a
relational store where retracted results are marked and excluded by default.

- (catalog snapshot 2026-07-28) **210 ordinary + 4 partitioned tables**,
  **59 views + 5 materialized views**, from **5,051 distinct `ingest_log`
  source paths**; drift audit: 185 rows, max |drift| 1.2375%, all with
  matching row counts.
- Engine: the `ssd2` **PostgreSQL 16** container — schema **`provenance`**.
- Reachable two ways: locally at `localhost:5433` (user `goku`, db `postgres`) and via the
  **`technonous` MCP** (`postgres_query`) — the latter is the AI/NL→SQL path.

## Query it (AI / NL→SQL)

Ask questions through the `technonous` MCP `postgres_query` tool, or `psql`. **Query the
`current_*` views** — they exclude retracted/superseded runs (`runs.is_current = false`):

```sql
-- Closed-loop headline: forecast-p90 stays feasible with falling cost across rho; p50 fails SLA
SELECT quantile, rho, bool_and(feasible) feasible, round(min(provisioned_ws))::int min_ws
FROM provenance.current_factorial
WHERE window_name='burst5' AND model='chronos' AND policy='forecast' AND readiness IS NULL
GROUP BY quantile, rho ORDER BY quantile, rho;
```

Column semantics are stored as SQL comments (`\d+ provenance.<table>`, or `pg_description`) so an
LLM writing SQL has the data dictionary inline.

### Handy entry points
- `current_llm_summary`, `current_encoder_summary`, `current_factorial`, `current_runs` — retraction-filtered.
- `v_forecast_best` — min-WAPE forecaster per (signal, resolution, mode).
- `v_infeasible` — factorial cells failing the 1000 ms p99 SLA.
- `v_closedloop_frontier` — forecast provisioning cost by window × model × quantile × ρ.
- `v_cost_frontier_dual` — forecast vs reactive, readiness- vs order-billed (the cost-order flip).
- `v_coverage` — full-trace (1M req) coverage guarantee per pool.
- `v_llm_drift` — **lineage audit** (below).

## Schema shape

```
runs  (spine: one row per execution; all comparison dims denormalized; supersedes/is_current)
 ├─ PROJECTIONS  llm_run_summary · encoder_run_summary · factorial_cell · coverage(_meta) ·
 │               verification · forecast_metrics · quantile_coverage · collector_fn · cost_accounting
 ├─ RAW FACTS    llm_request(K2) · encoder_series(K5) · composed_request(K6) · worker_schedule(K4) ·
 │               forecast(K10) · measured_request(K11)   -- big ones LIST-partitioned by experiment/model
 └─ PROVENANCE   ledger_entry(results-ledger.md) · ingest_log(idempotency)
```

Every RUN-KEYED projection and raw row carries `run_id → runs` (collector and other keyless projections are documented in `SCHEMA_GUIDE.md` §keyless), so a projected number is recomputable from
that run's raw rows. Dimensions (pool, window, policy, model, quantile, resolution, ρ, lead, config
C*, TP×N, gpu, engine, actuation, readiness…) live on `runs` / `factorial_cell`.

## Lineage / drift audit

`v_llm_drift` recomputes p99 TTFT from raw `llm_request` and compares it to the stored
`llm_run_summary` — the "is a chapter number still consistent with its artifact?" check. Current
state: **worst 0.39% across all 71 runs, every rowcount matches** (the 0.39% is percentile-
interpolation noise). Refresh after any K1/K2 reload:

```sql
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;
```

## Retraction handling

`runs.is_current = false` hides a run from every `current_*` view. Seeded rule: `actuation =
'target-time'` is demoted (superseded by issue-time). Finer supersession (specific retracted
artifacts named in `results-ledger.md` as prose) is marked manually:
`UPDATE provenance.runs SET is_current=false WHERE run_id = '…';`

## (Re)build

```bash
# 1. schema: apply EVERY numbered migration in numeric order (idempotent;
#    currently through 41_conv_relation_gate.sql). Reset with:
#    psql ... -c 'DROP SCHEMA provenance CASCADE'
for f in $(ls schema/[0-9]*.sql | sort -V); do
  psql -h localhost -p 5433 -U goku -d postgres -f "$f"
done
# 2. loaders
python3 loader/main.py --projections     # small typed layer (fast; NL queries usable after)
python3 loader/main.py --raw             # heavy raw fact tables (COPY; ~3 min parallel)
python3 loader/main.py                   # full pass incl. POST (K34 lineage refresh etc.)
```

Loader details: `loader/db.py` (psql transport — password from `docker inspect postgres` at
runtime, never persisted; bulk load streams CSV into `psql \copy`), `loader/runid.py`
(filename→dims), `loader/loaders.py` (per-kind K1–K13), `loader/ingest_common.py` (idempotency).
Re-running is idempotent: a file whose sha256 is unchanged in `ingest_log` is skipped
(`--reload` forces). `.claude/worktrees/` copies are excluded.

## Notes / follow-ups
- The 8 new-measurement families (`defense/anim/NEW-MEASUREMENTS.md`) are ingested + verified against
  the doc (experiments `a11 a12 a13 a14 a15 a2t a2tf a2x`, table `cost_accounting`). Still generating
  at build time (load with a plain `main.py` re-run once on disk): **A15 language E2E, A12 TimesFM
  language arms, A11 `week_fc_timesfm_L60`** — per-request records are written only at run completion.
- Unmatched experiments land in each partitioned table's `*_default` partition (correct, just not pruned).
- `grid_summary.json` (static-optimal C*/TP*/N* per window) is not yet a dedicated table — the
  individual grid runs are in `llm_run_summary`/`encoder_run_summary`; add a `grid_optimum` table if needed.
