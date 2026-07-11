# Verification: ITL estimand mismatch (Task 1) + TimesFM mean-vs-p50 head (Task 2)

Date: 2026-07-11. Recomputed from artifacts with `/home/gio/tese/eda/.venv/bin/python`.
No `.tex` or existing code/artifact was modified. This file only records findings +
proposed edits.

**Bottom line: both reviewers are correct.**
- Task 1: the offline ITL column (5.3 / 160.3 ms) is a *pooled per-token-gap* p99, which is a
  different estimand from aiperf's live ITL (per-request average ITL, then p99). The
  like-for-like offline values are **9.72 (forecast) and 152.68 (reactive)** — exactly the
  reviewer's numbers. Both verdicts (forecast PASS below the 100 ms sub-bound; reactive FAIL
  above 100 ms) still hold, and correcting the column *improves* the live-vs-offline agreement.
- Task 2: under a common p50 head, TimesFM's ctx@1-minute WAPE rises from 43.22% (mean head) to
  43.90% (median), and Toto-2 (43.26%) takes the cell. **TimesFM wins 0 of 20 cells at common
  p50** (it won exactly 1 at native-point). The specific "TimesFM takes the 1-minute context
  column" clause does not survive; the broader "which model wins is resolution-dependent"
  (Chronos coarse / Toto fine) claim does survive.

---

## TASK 1 — Live vs offline ITL estimand mismatch (validation.tex:64-70, tab:val-anchor)

### Artifacts used
- Live (aiperf): `simulation/results/live51/live_runs/live_fc/profile_export_aiperf.json`,
  `.../live_re/profile_export_aiperf.json` (aiperf 0.11.0, schema 1.3).
