# Independent re-derivation of the three proposed thesis defects

Source under review: `defense/anim/data/_final/THESIS-TEXT-DEFECTS.md`
Method: every number below re-read from the artifact files and the `provenance` DB. None of the
delivery's arithmetic was taken on trust. Prior audit `provenance/audit/ADJUDICATION.md` §0.4
(44 rejected fixes) checked for collisions on every proposed remediation.

Ingest sanity: `provenance.ingest_log` shows the a16/g2/g3_32b/g4/g6 load completed
2026-07-20 01:05–04:17 UTC. `sweep_run`/`sweep_point`/`sweep_curve` are populated
(1 run / 30 points / 6 curves). Nothing needed here is missing. One naming note: the runs
ADJUDICATION R13/R15 call `misc:235b_tp8_%` are now keyed `g3_32b:235b_tp8_%`
(`provenance.runs.experiment = 'g3_32b'`, `source_path` under `defense/anim/data/g3_32b/reports/`).
Same artifacts, renamed at ingest.

---

## The runtime fingerprint (needed by Defects 1 and 2)

Two report schemas exist in this corpus, and the schema **is** the runtime tag:

| schema | extra keys | runtime |
|---|---|---|
| "old" (~2.81–2.85 kB) | — | **wheel** build |
| "EXT" (~3.04–3.08 kB) | `gpu_hours`, `decode_worker_seconds`, `prefill_worker_seconds`, `decode_gpus_per_worker`, `prefill_gpus_per_worker`, `first_admission_prefix_cache_reused_ratio` | **source** build |

Independent corroboration, not just the key set: for the AIC-timed 8B on `head2k`, the wheel runs
carry `max_ttft_ms ≈ 7.6 s` at every speedup while the source runs carry `≈ 4.52–4.57 s`. Both
`simulation/results/srcbuild/*.json` (the R4-blessed files) and every
`defense/anim/data/g3_32b/reports/*.json` are EXT. The polynomial runs are unaffected by the
artifact (poly `max_ttft_ms` at s=1 is bit-identical, 2539.913656001503, between
`srcbuild/llm_head2k_poly_src.json` and `sweeps/reports/llm_head2k_poly_s1.report.json`) —
consistent with the stated mechanism, a slow per-request *AIC* callback.

### 8B-TP1, `head2k`, AIC timing: wheel vs source, all speedups

wheel = `simulation/results/sweeps/reports/llm_head2k_aic_s{N}.report.json`
source = `defense/anim/data/g3_32b/reports/8b_tp1_s{N}.report.json`

| s | TTFT p99 wheel | TTFT p99 source | Δ(src−wheel)/wheel | max TTFT wheel | max TTFT source | ITL p99 wheel | ITL p99 source |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 306.73 | 307.36 | **+0.2 %** | 7598.10 | 4517.57 | 22.87 | 22.62 |
| 2 | 418.23 | 394.30 | −5.7 % | 7608.50 | 4528.09 | 67.33 | 59.43 |
| 3 | 554.02 | 552.48 | −0.3 % | **4543.39** | **4543.39** | 109.51 | 108.48 |
| 4 | 882.08 | 782.68 | **−11.3 %** | 7650.62 | 4567.75 | 210.63 | 206.47 |
| 16 | 40163.45 | 49034.47 | **+22.1 %** | 41617.14 | 49738.47 | 588.58 | 228.78 |

The delivery's percentages are computed as (source − wheel)/wheel throughout and **all four check
out exactly**. (Stated the other way — source as denominator — s=4 is wheel +12.7 % over source.)
Its qualitative reading, that divergence grows with distance from the knee, is also right, with the
s=3 row as the sole exception — and that exception is explained by Defect 2.

---

## DEFECT 1 — twopool.tex:78 "against the 8B's 307 / 882"

### Verdict: **PARTIALLY CONFIRMED — but the delivery's core diagnosis is REFUTED.**

