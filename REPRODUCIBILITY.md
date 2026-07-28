# Reproducibility and provenance guide

Every number in the dissertation (`tex/tese.pdf`) traces to a pinned
artifact in this repository. This file is the entry point for verifying
that claim.

## Quick verification (no GPU, no database)

From a clean checkout:

```bash
# 1. Three-headline clean-checkout reproduction (detached worktree,
#    predicate-driven, negative probes; expects 0.623 vs 0.623):
bash verification/repro_clean_checkout.sh

# 2. Semantic gate: binds every promoted claim (chapter, conclusion,
#    abstracts EN+PT, both deck mirrors) to its artifact values, with
#    58 adversarial self-test mutations:
python3 verification/metric_stack_gate.py
python3 verification/metric_stack_gate.py --selftest "$(pwd)"

# 3. Silicon negative gates: 18 injected corruptions of the physical
#    replay evidence must each fail loudly (runs from tracked evidence
#    only — no live campaign state needed):
python3 verification/silicon_negative_gates.py
```

## Full delivery suite

`bash provenance/verify_all.sh` runs the 65-check suite (artifact
lineage, cache freshness, loader idempotency, the gates above, byte-gated
figure regeneration). It needs the provenance database (below) and the
`eda/.venv` environment.

## The provenance database

The Postgres schema `provenance` (raw traces, projections, `current_*`
views, evidence caches) is **derived state**: it rebuilds entirely from
tracked repository artifacts.

```bash
# connection (defaults: localhost:5433, user goku, db postgres);
# override with TESE_PGHOST / TESE_PGPORT / TESE_PGUSER / TESE_PGDATABASE
psql -h localhost -p 5433 -U goku -d postgres -f provenance/schema/00_*.sql   # apply schema files in order
python3 provenance/loader/main.py           # load + settle (idempotent; re-run must change nothing)
```

Read through the `current_*` views; the materialized caches carry
cardinality- and content-freshness guards (`v_mv_stale`,
`mv_check_results`).

## Key evidence pins

| What | Where |
|---|---|
| Results ledger (every artifact, command, date, and the tex it feeds) | `progress/results-ledger.md` |
| Silicon physical replay, burst window (5 reps × 3 arms + negative gates) | commit `6a8b2d7`, `simulation/results/silicon_anchor/SETTLED_EVIDENCE.md` |
| Silicon calm-day tier (15 reps + vLLM exact retimes, two-table gate) | commit `1511606`, `.../TIER3_STEADY24H_EVIDENCE.md` |
| Model / container identity | model+config sha256 and the vLLM image digest in `SETTLED_EVIDENCE.md` |
| Adversarial review corpus (118 disputes, all terminally closed) | `review/bridge/` (protocol in `BRIDGE.md`; 600+ validated messages) |
| Visual review corpus (per-figure and per-slide verdicts) | `review/visual/` |

## External inputs (not in this repository)

- **Trace**: the public Azure LLM inference trace (multimodal week);
  fetch per `workload/` documentation.
- **Model weights**: `Qwen/Qwen3-VL-8B-Instruct` from Hugging Face; the
  extracted vision tower's sha256 is pinned in the silicon evidence.
- **Engines**: vLLM `v0.22.0` by immutable digest
  (`sha256:0fec7ec5...`); HF-transformers versions in
  `simulation/results/silicon_anchor/env_snapshot_2026-07-28.json`.
- **GPU**: encoder measurements are RTX 5090-specific (locked clocks;
  collection protocol in the methodology chapter and
  `collector_artifacts/`).

## Archived record

This repository, its full git history (as a git bundle in which every
thesis-repository evidence pin above resolves; external-repository
commits are cited against their own upstreams), and a `pg_dump` of the
settled provenance schema are being archived under the **reserved DOI
[10.5281/zenodo.21654632](https://doi.org/10.5281/zenodo.21654632)**
(record registration pending publication --- this section flips tense
when the DOI resolves publicly)
(author ORCID [0000-0003-3682-1188](https://orcid.org/0000-0003-3682-1188)).
Corrections after examination will appear as new versions under the same
concept DOI. The GitHub repository (`gio-turing/thesis`) remains the live
mirror.
