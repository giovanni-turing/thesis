# WINDOW_ALIAS — the `week` / `aggregate` fold: what it is, what it cost, and the guard

**Date:** 2026-07-20 · **DB:** `provenance` @ localhost:5433, PostgreSQL 16
**Status:** defect CONFIRMED and REAL; thesis impact NIL; two guard checks (`C210`, `C211`) installed.

> **REMEDIATED 2026-07-20 — `provenance/schema/22_corrections.sql` PART B, applied.**
> The §3.2 DDL below was executed (with one addition): `runs` 129 and `composed_e2e` 4 `week`→`aggregate`;
> `rerun_b1_window` 1 and `rerun_b1_curve_point` 20 `steady`→`steady24h`; `head2k` registered in `windows()`
> (trace_offset 0, 2000 req, span 721.072 s, from `sweeps/traces/llm_head2k.jsonl.stats.json`);
> `span_chronos → aggregate` and `fulltrace → (do not fold)` registered in `v_window_alias`.
> **Addition to the plan:** each affected table gained a `window_name_as_ingested` column, backfilled for
> every row, so the pre-normalisation spelling is preserved and the rename is reconstructable exactly by
> `WHERE window_name <> window_name_as_ingested`. **`C209`, `C210`, `C211` are now all GREEN**; no
> previously green check regressed (46 checks: 40 pass, 6 fail, all `warn` and all pre-existing —
> C107, C207, C302, C306, C404, C601). Sections 1, 4 and 6 below describe the PRE-remediation state and are
> kept as the record of the defect.

---

## 1. THE FACT

### 1.1 What the alias structure actually is

`provenance.v_window_alias` declares three entries. Measured against the live data:

| alias | canonical | where the alias spelling actually occurs | verdict |
|---|---|---|---|
| `week` | `aggregate` | `runs` (129), `composed_e2e` (4) — and, via `run_id`, `encoder_run_summary` 116, `llm_run_summary` 13, `worker_schedule` 120 325, `composed_request` 749 601, `llm_request` 5 996 808 | **SAME SPAN — fold is correct** |
| `steady` | `steady24h` | `rerun_b1_window` (1), `rerun_b1_curve_point` (20). **Never in `runs`** (`runs` uses `steady24h`, 268) | **SAME SPAN — fold is correct; note should be upgraded PROBABLE → CONFIRMED** |
| `head2k` | *(none)* | `sweep_window` (1), `sweep_point` (18), `sweep_curve` (3), `sweep_decoupling` (2), `cost_model_variant` (6) | **GENUINELY DISTINCT — refusing to fold is correct** |

**Exactly one fold occurs inside `provenance.runs`: `week` (129) → `aggregate` (6) = 135.** All other 21
distinct values pass through as identity (burst1 332, burst2 51, burst3 332, burst4 299, burst5 296,
burst6 51, steady24h 268, e7–e18 8–16 each, fulltrace 15, plus 157 rows with NULL `window_name`).
`v_dim` is row-preserving: 2060 runs in, 2060 out.

> **Correction to the premise.** The figure is **135**, not 136 (129 `week` + 6 `aggregate`).
> `SCHEMA_GUIDE.md` §3 prints 136 / 6 / 130 and is off by one on two of the three numbers. Fixed there.

### 1.2 Is folding correct, or are the aliases distinct?

**The view is right. The base tables are wrong.** `week` and `aggregate` denote the identical span —
the 5.60-day chronos-forecastable window, 749 601 requests, 483 659.8 s, trace_offset 250 399. Proven on
four independent axes:

1. All 122 `week`+`aggregate` `encoder_run_summary` rows carry `requests = 749 601` — exactly `windows.aggregate.requests`.
2. All 122 carry `total_images = 11 408 002`, identical across both spellings.
3. All 13 `week`-spelled `llm_run_summary` rows have `num_requests = completed_requests = 749 601`.
4. `max(worker_schedule.t_s)` tops out at **483 644.9 s under both spellings** vs `windows.aggregate.span_s = 483 659.8` — one 15-s actuation step short, as expected.

It is emphatically **not** the 7-day `fulltrace` (604 799.7 s / 1 000 000 req). The "is `week` really 7 days?"
worry does not apply.