The delivery asserts the sentence "mixes two runtimes in one comparison". It does not. I checked the
235B side, which the delivery never did.

**Every number in the Family-transfer paragraph (twopool.tex:74–82) is wheel-runtime, on both arms.**

`simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` — all three are **old schema**, written
2026-07-06 21:52 alongside the wheel sweeps, and carry the wheel `max_ttft_ms` signature
(7712 / 8084 ms).

| quantity at :77–81 | published | wheel value | source value (`g3_32b`) |
|---|---:|---:|---:|
| 235B TTFT p99 @1× | 398 | 397.68 | 387.37 |
| 235B TTFT p99 @4× | 1,402 | 1401.71 | **20032.82** |
| 8B TTFT p99 @1× | 307 | 306.73 | 307.36 |
| 8B TTFT p99 @4× | 882 | 882.08 | 782.68 |
| 235B / 8B mean TPOT | 14.9 / 7.9 | 14.94 / 7.85 | 14.70 / 7.76 |
| 235B / 8B out tok/s/user | 87 / 142 | 86.94 / 141.75 | 87.19 / 141.96 |
| 235B ITL p99 @1× | 87.7 | 87.72 | 86.15 |

So the paragraph is **internally consistent**: a wheel-vs-wheel spot-check on one window and one
topology. The 8B's "307" coincides with the srcbuild value (307.36 → 307) only because the two
runtimes agree to 0.2 % at s=1; it is not evidence of mixing. "Requote 882 from source" — the
delivery's first proposed remediation — would *create* the mixing defect it claims to fix, by putting
a source 8B number opposite a wheel 235B number. **Do not do it.**

### What IS defective — two things, one of them much worse than what was reported

**(1a) The :69 parenthetical over-generalises.** "inflating the *extreme* tail only (identical p99…)"
is true at s=1 (0.2 %) and, coincidentally, at s=3 (0.3 %, and that row is a source run — see Defect
2). It is false everywhere else: −5.7 % at s=2, −11.3 % at s=4, +22.1 % TTFT and −61.1 % ITL at s=16.
The stated scope ("only") is not supported.

**(1b) The 4× spot-check column is not defensible against the runtime the chapter claims to use.**
This is the real finding and the delivery missed it. At 4× the trace rate the source build gives the
235B a TTFT p99 of **20,032.8 ms** against the published **1,402 ms** — a factor of 14.3. Both runs
complete all 2,000 requests on identical token totals with comparable e2e p99 (72.7 s wheel vs 69.0 s
source) and duration (195 s vs 200 s), so this is not a failed run: it is a systematic TTFT
*accounting* divergence under heavy queueing, not the "extreme tail only" effect the text describes.
Quoting 1,402 ms eleven lines after "These AIC numbers come from the source-built runtime" is
materially misleading, and it understates the flagship's degradation — the direction that flatters
the number.

At 1×, by contrast, the two runtimes agree to 2.7 % on the 235B and 0.2 % on the 8B. The 1× pair is
safe on either runtime.

### Collisions with rejected fixes

- **R4/R12 (`tab:sim-poly-aic`, twopool.tex:103–106):** no collision. That table is srcbuild and I
  confirm its cells independently — `srcbuild/llm_head2k_aic_src.json` gives mean TTFT 68.23,
  p99 307.36, max 4517.57, 141.95 tok/s/user, matching `g3_32b/reports/8b_tp1_s1.report.json`
  (68.21 / 307.36 / 4517.57 / 141.96). **Untouched by every edit below.**
- **R13 (235B knee is measured, do not hedge):** no collision — nothing below hedges the knee. One
  correction for the record: R13 cites `misc:235b_tp8_s2` ITL p99 = 213.044 ms; the current artifact
  (`g3_32b/reports/235b_tp8_s2.report.json`, post-`--force` re-run) reads **210.588 ms**. R13's cited
  value is stale by 1.2 %. Its conclusion is unaffected — 210.6 ms is still far over the 100 ms bound,
  and the source-build fine sweep brackets the crossing at s = 1.1351.
