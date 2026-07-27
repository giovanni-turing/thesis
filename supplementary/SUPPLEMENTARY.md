# Supplementary material — electronic appendix

Thesis: *Forecast-Informed Vision-Pool Provisioning for Modality-Disaggregated
Multimodal Serving* (Giovanni Oliveira, IME-USP).

This archive is the electronic appendix referenced from **Appendix A,
Table `tab:ap-supp`** of the manuscript. It defines what the archive is,
where each item lives, and how to reproduce it. **It copies nothing bulky:
every item below is a pointer to a path that already exists in the thesis
repository.** The manuscript's in-document mapping (Appendix A,
`tab:ap-manifest`) stays complete and self-contained; this archive is the
*depth* behind it, not a substitute for it.

## Pinned baselines

| Ref | Commit | What it pins |
|---|---|---|
| Manuscript baseline | `67bd44a` | `thesis: remediate all 34 adversarial-review findings, evidence-backed` — the corrected full-length manuscript, i.e. the rollback baseline for the shortening campaign. Every claim in the shortened thesis must be traceable to evidence present at or before this commit. |
| Comparator frontier | `4babe1c` | `experiment: warm-floor comparator frontier (plan §8.2)` — the frozen-protocol 5-arm comparator experiment (forecast / same-signal reactive / reactive + calibrated warm floor / deployable static / oracle) and its independent adversarial recomputation. |

Everything in S1–S6 is reachable from a checkout at `4babe1c` (which contains
`67bd44a`). Paths below are relative to the repository root.

---

## S1 — Complete results ledger (frozen copy)

**Path:** `progress/results-ledger.md`

The per-result provenance record kept under the standing project habit: for
every result, the exact artifact path, the command/config that produced it, the
UTC date, and which manuscript paragraph/table/figure it *feeds* or
*supersedes*. Entries are append-only and carry supersession explicitly, so a
corrected result never silently overwrites the one it replaced.

Reading order for an auditor: find the manuscript element in Appendix A
`tab:ap-manifest`, then find the ledger entry of the same name here. Entry
headings are `### <short name>  (<UTC date>)`.

The ledger is also the **kernel-collection and campaign history** index — see
`kernel_collection_history.md` in this directory for the phase-by-phase map.

## S2 — Complete forecasting grid

**Paths:** `predictors/` (drivers), `predictors/results/` (grid),
`predictors/results/logs/` (runtime logs), `predictors/results/metrics/`
(derived metrics), `predictors/results_dynamo/` (Dynamo shipped-predictor
registry sweep)

The manuscript reports the decision-relevant slices of the forecasting
evaluation. The archive holds all of it: every model × signal × resolution ×
horizon × quantile cell of the base grid as Parquet, the per-run logs, the
covariate/ablation and quantile-coverage metric files, and the matched-origin
rescore artifact (`predictors/matched_origin_rescore_2026-07-26.json`) that
backs the ARIMA framing.

Provenance run family: `predictors:*` in `provenance.current_runs`
(including `predictors:ewma_*` for the EWMA calibration arm).

Caveat that travels with this item: the evidential unit is the day/episode.
Factorial-cell counts (e.g. "60/60 configurations") are **parameter
robustness**, never a sample size.

## S3 — Full provenance manifest depth

**Paths:** `provenance/SCHEMA_GUIDE.md`, `provenance/schema/` (migrations
`01`–`35` plus the read-only role/optimisation scripts), `provenance/loader/`
(per-kind loaders + `selftest.py`), `provenance/verify_all.sh`,
`provenance/README.md`

The PostgreSQL store (schema `provenance`) that carries run-level identity for
the simulation and forecasting campaigns: run rows with canonical
window/policy/quantile/rho/cold-start/actuation identity, sha256 ingest gates,
the `current_*` views (current-run-only projections), the registered check
suite (`provenance.check_all()`), and the derived-value gates in
`verify_all.sh` that recompute each printed headline ratio from its **raw
operands** rather than checking transcription.

`manifest_full.md` in this directory is the expanded form of the in-thesis
manifest table — the same mapping with the explanatory prose and the workspace
layout that the thin appendix no longer prints.

## S4 — Kernel-collection history

**Path:** `collector_artifacts/` — one directory per collection phase
(`phase0`–`phase9`, `phaseA`–`phaseE`)