`steady == steady24h` is likewise **CONFIRMED, not merely probable**: `rerun_b1_window.steady` has
`trace_offset = 627 019`, `total_reqs = 88 260`, `span_h = 23.999`, against `windows.steady24h`
`trace_offset = 627 019`, `requests = 88 260`, `span_s = 86 396.7` (= 23.999 h). Byte-for-byte the same window.

### 1.3 A third name, undocumented

`provenance.windows` contains `aggregate` and `span_chronos` as **byte-identical rows**
(`trace_offset = 250 399`, `requests = 749 601`, `span_s = 483 659.8`). So one span carries **three names** —
`week` / `aggregate` / `span_chronos` — and `v_window_alias` documents only one of the two folds.
This is a *new* defect, one level up from the one under investigation. Guarded by `C211`.

### 1.4 WHICH QUERY IS RIGHT — unambiguously

```sql
-- ✗ WRONG. Returns 6 of 135 runs. Silently. No error.
SELECT ... FROM provenance.runs WHERE window_name = 'aggregate';

-- ✗ ALSO WRONG. Returns 0 rows. Silently. No error.
SELECT ... FROM provenance.composed_e2e WHERE window_name = 'aggregate';

-- ✓ RIGHT. Alias-aware, 135 runs.
SELECT ... FROM provenance.v_dim WHERE window_name = 'aggregate' AND is_current;
```

**Rule: never filter `window_name` on a base table. Route every window-scoped query through
`provenance.v_dim` (or join to it) — that is the only relation where the canonical name means what it says.**

The worst case is concrete and worth stating in full: `SELECT ... FROM provenance.runs WHERE
window_name='aggregate'` returns **only** the six `misc:react_p90_W{120,240,480}_aggregate_L{30,300}`
reactive-ablation runs and silently omits every headline run of that window — all `planner:week_*`,
`a11:week_*`, `a12:week_*`, `misc:week_static_C6/C7/C8`, and 112 factorial runs.

### 1.5 Blast radius, and the structure that contained it

`runs` is the **only relation in the entire schema carrying both spellings**. Everywhere else the spelling
is determined by the table, so a filter using whichever spelling that table actually uses returns the
*complete* population:

| relation | rows under aliased window names |
|---|---|
| `runs` | `aggregate` 6, `week` 129, `steady24h` 268 — **the only intra-table split** |
| `composed_e2e` | `week` 4 (no `aggregate`) |
| `ewma_ablation_cell` | `aggregate` 48, `steady24h` 32 (no `week`, no `steady`) |
| `factorial_cell` | `steady24h` 232 |
| `cost_accounting` | `steady24h` 8 |
| `grid_command` 13, `grid_closeout_variant` 5, `grid_vision_point` 4, `grid_llm_point` 3, `grid_window` 1 | `steady24h` |
| `rerun_b1_curve_point` 20, `rerun_b1_window` 1 | `steady` |
| `windows` | `aggregate` 1, `steady24h` 1 |
| `collector_*` (5), `sweep_*` (4), `cost_model_variant`, `grid_correction` | none |

Row-level exposure via `run_id` from the 135 split runs is ≈ 6.9 M child rows.

---

## 2. IMPACT ON THE THESIS

### **Zero verdicts change. Zero edits to revert. Nothing to restore.**

Every recorded audit query was re-run alias-aware and compared side by side.

**Only 2 of the ~990 claim objects filter `runs`/`current_runs` on an aliased window name in a way that
could bite, and neither moves:**

| claim | recorded verdict | as recorded | alias-aware | outcome |
|---|---|---|---|---|
| `verified/conclusion.json` (cost-ratio claim, `current_runs.window_name='week'`) | THESIS_WRONG | 15 rows | 15 rows, **byte-identical** (incl. `planner:week_fc_p90` gpu_hours = 518.6063450234815, `a13:ft_llm_static` = 672.0093014234247) | **UNCHANGED** |
| `verified/aiconfigurator.json` (`encoder_delay_p99_ms`, `r.window_name='week'`) | CONFIRMED | n=116, min 588.37, max 6083.88, `bool_or(queue_divergent)=f` | n=**122**, min 588.37, max 6083.88, `bool_or=f` | **UNCHANGED** |