- **R26 (32B not priced in the manuscript):** *adjacent, and it constrains the remedy.* The
  source-build 235B/8B numbers used above live in `g3_32b/`, created 2026-07-19/20 — post-manuscript
  defence material by R26's own reasoning. They are admissible as **evidence that a published number
  is unsafe**, but substituting them into the manuscript would import post-manuscript material into
  a chapter R26 has already ruled on. Hence the remedy below **deletes** the unsafe column rather
  than replacing its values.

### Exact replacement text

**Edit 1 — twopool.tex:67–72.** Replace:

```
run in-core (Rust) in microseconds. An earlier wheel-based runtime ran them
as per-request Python callbacks whose wall-time leaked into the simulated
clock, inflating the \emph{extreme} tail only (identical p99, maximum TTFT
7.6 vs.\ 4.5~s on identical perf data): an instrumentation artifact to
guard against when a timing hook is slower than the events it
prices.
```

with:

```
run in-core (Rust) in microseconds. An earlier wheel-based runtime ran them
as per-request Python callbacks whose wall-time leaked into the simulated
clock. At the trace's own rate that leak lands almost entirely on the
\emph{extreme} tail --- maximum TTFT 7.6 vs.\ 4.5~s on identical perf data,
against a TTFT p99 that agrees to \SI{0.2}{\percent} --- but it is not
benign once the pool queues: by $s{=}4$ the two runtimes' TTFT p99 differ by
\SI{11}{\percent}. An instrumentation artifact to guard against when a
timing hook is slower than the events it prices, and a reason to read
cross-runtime agreement only at the point where it was demonstrated.
```

**Edit 2 — twopool.tex:76–79.** Replace:

```
Qwen3-VL-235B-A22B at TP8 (MoE-TP~8), on the same shipped H100 data, window,
and topology: TTFT p99 of 398 / 1{,}402~ms at $1\times$/$4\times$ the trace
rate against the 8B's 307 / 882, with $2\times$ the decode latency
throughout (TPOT 14.9 vs.\ 7.9~ms; 87 vs.\ 142 output tok/s per user).
```

with:

```
Qwen3-VL-235B-A22B at TP8 (MoE-TP~8), on the same shipped H100 data, window,
and topology: TTFT p99 of \SI{398}{\milli\second} at the trace's own rate
against the 8B's \SI{307}{\milli\second}, with $2\times$ the decode latency
throughout (TPOT 14.9 vs.\ 7.9~ms; 87 vs.\ 142 output tok/s per user).
```

Rationale: this deletes only the $4\times$ column (the 1,402 / 882 pair), which is the sole part of
the paragraph that does not survive a source-build check. The $1\times$ figures agree across
runtimes to $\leq$ 2.7 % and stand as written. Nothing else in the paragraph changes; the knee
argument at :80–82, which carries the degradation story, is untouched, so no argumentative content
is lost. No renumbering, no macro changes, no effect on `tab:sim-poly-aic` or `tab:sim-knees`.

---

## DEFECT 2 — `simulation/results/sweeps/reports/` is runtime-mixed

### Verdict: **CONFIRMED** (conclusion right; the delivery's stated evidence is wrong and its scope is too narrow).

### What the files actually say

`stat` + key sets over all 19 reports:

