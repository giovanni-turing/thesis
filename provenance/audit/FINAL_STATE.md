# FINAL STATE — provenance store + thesis  (certified 2026-07-20)

Read this first. It is the one-page truth about what is in the store, what you can trust, what is
broken, and how to check any of it yourself. Nothing here is inflated in either direction.

## Verdict

**The store is arithmetically sound and the thesis agrees with it.** Every quantitative claim that
can be recomputed from an archived artifact does recompute; the manuscript builds clean; and the
handful of failing checks are each failing *for a named, adjudicated reason*, not because anything
drifted. No check was made to pass by weakening it.

## Store at a glance

| | |
|---|---|
| runs (spine) | **3,147** (2,461 `is_current`, 686 retracted, 4 with an explicit `superseded_by`) |
| rows | **99,019,523** exact across 211 base tables |
| raw partitions | composed_request 41,106,599 · llm_request 18,869,922 · encoder_series 10,342,685 · forecast 22,003,500 · worker_schedule 235,827 |
| tables / views / matviews | 211 / 56 / 5 |
| ingest_log | **4,149** files (1:1 with `file_path`, sha256-keyed, **0 dangling** — every path still on disk) |
| size | 21 GB |
| connection | `psql -h localhost -p 5433 -U goku -d postgres` (password from `docker inspect postgres`) |

## What is trustworthy

- **The 12 cross-table semantic identities (Lens C).** Checks `C001–C010`, `C101–C106` reproduce
  every projection from its raw rows. Only `C002` is off, by 0.18 % on one run (see below).
- **Referential integrity.** `check_all()` A2 + the independent orphan sweep: **0** orphan `run_id`s
  across every analytic table. Partition keys never disagree with `runs.experiment` (`C304/C305`).
- **Idempotency.** Re-running the whole loader changes **nothing**: a content digest over
  `ingest_log`, the annotated `runs` columns and the six raw/summary tables is byte-identical across
  three consecutive passes. (Three POST-passes and the ledger loader *print* nonzero counters while
  changing nothing — SCHEMA_GUIDE §6.14. The gate judges by the digest, not the printout.)
- **Lineage freshness.** `mv_llm_p99_check` is fresh (178 = 178); worst raw-vs-summary TTFT drift is
  1.24 % (< 2 %); every summary rowcount matches its raw rows.
- **The thesis.** `latexmk -pdf -g` exits 0, **0 errors, 0 undefined refs, 149 pages**. All 48
  `ADJUDICATION §0.4` rejected fixes are still correctly absent/present (spot pins: 882/783 absent;
  67.3/248, "were not priced", 1.1–6.8 %, 18.0 %, 0.96× all present; twopool ITL p99 = 87.7 ms, the
  86.2 that was once applied is reverted).

## Known limitations — permanent, not repairable in-store

- **Historical collision loss (unrecoverable):** 29,311 `llm_request` + 16,939 `composed_request` +
  1,793 `encoder_series` rows were overwritten by an early `misc:` run_id collision; the source
  corpus is no longer on disk. The mechanism is fixed (collision guard + injectivity in
  `selftest.py`); the rows themselves are gone.
- **432 of 610 `llm_run_summary` rows** (11.5 M requests) have **no raw backing** — the request logs
  were never archived, so those percentiles cannot be audited. Use `v_llm_summary_backing`.
- **9 `verification` rows never resolve** (3 structural markers + 6 model-level aggregates). Left
  failing as `C214` rather than exempted.
- **9,177 `worker_schedule` rows** on 6 `rerun_verify:react_p90_*` runs carry the aggregate run's
  schedule (`is_valid=false`); their stored `provisioned_worker_seconds` is still correct.

## Known failing checks — all adjudicated, none weakened

| check | sev | why it is allowed to fail |
|---|---|---|
| `C002` | error (ACCEPTED) | 1/178 runs, 0.18 % on `median_ttft_ms`: percentile-interpolation convention, not drift. Tolerance deliberately kept at 1e-3. |
| `C107` | warn | 24/7,817 client-vs-server gen-token mismatch at a vLLM logprob edge; server truth is stored. |
| `C207` | warn | 306 rows: `ingest_log.run_id` is an artifact-group label for 6 aggregate kinds, plus 5 legacy K35 log mislabels. |
| `C214` | warn | the 9 unresolvable verification rows above. |
| `C302` | warn | the 2 hand-assigned `measured:*` ids that deliberately encode source-class, not chapter. |

## Outstanding (clean gaps — something absent, nothing wrong)

- `simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` (3 files) never ingested; experiment
  `m235b` declared in `runid.py` but unloaded. Needs a loader for that report shape.
- File coverage: 5,673 result-like files on disk, 4,149 ingested, **1,536 not ingested (27.1 %)** —
  dominated by secondary artifacts (`.log`/`points`/`sched` siblings) and post-manuscript defence
  data, not measurements. "Not in the DB" is not evidence against a number — go to the artifact.

## How to re-verify (one command each)

```bash
./provenance/verify_all.sh                       # full gate: data + thesis + delivery, exits 0 when green
psql ... -c "select * from provenance.check_all() where not passed"   # the 5 failing, with notes in check_definition
(cd provenance/loader && python3 selftest.py && python3 main.py)      # 3/3 green; digest stable (counters may print)
cd tex && latexmk -pdf -g -interaction=nonstopmode tese.tex          # 0 err / 0 undef / 149 pp
```

Deeper reference: `provenance/SCHEMA_GUIDE.md` (schema, traps, worked queries) ·
`provenance/audit/ADJUDICATION.md §0.4` (the rejected-fix table) · `progress/results-ledger.md`
(artifact↔manuscript provenance, final entry dated 2026-07-20).