`conclusion.json` is immune because the six `aggregate`-spelled runs are all `pool=encoder` with **no
`llm_run_summary` row** (verified: all six have `has_llm = false`), so they never survive the join.

`aiconfigurator.json` is the **only claim in the whole audit whose population actually changes** — and its
statistics do not, because the six added values (588.37, 588.37, 588.37, 700.694, 733.643, 784.483) fall
strictly inside the pre-existing range. Alias-aware there is still exactly one `C=8` static week run:
`misc:week_static_C8 = 644.44 ms` vs published **644**. Verdict stands.

### The three `THESIS_WRONG` verdicts — the dangerous case — are alias-immune by construction

`verified/tese.json:68`, `verified/tese.json:114`, `verified/conclusion.json:85` are all the same
0.96× → 0.97× cost-ratio proposal. Their operands cannot see the alias at all:

- numerator: an explicit `run_id IN (...)` list on `llm_run_summary` — no `window_name` filter;
- denominator: `provenance.windows`, which has one `aggregate` row and **no `week` row**.

They were **already rejected** as **R18 in `ADJUDICATION.md` §0.4.3**, for an independent and stronger
reason: 0.9650 is the exact 2-dp tie point under all three legitimate denominators (0.96501675 /
0.96502895 / 0.96501512); the spread between defensible denominators (3e-5) exceeds the distance from the
tie (1.5e-5), so the value is not resolvable to two decimals. **Not re-opened.**

### Nothing was applied, so nothing needs reverting

Confirmed against the live tree, 2026-07-20:

- `tex/tese.tex:68` — `language fleet near-break-even, 0.96$\times$).`
- `tex/tese.tex:114` — `0,96$\times$).`
- `tex/closedloop.tex:376` — `span (0.96$\times$; replica scaling cannot morph TP2 into TP1, so the`
- `tex/conclusion.tex:85` — `0.96$\times$ its burst-sized static shape); the reactive controller's apparent aggregate pass`

All four still read 0.96. **No revert. No restored text. None of the 32 edits applied 2026-07-19/20 is impeached.**

### Reverse check

No `CONFIRMED` verdict was reached on a narrow population that the full population contradicts. Every
`CONFIRMED` claim among the aliased-window set filters a table with a single-spelling population
(`composed_e2e` `week`, `ewma_ablation_cell` `aggregate`, `factorial_cell` `steady24h`, `windows`) — i.e.
already complete. A targeted grep for `from provenance.(runs|current_runs) ... window_name='aggregate'`
across all 23 audit files returns **zero hits**.

### The honest caveat

**The audit survived by a data property, not by defensive query authoring.** It survived because outside
`runs` each table happens to use exactly one spelling. The same SQL style *would* produce wrong answers
the moment a future ingest writes an `aggregate`-spelled row into `composed_e2e` or a `week`-spelled row
into `ewma_ablation_cell`. Routing verification through `v_dim` remains the right practice — it just has
no retroactive consequences here.

---

## 3. IMPACT ON THE STORE

### 3.1 Is `v_dim`'s fold correct? — **Yes, and it should be strengthened**

The fold `week → aggregate` and `steady → steady24h` is semantically right. It is however **incomplete**:
it omits the `aggregate == span_chronos` duplication inside `provenance.windows`, and it understates the
`steady == steady24h` evidence as `PROBABLE` when it is provably CONFIRMED.

### 3.2 Should the base tables carry a canonical window column? — **Yes: normalise in place**

Adding a second `canonical_window_name` column would leave two columns and two ways to be wrong. The right
fix is to **normalise `window_name` itself to the canonical spelling** everywhere, and let `v_dim` keep the
fold only as a defensive no-op. That also turns `C209` green (129 `week` runs currently have no `windows` row).