| file | mtime | bytes | schema | runtime |
|---|---|---:|---|---|
| `llm_head2k_aic_s1` | 07-06 21:09 | 2813 | old | wheel |
| `llm_head2k_aic_s2` | 07-07 05:35 | 2812 | old | wheel |
| `llm_head2k_aic_s4` | 07-06 21:09 | 2817 | old | wheel |
| `llm_head2k_aic_s16` | 07-06 21:10 | 2816 | old | wheel |
| **`llm_head2k_aic_s3`** | **07-08 11:05** | **3057** | **EXT** | **source** |
| `llm_head2k_poly_s{1,2,3,4,8,16,32}` | 07-06 21:07, 07-08 11:05 (s3) | 2813–2821 | old | wheel (poly, artifact-immune) |
| `llm_burst1_poly_s{1,2,4,8}` | 07-06 21:10–21:12 | 2833–2846 | old | wheel |
| **`llm_burst1_aic_s1`** | **07-08 11:04** | **3055** | **EXT** | **source** |
| **`llm_burst1_aic_s2`** | **07-08 11:05** | **3078** | **EXT** | **source** |
| **`llm_burst1_aic_tp2_s1`** | **07-08 11:06** | **3055** | **EXT** | **source** |

So the mixture is **four** source files among the AIC runs, not one. The delivery caught only
`llm_head2k_aic_s3` and missed all three `llm_burst1_aic_*`. Note also that `llm_head2k_poly_s3`
was written on 07-08 with the **old** schema — so mtime alone is not the discriminator, contrary to
the delivery's framing ("s=3 written 2026-07-08 with a different schema, while s=1/2/4/16 on
07-06..07").

**The delivery's stated evidence is factually wrong.** It claims `llm_head2k_aic_s3` "carries
max_ttft 4543.39 ms — identical to the source build". The source build
(`srcbuild/llm_head2k_aic_src.json`) has `max_ttft_ms = 4517.568278000195`, not 4543.39. The correct
identification is a different one: 4543.39 matches `g3_32b/reports/8b_tp1_s3.report.json`
**to the digit**, and a full field-by-field diff of those two files shows an identical key set
(74 keys), 29 bit-identical fields, and the remaining 45 differing by ≤0.3 % — the residual
nondeterminism of two runs of the *same* source binary. The delivery reached the right conclusion
from the wrong comparison.

### Impact — which published numbers and which DB rows

**DB.** All 19 files are ingested under the single `sweep_run_id = 'sweeps:summary'`
(`generated_utc 2026-07-08 14:05:08+00`, `source_path .../sweeps/summary.json`), 30 `sweep_point`
rows, 6 `sweep_curve` rows. Neither table carries a runtime column, so:

- `sweep_point` — 4 of 18 populated rows are source-runtime: `(llm, head2k, aic, s=3)` and
  `(llm, burst1, aic, s∈{1,2})` plus the tp2 point (which is not in `sweep_point`; it reaches the
  thesis only through the `tab:sim-knees` caption). The 12 vision rows are unpopulated.
- `sweep_curve` — **`(llm, head2k, aic)` is the one curve that crosses the boundary**: its
  `speedups = {1,2,3,4,16}` / `metric_ms = {306.729, 418.226, 554.017, 882.077, 40163.453}` mix four
  wheel points with one source point at s=3.
  `(llm, burst1, aic)` is homogeneous **source** (s=1,2 both EXT). The two poly curves are
  homogeneous wheel and artifact-immune.
- `sweep_run`, `sweep_window` — no per-point content; unaffected.

**`tab:sim-knees` (twopool.tex:269–284) — affected, and mixed row-to-row.** Exactly how:

| row | published | runtime of those cells |
|---|---|---|
| LLM / AIC, steady, `$s{=}2$ (ITL-bound)`, `$307 \to 418$` | 306.73 → 418.23 | **wheel** |
| LLM / AIC, burst, `none: over at $s{=}1$`, `$1{,}868$` | 1868.03 | **source** (`llm_burst1_aic_s1`, EXT) |
| caption, "a TP2×2 shape passes the same window at \SI{748}{\milli\second}" | 748.39 | **source** (`llm_burst1_aic_tp2_s1`, EXT) |
| LLM / poly rows | — | wheel, artifact-immune |

So the table's two AIC rows come from different runtimes. That is a provenance defect in its own
right, though not an arithmetic one.