The audit trail of the aiconfigurator (AIC) encoder cost-model campaign on
RTX 5090: node discovery, system metadata, registry preflight, smoke and
limited collections, the GEMM/attention full collection, sanity charts,
the two-pool bring-up, and the validation phases A–E. See
`kernel_collection_history.md` for the phase-by-phase description, file
inventory and the corresponding ledger entries.

Upstream: the collected datasets were contributed as draft PR
**ai-dynamo/aiconfigurator #1312** (campaign through commit `b55dd0b7`).

## S5 — Audit trail and comparator frontier

**Paths:** `verification/` (adversarial reviews, resolutions, rerun reports,
scripts), `verification/adversarial_review_resolution.md` (the 34-item
resolution report), `provenance/audit/` (adjudications, delivery ruling,
claim corpus, cross-chapter checks),
`simulation/results/comparator_frontier/` (frozen-protocol comparator
experiment + `adversarial/` independent recomputation)

The record of what was challenged and how it was resolved. **This is the item
that makes the preservation contract auditable**:
`adversarial_review_resolution.md` lists all 34 corrected claims with the
changed text, the evidence recomputed for each, and the final gate outcomes.
Any reader checking whether a shortened passage weakened a corrected claim
should compare against this file, not against an earlier draft.

The comparator frontier (commit `4babe1c`) is filed here rather than under S2
because its value is adjudicative: it answers "was reactive merely denied
standing capacity?" under a single frozen protocol with parameters fixed on
the calibration split and one evaluation pass.

---

## Reproduction quickstart (mirrors Appendix A §"Reproduction quickstart")

1. **Environments.** `uv sync` in `eda/` (GPU EDA and trace conversion); the
   aiconfigurator venv for the cost model and `workload/trace_to_two_pool.py`;
   `ai-dynamo/dynamo/.venv` (source build, 1.3.0) for every `dynamo.replay`
   run. Versions are pinned in Appendix A `tab:ap-env`.
2. **Provenance store.** Apply `provenance/schema/*.sql` in numeric order, then
   run the loaders in `provenance/loader/`; check with
   `python3 provenance/loader/selftest.py`.
3. **Regenerate a result.** Take its row in Appendix A `tab:ap-manifest`, run
   the script column, compare against the artifact column, and read the ledger
   entry (S1) of the same name for the exact command and the manuscript locus
   it feeds.
4. **Verify.** `provenance/verify_all.sh` runs the delivery gates: full build
   (0 errors, 0 undefined references), the rejected-fix audit, the containment
   and methodological-overclaim gates, and the derived-value recomputations.

## Files in this directory

| File | Content |
|---|---|
| `SUPPLEMENTARY.md` | this index (S1–S6, pinned commits, quickstart, displacement record) |
| `manifest_full.md` | expanded reproduction manifest: the in-thesis mapping plus the explanatory prose and workspace layout displaced from the appendix |
| `kernel_collection_history.md` | phase-by-phase AIC collection history, file inventory, ledger cross-index, and the displaced engine-sensitivity detail |

---

## S6 — Content displaced by the 2026-07-26 restructure

The shortening campaign (`thesis_shortening_plan_v3.md`) reduced the manuscript
from 96 numbered pages to the current length by **relocation, deduplication and
tightening — never by deleting evidence**. This section is the complete
displacement record: what left the manuscript, the locus it left, where it now
lives, and which S-item covers it.

Two invariants held throughout and were verified after the fact:

* **No corrected claim was relocated out of the manuscript.** All 34 items of
  `verification/adversarial_review_resolution.md` remain *in* the thesis text,
  preserved in meaning (post-hoc labels, plateau-not-floor, the zero-startup
  reactive label, matched-origin ARIMA framing, onset 6.5 min, dispatch-cap vs
  frames-class, census wording, the 4-of-5 tie). Displacement moved *depth*,
  never a claim, a caveat or a retraction.
* **Nothing displaced left the repository.** Every item below is still on disk
  at the pinned commits above; the four chapter sources retired by the merge
  (`tex/aiconfigurator.tex`, `tex/twopool.tex`, `tex/validation.tex`,
  `tex/baselines.tex`) are recoverable in full from the manuscript baseline
  `67bd44a`.

### S6.1 — Introduction (RQ restructure)