```sql
-- ============================================================
-- REMEDIATION (NOT APPLIED — requires a maintenance window and a
-- re-run of the full check suite; recorded here so it is one command
-- when the store next accepts writes)
-- ============================================================
BEGIN;

-- 3.2a  Normalise the alias spellings to canonical in every base table.
UPDATE provenance.runs                 SET window_name = 'aggregate' WHERE window_name = 'week';    -- 129
UPDATE provenance.composed_e2e         SET window_name = 'aggregate' WHERE window_name = 'week';    --   4
UPDATE provenance.rerun_b1_window      SET window_name = 'steady24h' WHERE window_name = 'steady';  --   1
UPDATE provenance.rerun_b1_curve_point SET window_name = 'steady24h' WHERE window_name = 'steady';  --  20

-- 3.2b  Register head2k, which is genuinely distinct and has no windows row
--       (v_dim.window_span_s is NULL for it, so no sweep_* result can be cost-ratioed).
INSERT INTO provenance.windows (window_name, trace_offset, max_requests, requests, note)
VALUES ('head2k', 0, 2000, 2000,
        'trace head slice used by the sweep_* family: first 2000 requests from 2024-10-15 12:00:00. '
        'Genuinely distinct from every other window; NOT an alias of aggregate.')
ON CONFLICT (window_name) DO NOTHING;

-- 3.2c  Retire the two folds that are now no-ops, keep the head2k disclaimer,
--       and record the third name of the aggregate span.
--       (v_window_alias is a VIEW over a VALUES list in schema/20_semantic.sql;
--        edit that file — do not try to UPDATE the view.)
COMMIT;
```

### 3.3 Does `provenance.windows` need alias rows? — **No. It needs the opposite.**

Adding `week` and `steady` rows to `windows` would legitimise the drift and make the duplicate-span problem
worse (there would then be four names for one span). `windows` should hold **one row per distinct span**.
The action item there is the reverse: **collapse `span_chronos` into `aggregate`**, or, if `span_chronos`
must survive for the forecast-coverage narrative, record the identity explicitly in `v_window_alias`
(`span_chronos → aggregate`) so `C211` can go green. Recommended edit to `schema/20_semantic.sql`:

```sql
-- in the v_window_alias VALUES list:
  ('week',         'aggregate', 'CONFIRMED: requests=749601, total_images=11408002, completed_requests=749601 '
                                'and max(worker_schedule.t_s)=483644.9 all identical to the aggregate window.'),
  ('steady',       'steady24h', 'CONFIRMED (upgraded from PROBABLE): rerun_b1_window.steady has trace_offset=627019, '
                                'total_reqs=88260, span_h=23.999 == windows.steady24h exactly.'),
  ('span_chronos', 'aggregate', 'CONFIRMED: byte-identical windows row (trace_offset=250399, requests=749601, '
                                'span_s=483659.8). Kept as a separate name only for the forecast-coverage narrative.'),
  ('head2k',        NULL,       'GENUINELY DISTINCT: 2000-request trace head used by the sweeps. Do not fold.')
```

---

## 4. THE GUARD

Two checks were **written to `provenance.check_definition`** (the one authorized write). Both are
**RED right now, by design** — they are the alarm for a defect that is still present in the data. They go
green when §3.2 is applied.

### `C210` — error — *Window-name alias fold: no base table may carry a non-canonical window spelling*

Enumerates every base relation in `provenance` with a `window_name` column (from `pg_attribute`, so it
covers tables added in future), crosses it with every registered alias, and counts both spellings via
`query_to_xml` dynamic probes. It fails if **any** base table holds an alias-spelled row — that is exactly
the condition under which a canonical-name filter on that table returns a materially different population
than the alias-aware filter through `v_dim`. Rows where both spellings coexist are additionally flagged
`[INTRA-TABLE SPLIT]`, the worst case.

Current output:

```
ALIAS SPLIT: provenance.composed_e2e: week=4 vs canonical aggregate=0 [canonical filter returns a fraction/none];
             provenance.rerun_b1_curve_point: steady=20 vs canonical steady24h=0 [...];
             provenance.rerun_b1_window: steady=1 vs canonical steady24h=0 [...];
             provenance.runs: week=129 vs canonical aggregate=6 [INTRA-TABLE SPLIT]
```