**Does a published knee cross the boundary? Yes — and the knee survives it.** The steady AIC knee is
`$s{=}2$` because s=3 is the first point over a bound, and the binding bound is ITL p99 > 100 ms
(`sweep_run.thr_itl_p99_ms = 100`; `sweep_curve.knee_is_itl_bound = t`,
`first_over_speedup = 3`). The s=3 point that decides this is the **source** run. Checked both ways:

- ingested (source) value 109.51 ms > 100 → s=3 fails → knee = 2
- true wheel-runtime counterpart is unavailable, but the source rerun gives 108.48 ms > 100 → fails
- s=2 passes under either runtime (67.33 wheel / 59.43 source, both < 100)
- the independent source-build fine sweep puts the 8B-TP1 knee at **s = 2.8158** — between 2 and 3,
  exactly as the coarse grid reports

**The knee is robust.** No published knee changes. The `$307 \to 418$` cells are unchanged (both
wheel). The 554.02 / 4543.39 s=3 point is not printed anywhere in the manuscript; it appears only as
the point that sets the knee.

### Collisions

None. `tab:sim-poly-aic` (R4/R12) is sourced from `srcbuild/`, not from this directory, and is not
touched. Nothing here hedges the 235B knee (R13) or the 32B status (R26).

### Exact replacement text

**No numeric edit is required.** Every published cell that draws on this directory is either correct
as printed or unchanged by the mixture. The required change is a provenance disclosure, and the
`tab:sim-knees` caption is the right place for it — it is the only published object that draws AIC
rows from both runtimes.

Append to the `tab:sim-knees` caption (twopool.tex, after "...encoder-delay p99 for vision rows."):

```
The burst-window AIC rows and the TP2$\times$2 figure come from the
source-built runtime; the steady-window AIC row is from the earlier
wheel build, whose TTFT p99 agrees with the source build to
\SI{0.2}{\percent} at $s{=}1$ and which does not move the knee
(the source build brackets the same crossing at $s{=}2.8$).
```

Housekeeping, outside the manuscript: `simulation/results/sweeps/reports/` should not remain a
directory whose runtime can only be recovered from a JSON key set. Recommend either splitting the
four EXT files into `sweeps/reports_srcbuild/` or adding a `runtime` column to
`provenance.sweep_point` populated from the presence of `gpu_hours`. The latter is a one-line
backfill and makes the mixture queryable instead of forensic.

---

## DEFECT 3 — intro.tex:148 and :504, "offered-work upper bound"

### Verdict: **CONFIRMED in substance; the delivery's supporting statistics are drawn from the arm its own card disqualifies.**

`A16_decode_FINAL.md` states, correctly and at length, that `timesfm_e2e` "cannot support any
'against the trace' sentence" (its `primary_is_composed_duplicate = true`, trace fidelity
1.67e-05 vs 7.82e-07) and that the claim must be sourced from the two `ft_llm` arms. Then **every
figure it quotes is the `timesfm_e2e` figure.** Re-derived from
`defense/anim/data/a16_decode_spread/ft_llm_{static,reactive}_a16_stats.json` and
`a16_decode/timesfm_e2e_a16_stats.json`, all at `by_resolution/15/vs_primary_arrival`:

| statistic | ft_llm_static | ft_llm_reactive | timesfm_e2e | card quoted |
|---|---:|---:|---:|---|
| `n_requests` | 1,000,000 | 1,000,000 | 999,599 | — |
| `primary_is_composed_duplicate` | False | False | **True** | — |
| `totals.output_vs_trace_rel_err` | 7.8229e-07 | 7.8229e-07 | 1.6657e-05 | 7.82e-07 ✓ |
| **`frac_bins_understated`** | **0.4768** | **0.4728** | **0.5819** | **"58 %"** ✗ |
| `frac_bins_overstated` | 0.5224 | 0.5269 | 0.4176 | — |
| truth-selected top-1 % `bias_frac` | −0.00836 | −0.01199 | −0.01297 | −1.3 % (timesfm) |
| truth-selected top-1 % `frac_bins_short` | 0.5545 | 0.5792 | 0.5668 | 56.7 % (timesfm) |
| truth-sel. `shortfall_p90_tok_s` | 230.8 | 269.9 | 249.6 | 249.6 (timesfm) |
| truth-sel. `shortfall_max_tok_s` | 934.7 | 927.3 | 909.8 | 909.8 (timesfm) |
| truth-sel. `shortfall_max_frac_of_own_bin` | 0.7202 | 0.6019 | 0.7148 | 71.5 % (timesfm) |
| **arrival-selected top-1 % `bias_frac`** | **+0.5448** | **+0.5560** | **+0.5438** | +54.4 % ✓ |
| `verdict/res_15s/max_frac_bins_under_provisioned` | 0.11447 | 0.12350 | 0.12186 | 12.19 % (timesfm) |
| onset `ratio_mass_weighted` | 2.7586 | 2.8393 | 2.7962 | 2.796 (timesfm) |
| decay `ratio_mass_weighted` | 0.5093 | 0.5216 | 0.5059 | 0.506 (timesfm) |
| onset `n_bins` / mass frac | 403 / 4.79 % | 403 / 4.79 % | 403 / 4.78 % | 403 ✓, 5.65 % w/ decay ✓ |

**What holds.**

- *Not a pointwise upper bound* — **confirmed decisively**, and on the right arms. On the
  truth-selected busiest 1 %, the stamp falls short in **55.5 % / 57.9 %** of bins, with a worst-case
  shortfall of 934.7 tok/s = **72.0 %** of that bin's own true rate. At 1 s resolution
  `frac_bins_understated` = 0.5384 and the worst understated bin has ratio 0.182 (738 stamped vs
  4062 true tok/s). A pointwise bound is falsified many times over.
- *Strongly conservative on the observable selection* — **confirmed**. Arrival-selected busiest 1 %:
  +54.48 % / +55.60 % / +54.38 %. Spread across all three arms = **1.22 pp**; the delivery's
  "within 1.2 pp" is right at the rounding edge — say "within 1.3 pp" or quote the range.
- *Exact in total volume* — confirmed, 7.8229e-07 on both `ft_llm` arms.
- *Onset/decay characterisation* — confirmed on the ft arms (mass-weighted onset 2.76–2.84, decay
  0.51–0.52, onset+decay = 5.65 % of mass).

**What does not hold.**

The delivery's headline sentence, "understates 58 % of bins at 15 s", is **the `timesfm_e2e`
number and it does not reproduce on the arms that must source the claim**. On `ft_llm_static` and
`ft_llm_reactive` the stamp understates a **minority** of bins — 47.7 % and 47.3 % — and *overstates*
52.2 % / 52.7 %. A replacement sentence built on "58 %" would be wrong. Use the truth-selected hot-bin
figure (55–58 % short **within the busiest 1 %**), which is the load-bearing statistic anyway and
which does reproduce on all three arms.

### Do both sites need changing? Yes.

They phrase it differently but both assert the same unsupported thing:
- **:148** — "an upper bound on decode load" (pointwise, unqualified, inside the $R^2$ sentence)
- **:504** — "makes the decode series an offered-work upper bound" (the Scope-and-limitations
  statement)

:504 is the place for the full qualification; :148 should carry only the short, correct
characterisation and defer.

### Collisions

None. No rejected fix touches intro.tex:148 or :504. R45 (aiconfigurator.tex:444) is unrelated. The
$R^2 = 0.654$ value at :146–147 is a trace-EDA result, untouched by these edits.

### Exact replacement text

**Edit 3 — intro.tex:147–149.** Replace:

```
image-rate series but $R^2=\num{0.654}$ of decode demand (measured as
offered work stamped at arrival, an upper bound on decode load;
Chapter~\ref{cap:trace-eda}). The image signal is also an order of
```