| Displaced | Left from | Now at | S-item |
|---|---|---|---|
| The result previews that used to answer the RQs in the list itself | `tex/intro.tex`, RQ list | Stated once, in the RQ chapter that owns each result (Chapters 4–6) | — (in-manuscript relocation) |
| Old RQ3 "can the system be simulated defensibly enough?" as a *research question* | `tex/intro.tex` | Demoted to methodology (Chapter 3, `cap:metodologia`), which claims less than an RQ | — (in-manuscript relocation) |
| The intro's mirror of the "no fixed quantile materially improves coverage" counterexample list | `tex/intro.tex` | `tex/predictors.tex` `sec:pred-quantiles` (canonical presentation) | — |

### S6.2 — Related work

| Displaced | Left from | Now at | S-item |
|---|---|---|---|
| Per-work descriptors the "which load signal" lens does not use (architecture inventories, secondary mechanisms) | `tex/related.tex`, all six literature sections | The cited works themselves; all 62 citation keys retained | — |
| Three of the four restatements of "these systems do not size a pool on an encoder signal" | `sec:rel-llm`, `sec:rel-mm`, `sec:rel-forecast` | Deduplicated to one, in the "Two gaps" paragraph of `sec:rel-autoscale` | — |

### S6.3 — Methodology & platform (the three-chapter merge)

`tex/metodologia.tex` absorbs the former `aiconfigurator.tex` (AIC cost model),
`twopool.tex` (simulator + fidelity) and `validation.tex` (live-stack anchor).
All 26 of their labels travelled with their content and still resolve.

| Displaced | Left from | Now at | S-item |
|---|---|---|---|
| Full collection narrative: node discovery, registry preflight, smoke and limited collections, per-phase file inventories | former `aiconfigurator.tex` §"Collection and dataset" | `collector_artifacts/phase0`–`phase9`, `phaseA`–`phaseE`; narrated in `kernel_collection_history.md` | S4 |
| Engine-sensitivity depth beyond the appendix table | former `aiconfigurator.tex` | `kernel_collection_history.md` ("displaced engine-sensitivity detail") + `collector_artifacts/phaseE_physical_anchor/` | S4 |
| Per-run simulator configuration listings and the seam-by-seam fidelity walkthrough | former `twopool.tex` | `provenance/` (`current_*` views, run rows carry the canonical configuration identity) and `progress/results-ledger.md` | S3, S1 |
| Live-anchor operational log: per-tick planner traces, worker-manager transcripts, the full divergence write-up | former `validation.tex` | `simulation/results/live51/` (offline twins, `live_runs/`); harness `simulation/live51/` | S1, S3 |
| The four retired chapter sources themselves | `tex/{aiconfigurator,twopool,validation}.tex` (and `tex/baselines.tex`, S6.6) | Recoverable at commit `67bd44a` | S5 |

### S6.4 — RQ1, demand adequacy (EDA)

Three figures were displaced, each because its numbers survive in the body text
or in a retained table. **All three files remain in `figuras/eda/` and
`figuras_new/`; no claim was dropped.**

| Displaced figure | Number that carries it in the manuscript | S-item |
|---|---|---|
| `eda_l_request_clusters` | Table `tab:eda-archetypes` (the four archetypes, with the frames-class overlap note) | S1 |
| `eda_e_arrival_process` | §"Temporal structure": CV 1.55, Fano 1.8 → 938 | S1 |
| `eda_d_acf` | Table `tab:eda-persistence`, half-life column (69 min images vs 9 min requests) | S1 |

### S6.5 — RQ2, forecastability

Displaced to the complete forecasting grid (S2), all of it already archived as
Parquet plus derived metric files:

* the full model × signal × resolution × horizon × quantile grid (the chapter
  reports only the decision-relevant slices);
* the per-signal point-MAE tables;
* the per-decision GPU-time cost of each forecaster;
* the per-model context caps;
* the per-component ranges of the additive decomposition.

Paths: `predictors/results/` (grid), `predictors/results/metrics/` (derived),
`predictors/results/logs/`, `predictors/results_dynamo/` (shipped-predictor
sweep). Retained in the manuscript: the coverage table `tab:pred-coverage`, the
matched-origin ARIMA framing, and the retractability statement.

### S6.6 — RQ3, control payoff (baselines merged in)

`tex/closedloop.tex` absorbs the former `baselines.tex`; its nine labels
(`cap:baselines`, `sec:base-*`, `tab:base-*`) travelled with their content.