- Offline twins (dynamo replay, budget-capped at 4 TP2 = the table's "budget-matched" column):
  `simulation/results/live51/twin_fc_p90_cap4.report.json`,
  `simulation/results/live51/twin_re_cap4.report.json`.

### What the table currently reports (confirmed byte-for-byte against the artifacts)
| Policy | Metric | Live | Offline twin (table) | source field |
|---|---|---|---|---|
| Forecast | TTFT p99 (ms) | 695 | 651 | aiperf ttft p99 = 695.16 ; offline `p99_ttft_ms` = 651.14 |
| Forecast | ITL p99 (ms) | 11.5 | **5.3** | aiperf itl p99 = 11.470 ; offline **`p99_itl_ms` = 5.287** |
| Forecast | replica-seconds | 6,063 | 6,400 | offline `decode_worker_seconds` = 6399.81 |
| Reactive | TTFT p99 (ms) | 3,531 | 3,495 | aiperf ttft p99 = 3531.45 ; offline `p99_ttft_ms` = 3494.73 |
| Reactive | ITL p99 (ms) | 150.7 | **160.3** | aiperf itl p99 = 150.745 ; offline **`p99_itl_ms` = 160.260** |
| Reactive | replica-seconds | 1,799 | 1,948 | offline `decode_worker_seconds` = 1947.67 |

So the offline ITL column is `p99_itl_ms` from the replay report.

### How the LIVE ITL p99 is computed (aiperf) — per-request, then p99
`ai-dynamo/aiperf/src/aiperf/metrics/types/inter_token_latency_metric.py:16-52`:

```
class InterTokenLatencyMetric(BaseRecordMetric[float]):
    # Inter Token Latency = (Request Latency - Time to First Token) / (Output Sequence Length - 1)
```

It is a `BaseRecordMetric`: **one scalar per request** = that request's *average* inter-token
gap. The reported `inter_token_latency.p99` is the p99 taken **across requests**. Corroborated
by the artifact: `inter_token_latency.count` = 3057 (≈ #requests with osl≥2), whereas the
separate per-chunk metric `inter_chunk_latency.count` = 465083 (per-token). So live ITL =
"per-request mean ITL → p99 across requests".

### How the OFFLINE report computes `itl_ms` vs `tpot_ms` — pooled gaps vs per-request
`ai-dynamo/dynamo/lib/mocker/src/replay/collector.rs`:
- `mean_tpot_ms()` (L523-532): `(last_token_ms - first_token_ms)/(num_tokens-1)` — one value per
  request. Pushed into the **`tpots`** vector (L843-844) → the report's **`tpot` distribution**
  (`p99_tpot_ms`).
- `itls_ms()` (L534-538): `windows(2)` token-to-token diffs — **many values per request**.
  Pushed into the **`itls`** vector (L845-849) → the report's **`itl` distribution**
  (`p99_itl_ms`), a *pooled per-token-gap* distribution.
- Per-request emitted record (L395-398, L953): field `itl_ms = stats.mean_tpot_ms()`, with the
  comment: *"Inter-token latency for this request... **Matches AIPerf's `inter_token_latency`
  field — one scalar per request**."*
- SLA gate (L455-475): `avg_itl = (e2e_ms − ttft_ms)/(output_length − 1)` — the DGDR "ITL" SLA is
  evaluated on the **per-request average**, i.e. tpot.

Independently corroborated in
`ai-dynamo/dynamo/components/src/dynamo/profiler/utils/replay_optimize/specs.py:247-269`, which
maps the SLA/DGDR name `itl` → report field `mean_tpot_ms` and `p95Itl` → `p95_tpot_ms`, with the
comment *"`itl` is the DGDR-native name for what the Rust runner reports as `mean_tpot_ms`
(inter-token latency == time-per-output-token)."*

**Conclusion: aiperf `inter_token_latency` is definitionally identical to dynamo-replay `tpot`
(both = `(e2e−ttft)/(osl−1)` per request). The like-for-like offline field is `p99_tpot_ms`, NOT
`p99_itl_ms`.**

### Recomputed like-for-like offline ITL p99 (same estimand as aiperf)
Directly from the twin report JSONs:

| | Live aiperf `inter_token_latency` p99 | Offline `p99_tpot_ms` (like-for-like) | Offline `p99_itl_ms` (table, pooled) |
|---|---|---|---|
| Forecast | 11.470 | **9.718** | 5.287 |
| Reactive | 150.745 | **152.681** | 160.260 |

The reviewer's **9.72 (forecast) and 152.68 (reactive) are exactly `p99_tpot_ms`** — confirmed.
The current table is **not** comparing like-for-like: it puts a per-request-mean p99 (live)
against a pooled-token-gap p99 (offline).

### Corrected table cells and deltas
Δ conventions follow the existing table (forecast ITL in absolute ms; reactive ITL in %;
Δ% = (live−offline)/offline, matching the +6.8% / +1.0% TTFT rows):

| Policy | Metric | Live | Offline (corrected) | Δ (corrected) | Δ (current, wrong) |
|---|---|---|---|---|---|
| Forecast | ITL p99 (ms) | 11.5 | **9.7** | **+1.8 ms** | +6.2 ms |
| Reactive | ITL p99 (ms) | 150.7 | **152.7** | **−1.3%** | −6.0% |

Correcting the estimand **strengthens** the chapter's thesis (live and offline agree): forecast
live/offline goes from 11.5-vs-5.3 (looked ~2.2× worse live) to 11.5-vs-9.7 (~1.18×); reactive
tightens from −6.0% to −1.3%, matching the "within 1%" agreement already claimed for TTFT.

### Verdict check (must still hold) — HOLDS in both directions
- Forecast: ITL p99 = 9.72 ms < 100 ms sub-bound → **PASS** (TTFT 651 < 1000 also passes). Holds
  under either estimand (pooled 5.3 also < 100).
- Reactive: ITL p99 = 152.68 ms > 100 ms bound → **FAIL / above bound** (TTFT 3495 > 1000 also
  fails). Holds under either estimand (pooled 160.3 also > 100).

### Proposed tex fix — Option 1 (recommended: recompute offline column to like-for-like tpot)
Cleanest, keeps a single honest estimand in the headline table, and improves the agreement story.

`tex/validation.tex` line 65:
```
- & ITL p99 (ms) & 11.5 & 5.3 & $+6.2$\,ms \\
+ & ITL p99 (ms) & 11.5 & 9.7 & $+1.8$\,ms \\
```
`tex/validation.tex` line 70:
```
- & ITL p99 (ms) & 150.7 & 160.3 & $-6.0\%$ \\
+ & ITL p99 (ms) & 150.7 & 152.7 & $-1.3\%$ \\
```
Add one clause to the caption of `tab:val-anchor` (after the SLA parenthetical, line 55-57), so
the estimand is explicit:
```
+ ITL p99 is the per-request average inter-token latency
+ ($(\mathrm{e2e}-\mathrm{TTFT})/(\mathrm{osl}-1)$), aiperf's
+ \texttt{inter\_token\_latency}, computed identically live and offline
+ (the replay report's per-request \texttt{tpot} distribution).
```
Then update the two propagated copies in `tex/intro.tex` lines 502-504:
```
- sub-bound for the forecast policy, 11.5 versus
- 5.3\,ms, and \emph{above} the \SI{100}{\milli\second} bound for the
- reactive policy, 150.7 versus 160.3\,ms) and provisioned replica-time
+ sub-bound for the forecast policy, 11.5 versus
+ 9.7\,ms, and \emph{above} the \SI{100}{\milli\second} bound for the
+ reactive policy, 150.7 versus 152.7\,ms) and provisioned replica-time
```
`tex/conclusion.tex` line 47-48 states only the verdict directions ("forecast sub-bound, reactive
above bound"), no numbers — no change needed; the verdicts still hold.

### Proposed tex fix — Option 2 (footnote only, weaker)
Keep 5.3 / 160.3 but add a footnote to `tab:val-anchor`: the live ITL p99 is aiperf's
per-request average ITL while the offline 5.3/160.3 is the pooled per-token-gap p99; the
estimand-matched offline values are 9.7 and 152.7 ms (replay `p99_tpot_ms`), and the verdicts are
unchanged. Not recommended — it leaves an apples-to-oranges pair in the headline numbers.

---

## TASK 2 — TimesFM mean head vs Chronos/Toto medians (predictors.tex:79-84, tab:pred-wape)

### Artifacts used
`predictors/results/metrics/metrics_overall.parquet` (3200 rows; produced by
`predictors/precision.py` over the benchmark parquets). Columns:
`model, mode, span, resolution, variate, candidate, mae, rmse, wape`. `candidate` ∈
{`point`, `p10`…`p90`}; `variate` = req/img/ctx/gen; span=`common` is the cross-model span.

### Head verification (median-point identity)
For Chronos-2, Toto-2 and the baselines, `point` WAPE == `p50` WAPE exactly in every cell
(diff = 0.000), confirming their point forecast IS the median. For **TimesFM only**, `point`
(mean head) ≠ `p50` (e.g. ctx@1min: point 43.224 vs p50 43.897, diff −0.673). This is exactly
the head asymmetry the reviewer flags and that predictors.tex:79-81 already discloses.

### 1-minute context column, common span, overall WAPE (%)
Ranking among the five foundation configs:

| config | native point (table) | common p50 |
|---|---|---|
| TimesFM | **43.224** (bold win) | 43.897 |
| Toto-2 | 43.260 | **43.260** |
| Toto-2 (cov) | 43.293 | 43.293 |
| Chronos-2 | 43.364 | 43.364 |
| Chronos-2 (cov) | 43.437 | 43.437 |

- Under native point (mean head), TimesFM wins by **0.036** WAPE points over Toto-2.
- Under **common p50**, TimesFM (43.90) is the **worst** of the five for this cell; **Toto-2
  (43.26) takes it.** The displayed 1-minute context-column win vanishes. **Reviewer correct.**

### Full 20-cell winner tally (common span, overall WAPE), five foundation configs
Native point (as in the current table):
`Toto-2(cov) 11, Toto-2 4, Chronos-2 3, Chronos-2(cov) 1, TimesFM 1` → Toto configs 15/20;
the five non-Toto cells are 4 Chronos + 1 TimesFM (ctx@1min). Matches the tex prose exactly.

Common p50 (all three medians):
`Toto-2(cov) 11, Toto-2 5, Chronos-2 3, Chronos-2(cov) 1, TimesFM 0` → **TimesFM wins nothing**;
its ctx@1min cell transfers to Toto-2. Every other winner is unchanged.

TimesFM point-vs-p50, all shown cells (for a possible Option B recompute):

| res | req pt→p50 | img pt→p50 | ctx pt→p50 | gen pt→p50 |
|---|---|---|---|---|
| 1min | 33.44→33.57 | 53.39→53.38 | 43.22→43.90 | 37.80→37.62 |
| 1s | 66.28→65.15 | 120.47→102.91 | 95.84→87.36 | 89.51→83.33 |

(TimesFM wins no 1-second cell under either head, so those changes are cosmetic.)

### Does "which model wins is resolution-dependent" survive? — YES (narrowly)
Under common p50 the winner still shifts with resolution: Chronos-2 takes coarse cells
(req@1min, req@45s, ctx@45s) and Toto/Toto(cov) sweep the fine bins (all of 30s and finer). The
Chronos-coarse / Toto-fine structure is intact. Only the **TimesFM sub-clause** ("and TimesFM the
fifth (the 1-minute context column)") is head-dependent and fails at common p50. The chapter's
own "three-way tie / wins decided by ≤0.1 WAPE point over 167 origins, below sampling
variability" reading (predictors.tex:173-177) is *reinforced*: the TimesFM win was a 0.036-point,
head-dependent artifact — precisely the noise-level effect the thesis already disclaims. This is
also consistent with predictors.tex:279-289, which already reports TimesFM's mean head is beaten
in 18/20 cells by a below-median quantile.

### Proposed tex fix — Option A (recommended: keep native-point table, add common-p50 caveat)
The per-model head is already stated (predictors.tex:79-81). Amend the winner sentence at
`tex/predictors.tex` lines 170-172. Current:
> Chronos-2 takes four of the five remaining coarse-bin cells and TimesFM the fifth (the
> \SI{1}{\minute} context column).

Append a caveat (or footnote) immediately after it:
```
+ (TimesFM's lone column win is an artifact of its mean point head: under a
+ common p50 head its \SI{1}{\minute} context WAPE is 43.9\% and Toto-2 (43.3\%)
+ takes that cell, so no column win survives for TimesFM --- reinforcing the
+ noise-level reading below.)
```
This keeps the table faithful to each model's shipped point forecast (mean for TimesFM, median
for the others) while removing any implication that the ctx@1min result is a robust TimesFM win.

### Proposed tex fix — Option B (recompute the TimesFM row at common p50)
If a strictly head-matched table is preferred, replace the TimesFM row of `tab:pred-wape`
(line 129) with p50 values and move the ctx@1min bold to Toto-2:
```
- TimesFM         & 33.4 & 53.4 & \textbf{43.2} & 37.8 & & 66.3 & 120.5 & 95.8 & 89.5 \\
+ TimesFM         & 33.6 & 53.4 & 43.9 & 37.6 & & 65.2 & 102.9 & 87.4 & 83.3 \\
```
and change the ctx@1min bold from TimesFM to Toto-2 (43.3), plus rewrite the winner sentence to
"...Chronos-2 takes four of the five remaining coarse-bin cells and Toto-2 the fifth." Less
faithful (it hides TimesFM's actual shipped mean-head output), so Option A is preferred; if
Option B is taken, add a note that the table is computed at a common p50 head.

---

## Reproduction commands
```
# Task 1 live values
/home/gio/tese/eda/.venv/bin/python -c "import json;d=json.load(open('simulation/results/live51/live_runs/live_fc/profile_export_aiperf.json'));print(d['inter_token_latency']['p99'], d['inter_token_latency']['count'], d['inter_chunk_latency']['count'])"
# Task 1 offline like-for-like (tpot) vs table (itl)
/home/gio/tese/eda/.venv/bin/python -c "import json;[print(f, json.load(open(f'simulation/results/live51/{f}'))['p99_tpot_ms'], json.load(open(f'simulation/results/live51/{f}'))['p99_itl_ms']) for f in ['twin_fc_p90_cap4.report.json','twin_re_cap4.report.json']]"
# Task 2
/home/gio/tese/eda/.venv/bin/python -c "import pandas as pd;d=pd.read_parquet('predictors/results/metrics/metrics_overall.parquet');d=d[(d.span=='common')&(d.resolution=='1min')&(d.variate=='ctx')];print(d[d.candidate.isin(['point','p50'])][['model','mode','candidate','wape']].to_string())"
```