```sql
WITH rels AS (
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
SELECT (SELECT count(*) FROM bad) = 0 AS passed,
       CASE WHEN (SELECT count(*) FROM bad) = 0
            THEN 'No base table carries a non-canonical window spelling; every base-table window filter sees the full alias-aware population.'
            ELSE 'ALIAS SPLIT: ' || (SELECT string_agg(
                     format('%s: %s=%s vs canonical %s=%s%s', rel, alias, n_alias,
                            canonical_window, n_canon,
                            CASE WHEN n_canon > 0 THEN ' [INTRA-TABLE SPLIT]' ELSE ' [canonical filter returns a fraction/none]' END),
                     '; ' ORDER BY rel, alias) FROM bad)
       END AS detail;
```

### `C211` — warn — *`provenance.windows`: no unregistered duplicate span*

Fails when two `windows` rows share `(trace_offset, requests, span_s)` without the pair being registered in
`v_window_alias`. Same defect one level up: a query keyed on one name silently misses evidence filed under
the other.

Current output:

```
UNREGISTERED DUPLICATE SPAN(S): aggregate == span_chronos (trace_offset=250399, requests=749601, span_s=483659.8)
```

```sql
WITH dup AS (
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
SELECT (SELECT count(*) FROM unreg) = 0 AS passed,
       CASE WHEN (SELECT count(*) FROM unreg) = 0
            THEN 'Every provenance.windows row denotes a distinct span, or its duplicate spelling is registered in v_window_alias.'
            ELSE 'UNREGISTERED DUPLICATE SPAN(S): ' || (SELECT string_agg(
                     format('%s (trace_offset=%s, requests=%s, span_s=%s)',
                            array_to_string(names, ' == '), trace_offset, requests, span_s),
                     '; ' ORDER BY trace_offset) FROM unreg)
       END AS detail;
```

### `SCHEMA_GUIDE.md`

§3 "Window-name drift" has been corrected (136/130 → **135/129**) and given an explicit trap box pointing at
`C210`, `C211` and this file.

---

## 5. HONEST BOUNDING — how much of the verification this could have touched

Mechanical scan of all 23 files under `audit/verified/` and `audit/adversarial/`:

| population | count | share |
|---|---|---|
| claim objects scanned | **990** (the headline figure of 917 counts adjudicated claims; the file-level object count is 990) | 100 % |
| claims whose recorded SQL touches `window_name` at all | **221** | **22 %** |
| …filtering an **aliased** window name (`week`/`aggregate`/`steady`/`steady24h`) against a base table | **52** | **5.3 %** |
| …of those, filtering `runs` / `current_runs` — the only relation where the split can bite | **5** | **0.5 %** |
| …of those 5, on a *foldable* name rather than `burst*`/`steady24h` | **2** | **0.2 %** |
| claims whose result actually changes alias-aware | **1** (`aiconfigurator`, 116 → 122 rows) | **0.1 %** |
| claims whose **verdict** changes | **0** | **0 %** |

**Do not overstate:** the maximum conceivable exposure was 22 % of the audit, but the realised exposure was
one claim, whose statistics were unmoved. **Do not minimise:** the defect is real, it is latent in `runs`
today, and 135 runs / ≈6.9 M child rows sit behind it. The reason nothing broke is a data accident, not a
safeguard — which is precisely why `C210` now exists.

### Scoping limits of this assessment

- The scan keys on **recorded SQL text** in the claim JSONs. A verdict decided by reasoning never written
  into a `sql`/`query` field would not have been caught. 221 of 990 claim objects carried window-touching
  SQL and only those could be re-run.
- Two findings surfaced **outside** the alias scope, reported here but not investigated:
  1. `factorial_cell` has **zero** `week`/`aggregate` rows despite 112 runs with `experiment='factorial'`
     AND `window_name='week'` — a coverage gap, unrelated to the alias, worth its own check.
  2. Six `burst1`-labelled runs (`misc:react_p90_W{120,240,480}_burst1_L{30,300}`) have
     `encoder_run_summary.requests = 64 804` correctly matching burst1, yet their `worker_schedule.max(t_s)`
     is 483 3xx–483 6xx s — the schedule clock is **full-trace-relative**, so any span derived from
     `max(worker_schedule.t_s)` is wrong for those runs.
- Adjacent hazard with zero current exposure: any join between `rerun_b1_window` and `grid_window` on
  `window_name` silently drops the `steady` row (7 windows → 6).

---

## 6. `check_all()` matrix after installing the guard