| Displaced | Left from | Now at | S-item |
|---|---|---|---|
| Full TTFT distributions (p50 / p90 / max) behind the language-pool ledger | `tab:cl-ledger-llm` caption states the displacement | `provenance` views `v_pool_latency`, `v_joint_e2e`; `simulation/results/llm_week/` | S3, S1 |
| The 101-point static grid, cell by cell | `sec:base-static` (which keeps the effective optima and the burst5 `C*` 16→8 supersession) | `simulation/results/grid/` + `verification/rerun-stability-e2e.md` | S1, S5 |
| The full warm-floor family `M = 1…32`, per-member per-episode | `sec:cl-aggregate` (which keeps `M=1…6`, the `M≥9` plateau and the envelope figure) | `simulation/results/comparator_frontier/eval_family/`, `frontier_summary.json` | S5 |
| Per-fold and per-combiner detail of the hybrid sweep | `sec:cl-aggregate` (which keeps F2/F6 and the post-hoc label) | `simulation/results/encoder_hybrid/{folds,combos}/` | S1 |

### S6.7 — Appendix A (39 pp → thin manifest)

| Displaced | Left from | Now at | S-item |
|---|---|---|---|
| Full manifest prose, file-level artifact lists, row-level caveats, workspace layout | `tex/apendice.tex` §"Figure and table manifest" | `supplementary/manifest_full.md` | S3 |
| Environment narrative and the kernel-collection history | `tex/apendice.tex` §"Environment" | `supplementary/kernel_collection_history.md` | S4 |
| Ecosystem/tooling inventory (`tex/apendice_ecosystem.tex`, labels `app:ecosystem`, `tab:app-ecosystem`) | dropped from the build; no manuscript element references it | still on disk in `tex/`, and recoverable at `67bd44a` | S5 |
| The reproduction quickstart's step-by-step expansion | `tex/apendice.tex` | mirrored in "Reproduction quickstart" above, expanded in `manifest_full.md` | S3 |

**Retained in the manuscript by design** (plan §3, adversarial-review Finding 4):
one pointer row per numbered figure and table (`tab:ap-manifest`), the
environment table (`tab:ap-env`), the reproduction quickstart, and this
archive's index (`tab:ap-supp`).

### S6.8 — Reading the pre-restructure manuscript pointers in the provenance artifacts

`simulation/results/comparator_frontier/frontier_summary.json` (its
`source_ref` fields and caveat prose), the comments and `source_ref` values in
`provenance/schema/{22,23,25,26,33}*.sql`, and the module docstrings of
`provenance/loader/{main,load_live,load_group_c,load_collector_silicon}.py`
cite manuscript loci of the form `tex/{twopool,baselines,validation,
aiconfigurator}.tex:NNN`. Those four sources were retired by the merge on
2026-07-26 (S6.3, S6.6). **The citations are correct as historical records and
were deliberately not rewritten** — they date the assertion they carry and
resolve against the manuscript baseline `67bd44a`. No delivery gate reads them
(`provenance.check_definition.sql_text` references no `tex/` path). To follow
one forward, map the file to its absorbing chapter — `aiconfigurator`,
`twopool`, `validation` → `tex/metodologia.tex`; `baselines` →
`tex/closedloop.tex` — and find the label named in the same sentence; every
label of the four survived the move.

---

## S7 — Clean-checkout reproduction test (plan §8.8-1)

**Path:** `verification/repro_clean_checkout.sh` (runner) and
`verification/repro_clean_checkout_report.md` (latest report).

Independent reproduction of headline results from a **detached clean worktree
at HEAD**, no live-tree state: (1) the §8.2 comparator frontier recomputed
cell-by-cell (313 cells) from the tracked raw run outputs and self-verified
against the tracked `frontier_summary.json` (stats, calibration selection,
calibration table, summary link); (2) the request-linked composed nine-cell
join, first from plain tracked files only (five cells reproduce and equal the
committed artifact; the boundary is recorded exactly), then (3) with the four
archive-dependent cells' replay inputs inflated from their **tracked
`.jsonl.zst` archives inside the checkout** (`zstd -d`), after which the
regenerated nine-cell artifact must be **byte-identical** to the committed
object. The bulky replay inputs (1.8 GB plain) are therefore carried by the
repository itself at ~192 MB compressed; this archive keeps its pointer-only
contract.