with:

```
image-rate series but $R^2=\num{0.654}$ of decode demand (measured as
offered work stamped at arrival, which displaces decode work in time
without changing its total; Section~\ref{sec:intro-scope},
Chapter~\ref{cap:trace-eda}). The image signal is also an order of
```

**Edit 4 — intro.tex:502–504.** Replace:

```
arrival-side information only: the rate signals stamp each request's full
token volume at its arrival minute, which is faithful for encoder and
prefill work but makes the decode series an offered-work upper bound. The
```

with:

```
arrival-side information only: the rate signals stamp each request's full
token volume at its arrival minute, which is faithful for encoder and
prefill work but displaces decode work in time. The decode series is exact
in total volume --- within \num{8e-7} of the replay --- and strongly
conservative on the bins an operator can actually identify, running
\SIrange{54}{56}{\percent} high on the busiest \SI{1}{\percent} of bins as
selected by the arrival stamp itself. It is \emph{not} a pointwise upper
bound: on the busiest \SI{1}{\percent} selected on the true series it is
under \SI{1.2}{\percent} low in the mean but falls short in
\SIrange{55}{58}{\percent} of those bins, so its shortfalls concentrate in
bins identifiable only in hindsight. The
```

Every number in Edit 4 is the range over the two `ft_llm` arms (n = 1,000,000 each, genuine trace
join), so it is exactly as strong as the evidence and no stronger. "8e-7" is
`totals.output_vs_trace_rel_err`, not the `mass_conservation_rel_err ≈ 1e-14` construction identity
the card warns against. `\SIrange` requires `siunitx`, already loaded for the `\SI` calls on the
adjacent lines. No macro or label is disturbed; `\label{sec:intro-scope}` at :498 is the target of
the new cross-reference added in Edit 3.

**Carry the card's residual risks.** Do not, on this evidence, write any sentence claiming a
provisioning risk: the decode series enters the planner only as `osl = gen/req`
(`replay_with_forecast.py:138`), never as a decode rate, and the controller point-samples at
stride 4 with per-phase bias spanning zero (+1.27 / +4.67 / +0.04 / −9.43 % against true 60 s mass).
Any provisioning claim built on A16 is one inferential step short. The proposed wording above makes
no such claim.

---

## Summary

| defect | verdict | edit required |
|---|---|---|
| 1 — twopool.tex:78 "307 / 882" | **PARTIALLY CONFIRMED**; delivery's mixed-runtime diagnosis **REFUTED** (the whole paragraph is wheel on both arms). Real defect is the 4× column: source build gives the 235B 20,033 ms vs the published 1,402 ms. | Edits 1 and 2 — qualify :69, delete the 4× column at :77–78. **Do not** requote 882 as 783. |
| 2 — `sweeps/reports/` runtime-mixed | **CONFIRMED**; delivery's evidence wrong (4543.39 ≠ srcbuild's 4517.57) and scope too narrow (4 source files, not 1). Steady AIC knee curve crosses the boundary but the knee is robust; `tab:sim-knees` draws its two AIC rows from different runtimes. | No numeric edit. Caption disclosure on `tab:sim-knees` + a `runtime` column backfill on `provenance.sweep_point`. |
| 3 — intro.tex:148 / :504 "upper bound" | **CONFIRMED** in substance; delivery's statistics come from the `timesfm_e2e` arm its own card disqualifies, and its "58 % of bins" figure **does not reproduce** on the `ft_llm` arms (47.7 % / 47.3 %). | Edits 3 and 4 — both sites, using ft-arm ranges only. |

No proposed edit contradicts a rejected fix. `tab:sim-poly-aic` (R4/R12) is independently
re-confirmed and untouched; R13's conclusion stands on a value that has since shifted 1.2 %
(213.044 → 210.588 ms, still far over bound); R26's post-manuscript rule is the reason Edit 2
deletes rather than substitutes.