46 checks (C007 disabled). **38 pass, 8 fail** — 7 of the 8 pre-existing and documented, plus the two new
guards, of which `C210` is the one this document is about.

| check | sev | pass | detail |
|---|---|---|---|
| C001 | error | ✓ | 0 runs with `completed_requests <> count(llm_request)`; 108 compared |
| C002 | error | ✓ | 0 of 108 exceed 1e-3 on `median_ttft_ms` |
| C003 | warn | ✓ | 0 of 108 exceed 2e-2 on `p99_ttft_ms` (worst 0.00389) |
| C004 | error | ✓ | 0 of 368 mismatch on `encoder_run_summary.requests` |
| C005 | error | ✓ | 0 of 444 exceed 1e-3 on the worker-seconds integral |
| C006 | error | ✓ | 0 of 1080 forecast cells disagree beyond 1e-6 |
| C008 | error | ✓ | 0 of 16 EDA 1 s statistics disagree beyond 1e-6 |
| C101 | error | ✓ | 0 of 40 cost_accounting rows break the decomposition |
| C102 | error | ✓ | 0 of 208 ewma_ablation_cell ratio rows break |
| C103 | error | ✓ | 1000000 = 749601 + 250399 |
| C104 | error | ✓ | 0 of 80 coverage rows where `ok <> (requests >= expect)` |
| C105 | error | ✓ | vllm_token_itl = energy.tot_gen_tokens = 1 354 025 |
| C106 | error | ✓ | 0 of 6 hard reconciliation checks failing |
| **C107** | warn | ✗ | 1 of 7 soft checks: `measured:vllm_h100_trace/client_gen_tokens_eq_gen` mismatch=24 (known logprob edge; server truth used) |
| C201–C205 | error | ✓ | 0 orphans (llm_request, composed_request, encoder_series, worker_schedule 214 262, verification) |
| C206 | info | ✓ | 313 of 355 verification rows carry a bare run_id absent from runs (expected) |
| **C207** | warn | ✗ | 301 of 2484 ingest_log rows reference a run_id absent from runs (pre-existing) |
| C208 | error | ✓ | 0 orphans across llm/encoder summaries and factorial_cell |
| **C209** | warn | ✗ | **129 runs whose `window_name` is not in `windows`: `week`** ← the same defect, seen from the FK side |
| **C210** | **error** | **✗** | **ALIAS SPLIT: composed_e2e week=4; rerun_b1_curve_point steady=20; rerun_b1_window steady=1; runs week=129 vs aggregate=6 [INTRA-TABLE SPLIT]** ← NEW GUARD |
| **C211** | **warn** | **✗** | **UNREGISTERED DUPLICATE SPAN: aggregate == span_chronos** ← NEW GUARD |
| C301 | error | ✓ | 0 run_ids map to >1 source_path |
| **C302** | warn | ✗ | 2 runs whose run_id prefix ≠ experiment (`measured:vllm_h100_trace`, `measured:vllm_per_request`) |
| C303 | error | ✓ | 0 run_ids without a colon |
| C304, C305 | error | ✓ | 0 logical and 0 physical partition misfiles |
| **C306** | warn | ✗ | 94 runs filed under `experiment = misc` |
| C401 | error | ✓ | 0 dangling supersession pointers |
| C402 | info | ✓ | runs=2060, not_current=2, supersedes=2, superseded_by=2 |
| C403 | error | ✓ | 0 of 284 `has_raw_records` disagreements |
| **C404** | warn | ✗ | 176 of 284 llm_run_summary rows have no backing raw rows |
| C405 | error | ✓ | mv_llm_p99_check 108 rows = 108 runs with raw rows |
| C501–C507 | error | ✓ | all vocabularies clean (pool, policy, quantile, readiness, actuation, engine, coverage.pool) |
| **C601** | warn | ✗ | default-partition rows: composed = 14 165 602 |
| C602 | error | ✓ | 0 malformed sha256 |
| C603 | error | ✓ | 0 families with raw rows but no dedicated partition |

**New failures introduced by this work: `C210` (error) and `C211` (warn) — both intended.** No previously
green check turned red. `C209` was already red for the same underlying reason and is the FK-side view of
`C210`; applying §3.2 turns all three green at once.
