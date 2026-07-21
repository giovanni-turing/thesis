# THE ADJUDICATION LEDGER — FINAL, POST-ADVERSARIAL

Single authoritative worklist for editing the thesis, after (a) claim-by-claim verification against
`provenance.*` (`audit/verified/*.json`, 917 claims), (b) the internal-arithmetic pass
(`audit/internal_defects.json`, 107 defects), (c) the cross-chapter consistency pass
(`audit/crosschapter_report.md`), and (d) **adversarial review of every mismatch in all 13 chapters**
(`audit/adversarial/*.json`).

**Status: complete.** All 13 chapters have been adversarially reviewed. Nothing below is provisional.

**Rules applied throughout (all ratified by the adversarial pass):**

1. A thesis number obtainable from the archived value under an ordinary rounding-to-published-precision
   convention is CONFIRMED, not wrong.
2. **Never recompute a percentage or ratio from already-rounded table cells.** This single failure mode
   produced *nine* of the rejected fixes in §0.4.
3. **"Not in the DB" ≠ "unverifiable."** Go to the archived artifact on disk. This change of method flipped
   the majority of INSUFFICIENT_DATA verdicts to CONFIRMED.
4. **Identify the artifact before comparing.** Several proposed fixes compared the thesis against the wrong
   file in a family of similarly-named artifacts (`vllm_eager_vit` vs `vllm_eager_dense`; srcbuild vs wheel;
   `anchor_flash_attention_2_5x50` vs `merged_fa2.csv`).
5. Where the honest fix is to *weaken* a claim rather than restate it, that is said explicitly. Never delete.
6. Nothing below proposes a number that is not either (i) read from a query/artifact printed inline, or
   (ii) derived by arithmetic printed inline.

---

## 0. Totals

### 0.1 Verification verdicts (all 13 chapters, 917 claims) — first pass

| Verdict | Count |
| --- | ---: |
| CONFIRMED | 678 |
| UNVERIFIABLE | 125 |
| INSUFFICIENT_DATA | 41 |
| THESIS_WRONG | 28 |
| DEFINITIONAL | 28 |
| ARTIFACT_SUPERSEDED | 17 |

### 0.2 Adversarial review — ALL 13 chapters, 112 mismatches

| Chapter | Reviewed | Upheld | Overturned | Verdict upheld, fix revised |
| --- | ---: | ---: | ---: | ---: |
| baselines | 16 | 10 | 6 | 0 |
| closedloop | 15 | 0 | **15** | 0 |
| aiconfigurator | 8 | 3 | 5 | 0 |
| predictors | 9 | 5 | 4 | 3 |
| twopool | 15 | 10 | 4 | 1 |
| apendice | 14 | 6 | 7 | 1 |
| intro | 13 | 2 | **11** | 0 |
| conclusion | 6 | 2 | 4 | 0 |
| trace-eda | 6 | 1 | 5 | 0 |
| validation | 3 | 0 | **3** | 0 |
| tese | 3 | 1 | 2 | 0 |
| related | 3 | 2 | 0 | 1 |
| apendice_ecosystem | 1 | 0 | 1 | 0 |
| **total** | **112** | **42** | **67** | **3** |

> **Overall overturn rate: 67 / 112 = 59.8 %.**
> Counting the 3 "verdict upheld but the proposed fix was itself wrong" cases as partial reversals, the
> first pass was materially wrong about **70 of 112** mismatches (**62.5 %**).
>
> Four chapters were reviewed to a **zero-defect** result (closedloop, intro, validation, tese: every
> mismatch overturned). Read this rate as the reason §0.4 exists: an unreviewed defect list applied
> verbatim would have introduced more errors than it removed.

### 0.3 Post-adjudication worklist size

| Action class | Count |
| --- | ---: |
| §1 EDITS TO MAKE (survived adversarial review) | **32** |
| — of which change a published digit | 13 |
| — of which are scope/wording narrowings (no digit changes) | 19 |
| §1 blocked pending an author answer (do **not** guess) | 1 |
| §2 DB CORRECTIONS (thesis correct, database stale/absent) | 12 groups |
| §3 DENOMINATOR / DEFINITION CLARIFICATIONS | 20 |
| §4 LIMITATIONS THE DATA RETIRES (1 fully, 4 partially) | 5 |
| §5 REMAIN UNVERIFIABLE (assert, do not claim as measured) | 125 |
| §6 OPEN QUESTIONS | 9 (2 of the previous 9 now answered, 3 new) |
| **Proposed fixes explicitly REJECTED** | **44** |

Chapters with **zero** text edits of their own: `tese.tex`, `baselines.tex`. `intro.tex` carries exactly one
edit, and only as the mirror of a `related.tex` fix.

### 0.4 REJECTED fixes — the most important section in this document

Every one of the 44 entries below was proposed by an earlier pass and is **wrong**. Applying any of them
would introduce an error into a correct thesis, or replace one wrong value with a different wrong value.
A downstream editor working from the first-pass defect lists **must** diff against this table first.

#### 0.4.1 Rejected because the fix was computed from already-rounded cells

| # | Proposed (rejected) | Site(s) | Why rejected |
| --: | --- | --- | --- |
| R1 | `1.1 % → 1.0 %` | conclusion.tex:53; validation.tex:72, 83, 97, 159; intro.tex:536 | Unrounded live 3531.4532 (`live_re/profile_export_aiperf.json`) vs offline twin 3494.725887 (`llm_run_summary`) → **1.05094 % → 1.1 %**. The 1.03 % came from dividing the printed cells 3,531 / 3,495. Re-proposed and re-rejected in **three** separate chapter reviews. |
| R2 | `18.0 % → 18.6 %` | validation.tex:161 | Unrounded: live ITL p99 11.469605 (aiperf export) − offline 9.718328 (`llm_run_summary.p99_tpot_ms`) = 1.751277; 1.751277/9.718328 = **18.020 % → 18.0 %**, exactly as published. The 18.6 % came from 1.8/9.7 — both operands pre-rounded. **This also answers old Q2.** |
| R3 | `+24 % → +23 %` and `1.24× → 1.23×` | intro.tex:253; twopool.tex:61 | See R4 — the premise (which artifact backs the poly column) is false. |
| R4 | tab:sim-poly-aic poly cell `67.3 / 248 → 67.4 / 249` | twopool.tex:103 | The poly column is `simulation/results/srcbuild/llm_head2k_poly_src.json`, **not** the wheel row `sweeps:llm_head2k_poly_s1`. Decisive discriminator: the thesis prints mean TTFT **67.3**; srcbuild gives 67.30122 → 67.3, the DB wheel row gives 67.390 → 67.4. All five other poly cells (2,540 / 6,879 / 6.79 / 181 / 160.6) also match srcbuild. Ratio 307.36448/248.46453 = **1.23699 → 1.24 → +24 %**, as published. |
| R5 | `0.36 → 0.35` justified from the 3-dp store 0.355 | trace-eda.tex:246 | Direction is right (see [E22]), rationale is not: use the unrounded **0.3546002012649865** (`eda_metric`, `d_signals`, `pearson_1min.img_vs_req`). Rounding the stored 0.355 upward is exactly how the erroneous 0.36 arose. |
| R6 | relative-edge percentages recomputed from tab:pred-wape | predictors.tex:411 | Printed 54.2/52.9 gives 2.40 % against the true 2.30 %. Use unrounded `forecast_metrics.wape`. |

#### 0.4.2 Rejected because the fix compared against the wrong artifact

| # | Proposed (rejected) | Site(s) | Why rejected |
| --: | --- | --- | --- |
| R7 | `178.3 → 178.4` | apendice.tex:150 | tab:app-engine's vLLM column is `phaseE_physical_anchor/vllm_eager_vit.json` (**178.343**), the standalone eager vLLM vision tower named in the body at :187 — not `vllm_eager_dense.json` (178.4062). **178.3 is correct.** |
| R8 | `333.7 → 333.6` | apendice.tex:151 | Same artifact error: `vllm_eager_vit.json` = **333.732** → 333.7. Correct as printed. |
| R9 | HF-FA2 `54.1 → 54.2`, `465.7 → 465.6` | apendice.tex:149, 151 | Those cells come from `anchor_flash_attention_2_5x50.json` (**54.0604**, **465.7424**), not `merged_fa2.csv`. Correct as printed. |
| R10 | `1.25× → 1.26×` at N=8 | apendice.tex:182 | 54.0604/43.126 = **1.2535 → 1.25** from the 5×50 anchor. 1.26 came from the wrong FA2 file. |
| R11 | residual tuple `→ (−2.2, +11.4, +5.5)` **and** the rival `→ (−2.1, +11.3, +5.5)` | apendice.tex:185 | Against `vllm_eager_vit.json`: −2.2009 / +11.328 / +5.488 %. The published **(−2.2, +11.3, +5.5)** is already the single-basis unrounded tuple. Both proposals are wrong; the "mixed bases" charge collapses. |
| R12 | edit tab:sim-poly-aic cells / the 1.24-1.8-1.9 ratios toward `sweeps:llm_head2k_{poly,aic}_s1` | twopool.tex:61, 103, 104, 105, 106 | Those DB rows are the **wheel** runtime (max TTFT 7598.10 ms) that twopool.tex:64-66 explicitly names and discards. The srcbuild artifacts reproduce all six cells exactly. Would replace six correct numbers with six wrong ones. |
| R13 | soften the 235B knee to "by inference from an ITL p99 of 87.7 ms" | twopool.tex:82 | The knee is now **measured**: `misc:235b_tp8_s2` ITL p99 = 213.044 ms > 100 ms, with 25 finer points bracketing the crossing at s ∈ [1.121, 1.135]. Hedging would understate a supported result. |
| R14 | soften "identical to three decimals" → "agree to within 1 ms" | twopool.tex:151 | The first pass compared `sweeps:vision_head2k_s1` (a vision-converter run) against `sweeps:llm_head2k` (a language isolation run) — two different experiments. The real sequential-vs-batched validation (`progress/phase2-simulation.md:116-118`) reports p50/p90/p99 **exactly equal**. |
| R15 | soften/delete the 235B-TP8 spot-check | intro.tex:380, 526 | 26 runs exist as `misc:235b_tp8_%` with `tp=8`. The first pass missed them by filtering `runs.model`, which stores **forecast**-model names. |
| R16 | edit toward `llm_run_summary.p99_itl_ms` (5.29 / 160.26 ms) | intro.tex:537, 538 | Different metric. tab:val-anchor defines ITL p99 as (RequestLatency−TTFT)/(OSL−1) = aiperf TPOT = **`p99_tpot_ms`** (9.7183 / 152.6811), which matches the thesis exactly. |
| R17 | substitute the 9-minute median from `eda_burst_episode` | trace-eda.tex:290; predictors.tex:335 | That table holds 24 `episode_kind='merged'` rows — a **different population** from the 18 episodes the EDA figure and both chapters report (median 6.5 → published 6). |

#### 0.4.3 Rejected because the thesis statement is true as written

| # | Proposed (rejected) | Site(s) | Why rejected |
| --: | --- | --- | --- |
| R18 | `0.96× → 0.97×` | tese.tex:68, 114; conclusion.tex:85; closedloop.tex:375 | The ratio is **0.9650 — the exact 2-dp tie point** — under all three legitimate denominators (published operands 0.96501675; `windows.aggregate` span×4 GPU 0.96502895; `a13:ft_llm_static` pro-rated 0.96501512). The spread between defensible denominators (3e-5) **exceeds** the distance from the tie (1.5e-5), so the value is not resolvable to two decimals. 0.96 is obtainable by truncation or round-half-even. The same ratio beside its own operands is already **CONFIRMED** at closedloop.tex:373-375. Applying the fix would convert a consistent thesis into an inconsistent one. See Q7. |
| R19 | `1,314 → 1,315` | baselines.tex:108 | 1,314 is the floor of the measured min 1313.800 (`grid_llm_point`, TP1×4). Narrowing would exclude the measured minimum. |
| R20 | `~14 % → ~12.5 %` | closedloop.tex:337 | Retained policy scale is **8.0**, not 7.0; binding burst4 knee is 7.0 → 8.0/7.0 = 1.143 = the published ~14 %. |
| R21 | "reconcile 400/40 with 500/50" | baselines.tex:159 vs tab:base-ladder | Both correct, different experiments (`run_32_reactive.sh:24` = 500/50; `run_44_riders.sh` ladder starts at 400/40). |
| R22 | replace "typically under 2 WAPE points" with a 1-min-only bound | predictors.tex:175 | The hedge holds in **16 of 20** grid cells, and the chapter separately acknowledges the larger sub-minute gaps at :386. Not an error. |
| R23 | replace "within ≈2 WAPE points" as "4× too loose" | predictors.tex:382 | The sentence is an **upper bound**; the measured max 1-min inter-model gap is 0.472 points. A conservative true bound is not a defect. |
| R24 | "about a WAPE point" → "0.6 WAPE points (1.2 % relative)" *as an error correction* | predictors.tex:191 | 0.602 → "about a" point at one significant figure; both operands (0.521, 0.515) are printed in the same sentence. Permissible as precision polish; **must not be logged as an error**. |
| R25 | `≈2.25× → 2.48×` (or 2.5×) | twopool.tex:436 | 2.25 is the exact patch-count ratio (672/448)² that the sentence explicitly derives. Substituting the AIC anchor makes the sentence contradict its own stated premise. |
| R26 | edit the "32B were not priced" clause | twopool.tex:391 | The only 32B rows (`misc:32b_tp2_*`, created 2026-07-20 from `defense/anim/data/g3_32b/`) are **post-manuscript** defence material. |
| R27 | `26 → 39` parquet files | apendice.tex:275 | 26 = 6 models × 4 signals + 2 covariate variants — exactly the files feeding tab:pred-wape and the four `pred-*` figures. The 39-file total includes 12 `*_expctx` and 3 `ewma_cal_*` belonging to other rows. **Answers old Q6.** |
| R28 | weaken "external hard lock" → "no lock-command log captured" | apendice.tex:124 | The command **is** archived: `ENCODER_ANCHOR_SUMMARY.md:92`, `nvidia-smi -lgc 2400,2400 -lmc 14001`. Weakening would understate a documented intervention. (The *separate* SM 2407 defect at :28 does survive — see [E16].) |
| R29 | `21.4 M → 16,657,524` forecast rows | intro.tex:431 | The DB is 5.3 M short only because the covariate-mode point partitions at 1 s/30 s/45 s/1 min were never ingested. The on-disk archive the sentence refers to totals **21.57 M–22.00 M**. |
| R30 | drop the parenthetical "measured 1.0 s spawn-to-registered latency" | validation.tex:43 | It is measured: 5 spawn→`Discovery Added` pairs across both anchor live runs give 0.954–0.996 s, mean **0.986 s → 1.0 s**. Deleting it removes a correct measurement. |
| R31 | "clamps it to 8" → "clamps it to 4 replicas (8 GPUs at 2 GPUs/TP2 replica)" | validation.tex:140 | The 24-replica request is from `episode_twins/burst4_fc.log`, an **offline** episode replay where `max_gpu_budget` is in **replica units** ("clamped 24 replicas (= 24 GPUs) → 8 replicas (= 8 GPUs)"). The fix would attach the anchor's cap of 4 to a different run and assert a conversion the offline path does not perform. |
| R32 | `0.12 → 0.123` | related.tex:225 | 0.12 is the correct 2-digit rounding of 0.12253911262014872. Cosmetic only; must never appear in an errata. |
| R33 | rewrite conclusion.tex:95 on the premise that the denominator is wrong or the unit mismatched | conclusion.tex:95 | Both premises false. The cheapest static fleet (C=2, 1,209,599 ws) **fails** at enc p99 2,904.6 ms, so "best static" cannot mean it; and 1 worker = 1 GPU is exact (`grid_window_effective.gpu_hours_rtx5090_effective = span_h × c_star`). Only the loose paraphrase is worth touching, optionally. |
| R34 | change the ≈3 % figure itself | conclusion.tex:39 | The 3 % is correct and confirmed on its measured side (attention 1.300 ms at N=1). Only the operator **name** is at fault ([E1]). |
| R35 | `1.36–1.61 → 1.4–1.6` harmonisation, or "fixing" the ≈1.4–1.6× summaries | intro.tex:249, 510; apendice.tex:194; conclusion.tex:106 | Upheld as correct at one-decimal precision. Optional cosmetic tightening only. |
| R36 | weaken/hedge the diurnal harmonic family or the 1/f fit band | trace-eda.tex:136, 317 | Both premises false: the full periodogram is recomputable from the source trace, and the fit band is hard-coded at `analysis/trace_eda/f_fourier.py:73` (`fb > 1/43200 & fb < 1/600` = 10 min–12 h, verbatim as published). |
| R37 | append "the 12/8/6 h overtones fall inside the band and are not notched out" | trace-eda.tex:317 | For the **image** signal (the signal the sentence is about) the 12 h and 8 h lines are **below** local background (power ratios 0.19, 0.23). The caveat would assert contamination that does not exist. |
| R38 | "per-image token rate" / describe 277 and 66 as median-context ÷ image-count ratios | trace-eda.tex:38 | Arithmetically false at k=1 (1069/1 = 1069, not 277). Only *(median ctx(k) − 792)/k* reproduces **both** 277.000 and 66.427. |
| R39 | "median 1 image among their image-bearing requests" | trace-eda.tex:411 | `q_multires_tails.py:106-131` computes over **all** requests in the hot minutes. The fix states a false provenance. |
| R40 | flag burst5 `C*` / `grid_vision_point.feasible` for re-ingest | apendice.tex:301 | Already done: `grid_window.c_star_corrected = 8`, `is_superseded = t`, `grid_window_effective` resolves it with `correction_source`. Overwriting `grid_window.c_star` would destroy the raw pre-correction record. |
| R41 | `ai-dynamo 1.3.0 (source)` → `v1.3.0-rc1 (2026-06-30)` | apendice_ecosystem.tex:125 | The editable install points at a tree whose HEAD is **70c965db26** (2026-07-19) — *after* rc1 and not that tag. Would replace a correctly hedged statement with a false tag attribution. |

#### 0.4.4 Rejected because the replacement magnitude or label is itself wrong

| # | Proposed (rejected) | Site(s) | Why rejected |
| --: | --- | --- | --- |
| R42 | `−5.8 %/+4.3 % → −4.1 %` | aiconfigurator.tex:196 | Direction right, endpoint wrong: correct value is **−4.2 %** (see [E2]). |
| R43 | "p30 in the last" | predictors.tex:282 | The DB gives **p10** for TimesFM on 1-second images (p10 WAPE 99.94 vs point 120.47, −17.04 %). p30 wins **no** TimesFM cell. Would swap one wrong quantile label for another. |
| R44 | "only the fastest decile, ~10 % of bursts" and "10th-percentile onset 1.7 minutes" | related.tex:312; intro.tex:167 | (a) Confuses a percentile **label** with the qualifying **fraction**: 8/24 merged and 6/18 published episodes have onset ≤ 2 min ≤ the 165 s max lead → **~33 %**. Would swap an overstatement for an understatement. (b) "1.7 minutes" contradicts trace-eda.tex:289-291's published "10th percentile 2 minutes" and manufactures a new inconsistency. Correct fix at [E27]. |
| R45 | `≈0.25 ms → 1.18 ms` (or the reverse) | aiconfigurator.tex:444 | Blocked on **Q2**. Do not pick one silently. |
| R46 | small-N compile band `1.06–1.15×` | apendice.tex:191 | Measured N≤6 maximum is **1.1708** (N=6). Band is 1.06–**1.17**. |
| R47 | ModServe: attribute the 3.3–5.5× to *image-encoding* throughput | related.tex:56 | The stage was not read from the cited paper; applying it inserts a fabricated attribution into a citation. Safe form: decouple the two figures without naming a stage. |
| R48 | "qualify 0.96× as Chronos-specific" in the abstract | tese.tex:68 | Downgraded to non-mandatory. True (Toto 1.164×, TimesFM 1.193×) and already disclosed at closedloop.tex:382; an abstract legitimately reports the primary configuration. |

---

## 1. EDITS TO MAKE

**Only defects that survived adversarial review.** Ordered by chapter, then criticality
(headline → supporting → incidental), then line. Every entry carries the query or arithmetic that
justifies it. `V:` = final verdict class. `C:` = criticality.

### 1.1 conclusion.tex — 1 edit

**[E1] conclusion.tex:39 — C: headline — V: DEFINITIONAL (upheld)**
- Current: `validated to ${\approx}3\%$ on its dominant operator with a fully attributed residual ledger`
- Replace: `validated to ${\approx}3\%$ on its collected attention operator (the GEMM stratum ${\approx}6\%$) with an attributed residual ledger`
- DB: `SELECT n_images, entry_kind, entry_name, ms, total_kernel_ms FROM provenance.collector_kernel_ledger WHERE n_images=1 AND entry_kind='category' ORDER BY ms DESC;` → gemm **6.029 ms**, attention **1.300 ms**, elementwise 1.179, patch_embed 0.495, norm 0.262, gather_cat 0.257, other 0.020; total 9.542 ms.
- Arithmetic: attention = 13.6 % of kernel time; **GEMM = 63.2 % is the dominant category**. Corroborated by `collector_vit_op_breakdown`: matmul share 0.789/0.675/0.661 at N=8/32/64. The source chapter says so itself (aiconfigurator.tex:441-442, :513: "on the collected attention operator").
- **The 3 % must not be touched** (R34). Dropping `fully` is required by [E4] below.

*(conclusion.tex:85 `0.96×` — REJECTED, R18. conclusion.tex:95 "roughly two-thirds" — overturned to CONFIRMED; optional tightening only, see §3.1.)*

### 1.2 aiconfigurator.tex — 3 edits + 1 blocked

**[E2] aiconfigurator.tex:196 — C: headline — V: THESIS_WRONG (upheld, endpoint revised)**
- Current: `The pre-infill 448-pixel path shows this stratum's cost here: $+4.3\%$ to $-5.8\%$ from the exact measurements.`
- Replace: `The pre-infill 448-pixel path shows this stratum's cost here: $-4.2\%$ to $+6.2\%$ from the exact measurements (equivalently, the infill shifted the prediction by $+4.3\%$ at one image and $-5.8\%$ at six).`
- DB: `SELECT n_images, engine, aic_ms FROM provenance.collector_fn WHERE engine IN ('aic','aic_postinfill') ORDER BY n_images;` → N=1 7.822/8.162; N=6 33.760/31.792; N=8 44.105/43.126; N=16 83.783/82.217; N=32 160.701/160.196; N=64 314.498/316.369.
- Arithmetic: the published pair is (post−pre)/pre = +4.347 % (N=1), −5.829 % (N=6) — the shift applied *to the prediction*. The sentence's own framing (pre-infill deviation *from* the exact measurement) has the post-infill exact-hit as base and the **opposite sign**: (7.822−8.162)/8.162 = **−4.166 %**; (33.760−31.792)/31.792 = **+6.190 %**. Extremes over the tabulated range: N=8 +2.27 %, N=16 +1.90 %, N=32 +0.32 %, N=64 −0.59 %. Lower endpoint is **−4.2 %**, not the −4.1 % first proposed (R42).

**[E3] aiconfigurator.tex:350 — C: supporting — V: DEFINITIONAL (upheld)**
- Current: the sentence attributing "twelve" batch sizes to this section's f(N) sweep.
- Replace with either `the twelve anchor batch sizes of the silicon sweep are memoized in minutes` or `the eight batch sizes of this section's protocol`.
- DB: `SELECT source_path, count(DISTINCT n_images) FROM provenance.collector_encoder_fn GROUP BY 1;` → `anchor_sdpa_5x50` = **8** points (1,2,4,6,8,16,32,64 — the 5×50 protocol this section describes); `silicon_burst5`/`silicon_burst3` = **12** points (1,4,9,16,17,25,33,36,41,49,57,64). Twelve is real but belongs to the phase-E silicon anchor grid.

**[E4] aiconfigurator.tex:452 (+ :18, :433) — C: headline — V: internal arithmetic**
- Current: `Removing the two unmodeled modules leaves \SI{8.92}{\milli\second} of AIC-comparable work against \SI{7.82}{\milli\second} predicted, within ${\approx}12\%$, fully attributed...`
- **Weaken, do not restate:** delete `fully attributed`, and the companion `closes ... with no unexplained residual` at :18 and :433; write `within ${\approx}12\%$, with the residual attributed term by term except for a ${\approx}0.7$\,ms remainder`.
- Inline arithmetic: gap = 8.917 − 7.822 = **1.095 ms**. Published attributions: attention −0.042 ms; GEMM "≈+6 %" of a predicted GEMM ≤ 7.822 − 1.342 = 6.480 → ≤ **+0.389 ms**; elementwise+layernorms ≈ **+0.25 ms**. Max attributed = **+0.597 ms** < 1.095 ms. The ledger does not close as claimed.
- Do not invent the missing term. Publishing the predicted GEMM subtotal would settle it (**Q3**).

**[BLOCKED-1] aiconfigurator.tex:444 — C: supporting — V: internal arithmetic (self-contradiction)**
- Two published values for the identical shape/stack (448², N=1, HF-eager): :444 says `${\approx}0.25$ ms` for unfused elementwise + layer norms; :293 says elementwise `rises from 1.18 to 1.89 ms per image`, and `collector_kernel_ledger` carries elementwise = **1.179 ms** at N=1. Ratio 1.18/0.25 = 4.7×.
- **Do not apply either value** (R45). Resolve **Q2** first: is 0.25 ms the absolute term or the *excess over prediction*? Then reconcile.

### 1.3 predictors.tex — 5 edits

**[E5] predictors.tex:282 — C: headline — V: THESIS_WRONG (upheld, fix revised)**
- Current: `...beaten in 18 of its 20 cells (median improvement $-1.7\%$, always by a below-median quantile, modally p40)...`
- Replace the quantile clause: `(median improvement $-1.7\%$, always by the median or a lower quantile --- the p50 head in 17 of the 18, p10 in the last, 1-second images)`
- DB: pairing `candidate='point'` against `min(wape)` over quantile candidates per (model, mode, resolution, variate) in `provenance.forecast_metrics` (`span='common' AND h=-1`) → TimesFM **18/20** beaten, median **−1.679 %**, best −17.04 %. Grouping the same join by (model, best-quantile): TimesFM **p50 = 17 cells, p10 = 1 cell** (1 s images, WAPE 99.94 vs point 120.47); **p40 wins no TimesFM cell** (p40 is the modal winner across all 51 cells, which is the conflation).
- **Write p10, not p30** (R43). Everything else in the sentence verifies: 31 baseline cells (EWMA 9 + Holt-Winters 16 + naive 6); Holt-Winters 1-s images p10 118.91 vs point 217.04 = **−45.21 %**.

**[E6] predictors.tex:411 — C: headline — V: THESIS_WRONG (upheld, fix revised)**
- Current: `a modest 2--9\% relative edge at provisioning cadence, one-third relative at sub-minute bins`
- Replace: `a modest 2--9\% relative edge at provisioning cadence, widening to 8--32\% at 1-second bins --- one-third on the image signal, where WAPE${\approx}100\%$ marks the no-skill floor`
- DB (best FM vs best baseline, unrounded `forecast_metrics.wape`, `candidate='point' AND h=-1 AND span='common'`): 20/20 cells positive. 1 min: images 2.30, ctx 3.30, requests 5.03, gen 9.27 %. Sub-minute: 45 s 7.91–10.64; 30 s 8.87–11.31; 15 s 13.32–16.39; **1 s: requests 7.58, gen 18.33, ctx 18.84, images 32.40 %**.
- "One-third" is reached in **1 of 16** sub-minute cells. The body at :154 scopes it correctly; the summary drops the scope. **Do not extend "one-third" to 15/30/45 s** (7.9–16.4 %), and do not recompute from table cells (R6).

**[E7] predictors.tex:96 — C: supporting — V: THESIS_WRONG (upheld, fix substantially revised)**
- Current: `averaged over a configuration's ${\approx}54$k origins, one 12-step forecast costs ${\approx}65$ (Chronos-2) to ${\approx}90$ (Toto-2) milliseconds of GPU time, comfortably inside any 15--60-second decision cadence.`
- Replace: `averaged over a configuration's \num{54000}--\num{56600} origins, one 12-step forecast of all four signals costs \SI{4}{\milli\second} (TimesFM) to \SI{51}{\milli\second} (Chronos-2 with covariates) of GPU time, comfortably inside any 15--60-second decision cadence.`
- Source: archived per-part logs `predictors/results/logs/*.log`, summed per (model, mode): chronos/uni 54,035 origins / 697.8 s = **12.91 ms**; chronos/cov 54,035 / 2752.4 s = **50.94 ms**; toto/uni 55,740 / 2383.6 s = **42.76 ms**; toto/cov 55,740 / 2364.8 s = **42.43 ms**; timesfm/uni 56,595 / 236.8 s = **4.18 ms**. Each part emits 48 rows per origin (4 variates × 12 steps), so one origin = one 12-step forecast of all four signals.
- The defect is proven **internally**: the published 65/90 divide a **two-configuration** runtime total (chronos 3450.2 s, toto 4748.4 s) by a **one-configuration** origin count, and the immediately preceding sentence uses those same totals *correctly* as per-model wall-clock ("roughly one hour and 80 minutes" = 57.5 and 79.1 min).
- **Supersedes the earlier proposal of ≈32/≈43 ms**, which halved the double count but kept the wrong pairing.

**[E8] predictors.tex:252 — C: supporting — V: THESIS_WRONG (upheld)**
- Current: `(75--100\% WAPE, against 58--72\% for the direct context forecast and 33--38\% for requests)`
- Replace: `(73--100\% WAPE, against 57--72\% for the direct context forecast and 33--38\% for requests)`
- Source: `predictors/results/metrics/additive_structural_ablation.json → component_forecastability_at_onsets` (subset `onset_steep_image_rise`), 4 entries: chronos/1min (images 0.75116, requests 0.37681, ctx_direct 0.57790), toto/1min (0.73326, 0.32829, 0.56542), chronos/15s (0.99647, 0.37485, 0.71636), toto/15s (1.00132, 0.37477, 0.71569).
- Ranges: images **73.33–100.13**, ctx_direct **56.54–71.64**, requests 32.83–37.68. The published *requests* range (33–38) already includes Toto-2's 32.83, proving the sentence is **not** scoped to Chronos-2 — yet the images and ctx lower bounds are the Chronos-2-only minima. 73.33 cannot bracket to 75; 56.54 cannot bracket to 58.

**[E9] predictors.tex:303 — C: supporting — V: THESIS_WRONG (upheld)**
- Current: `...reading as 0.14--0.21 coverage on images against 0.07--0.13 on the other signals.`
- Replace: `...against 0.07--0.14 on the other signals.`
- DB: `SELECT model, signal, (detail->'1min'->>'cov10')::float, (detail->'1min'->>'cov50')::float, (detail->'1min'->>'cov90')::float FROM provenance.quantile_coverage ORDER BY signal, model;` (20 rows) → p50 **0.435–0.484** (published 0.43–0.48 ✓); p90 0.880–0.898 (published 0.88–0.90 ✓); images p10 **0.142–0.213** (✓); non-image p10 **0.072 (TimesFM/gen) – 0.144 (Chronos-2-cov/ctx)**.
- 0.144 rounds to 0.14 and cannot bracket to 0.13. The same sentence's p90 parenthetical names a covariate configuration, so the 0.144 row cannot be excluded on scope grounds. **Change only the 0.13.**

*(predictors.tex:175, :191, :335, :382 — all overturned to CONFIRMED; R22, R24, R17, R23.)*

### 1.4 twopool.tex — 5 edits + 1 optional

**[E10] twopool.tex:230 — C: headline — V: THESIS_WRONG (upheld)**
- Current: `because the two tails are positively correlated ($r{=}0.52$ on image-bearing requests)`
- Replace: `($r{=}0.53$ on image-bearing requests)`
- Source: `simulation/results/rerun_verify/e2e_ingress_to_first_token.json → correlation_enc_vs_ttft.image_requests_only` = **0.527** (all_requests 0.424) → 0.53 at two decimals.
- Adversarial stale-artifact check **confirms** the defect: `git show a1d12a1^:simulation/results/rerun_verify/e2e_ingress_to_first_token.json` → 0.516, the pre-regeneration **target-time** run. Commit a1d12a1 rebuilt the artifact on issue-time inputs; the thesis number was never propagated. The thesis is stale, not the DB.

**[E11] twopool.tex:217 — C: headline — V: DEFINITIONAL (upheld)**
- Current: `validated against the week replay to within 8\% at p99: \SI{706}{} modelled versus \SI{651}{\milli\second} replayed`
- Replace: `validated against the week replay to within 8.5\% at p99: ...`
- Source: `simulation/results/rerun_verify/e2e_ingress_to_first_token.json → ttft_validation.modeled.p99` = **705.94**, `ttft_validation.replay_report.p99` = **651.1395369768143**. DB corroborates: `SELECT window_name, arm, ttft_p99_ms FROM provenance.composed_e2e WHERE window_name='week';` → 651.1 for fc_chronos/fc_toto/fc_timesfm.
- Arithmetic: against the **replayed reference** (705.94−651.1395)/651.1395 = **8.4160 %**; against the modelled value 7.7627 %. Only the second supports "within 8 %", and validating a model against a measurement conventionally normalises by the measurement. **8.5 % is true under both denominators**, so it cannot introduce an error. The defect is the unstated denominator, not the numbers. See §3.2.

**[E12] twopool.tex:185 — C: headline — V: DEFINITIONAL (upheld)**
- Current: `matches to within $12.8\%$ across the whole $N\le64$ serving regime (a dense sweep of 69 batch sizes)`
- Replace: `... across the whole $N\le64$ serving regime (64 consecutive batch sizes within a dense $N{=}1$--$512$ sweep of 69 points)`
- DB: `SELECT count(*) n_all, count(*) FILTER (WHERE n_images<=64) n_le64, min(n_images), max(n_images) FROM provenance.collector_encoder_fn WHERE source_path LIKE '%vllm_eager_dense%';` → **69 / 64 / 1 / 512**.
- **The 12.8 % bound must not be touched:** `progress/results-ledger.md:479` records max |dev| = **+12.7 % at N=52** across the dense N≤64 grid. Only the parenthetical mis-scopes.

**[E13] twopool.tex:403 — C: supporting — V: DEFINITIONAL (upheld)**
- Current: `the steady-window knee moves by one octave between the two models (Table~\ref{tab:sim-knees})`
- Replace: `the steady-window knee moves by one sweep step between the two models ($s{=}3$ polynomial to $s{=}2$ calibrated, a factor $1.5$ in offered load, $8.3\to5.5$~req/s)`
- DB: `SELECT run_id, p99_ttft_ms, p99_itl_ms FROM provenance.llm_run_summary WHERE run_id LIKE 'sweeps:llm_head2k%';` → poly s3 ITL p99 94.336 (PASS) / s4 154.237 (FAIL) → knee **s=3**; aic s2 67.334 (PASS) / s3 109.513 (FAIL) → knee **s=2**.
- Arithmetic: an octave is a factor 2; the shift is 3→2, a factor **1.5** (log₂ 1.5 = 0.585 octaves), and on offered load 8.3→5.5 req/s, factor 1.509. The sweep grid is unit-spaced below s=4, so a full octave is not expressible there. **Do not touch :387** ("one to two octaves higher") — a different, genuinely octave-spaced region.

**[E14] twopool.tex:276 — C: incidental — V: internal arithmetic (table-vs-table)**
- Current: `LLM / poly & steady & $s{=}3$ (ITL-bound) & 8.3 req/s & $249 \to 374$`
- Replace: `$248 \to 374$`
- Justification: tab:sim-poly-aic at :103 publishes **248** for the same cell, from `simulation/results/srcbuild/llm_head2k_poly_src.json` (p99 248.46453). tab:sim-knees prints 249, the **wheel**-runtime value (`sweeps:llm_head2k_poly_s1`, 249.441). Both are defensible in isolation, but they are the **same run under two builds**, and the chapter commits to srcbuild at :58-66. Harmonise **onto 248**.
- **Do not "fix" tab:sim-poly-aic to 249** (R4, R12). Knock-on: the :61 ratio 307.36448/248.46453 = 1.23699 → **1.24, unchanged as published**.

**[E15] twopool.tex:391 — C: incidental — V: DEFINITIONAL (upheld) — optional**
- Current: `Language-pool results are reported for the 8B at TP1 with a 235B-TP8 spot-check ...; intermediate family members (32B) were not priced`
- Replace: `Language-pool results are reported for the 8B at TP1, with a TP2$\times$2 spot-check on the burst window and a 235B-TP8 spot-check`
- DB: `SELECT run_id, tp FROM provenance.runs WHERE tp=2 AND pool='language';` → `sweeps:llm_burst1_aic_tp2_s1` exists and is thesis-era; the chapter reports it itself at :265 ("a TP2×2 shape passes the same window at 748 ms"). The limitation sentence understates the chapter's own coverage.
- **Leave the 32B clause untouched** (R26).

### 1.5 apendice.tex — 6 edits

**[E16] apendice.tex:28 — C: supporting — V: THESIS_WRONG (revised from INSUFFICIENT_DATA)**
- Current: `the AIC data-collection and GEMM-validation runs pin the GPU clocks (SM \SI{2407}{\mega\hertz}, memory \SI{14001}{\mega\hertz})`
- Replace: `the AIC data-collection and GEMM-validation runs pin the GPU clocks via \texttt{nvidia-smi -lgc 2400,2400 -lmc 14001} (delivered SM 2377--2400\,\si{\mega\hertz}, MEM \SI{13801}{\mega\hertz}; the AIC cost model itself is parameterised at the \SI{2407}{\mega\hertz} boost reference)`
- Source: `collector_artifacts/phaseE_physical_anchor/ENCODER_ANCHOR_SUMMARY.md:92` — "The user locked the clock (`nvidia-smi -lgc 2400,2400 -lmc 14001`) → settled at SM 2392 / MEM **13801**".
- DB: `SELECT DISTINCT sm_clock_mhz FROM provenance.collector_encoder_fn ORDER BY 1;` → 2377, 2385, 2392, 2400, 2887. **No archived reading is 2407.** 2407 MHz is the RTX 5090 boost-spec figure the AIC cost model assumes (`verify-fabel.md:26`; `phaseB_batch_validation/bench_vit_batches.py:13` calls it "the 2407 MHz lock reference"). The requested SM was 2400 and the delivered memory clock 13801.
- **Do not apply this to :124** (R28) — that sentence states the *target* 2400/14001, which is literally the command.

**[E17] apendice.tex:179 — C: headline — V: THESIS_WRONG (upheld)**
- Current: `The HuggingFace-transformers eager forward (SDPA attention) runs $1.36$--$1.61\times$ above the composition, rising with $N$;`
- Replace: `runs $1.36$--$1.62\times$ above the composition, rising with $N$ above $N{=}8$;`
- DB: `SELECT n_images, ratio_meas_over_aic FROM provenance.collector_encoder_fn WHERE source_path LIKE '%anchor_dense_sdpa_2400%' AND n_images IN (1,8,32,64);` → 1.3885, 1.3613, 1.5843, **1.6170**.
- Every candidate basis exceeds 1.615: unrounded 511.573/316.369 = 1.61701; published cells 511.6/316.4 = 1.61694; 5×50 anchor 1.6160; oneworker burst5 1.6171; dense-sweep max over N≤64 = **1.6208**. A range upper bound must **contain** the measured maximum. Secondary: "rising with N" is false from N=1→8 (1.3885 → 1.3613).
- Resolves the intra-thesis disagreement with aiconfigurator.tex:274 (1.62). See §3.4.

**[E18] apendice.tex:196 — C: headline — V: THESIS_WRONG (upheld)**
- Current: `... (residual up to $+12.7\%$ inside the regime, growing to $+21.8\%$ only past the FIFO cap at $N{=}512$).`
- Replace: `... growing to $+21.8\%$ only past the FIFO cap at $N{=}64$, reaching that value at the $N{=}512$ sweep endpoint.`
- Source: `collector_artifacts/phaseE_physical_anchor/winsched_ctrl_aic.stats.json → encoder_batch_images` = **64** (images_per_batch p90 = p99 = 64). The figure caption at :168 and the regime definitions at :116/:196 all put the cap at 64; N=512 is the sweep **endpoint**.
- **All three percentages verify and must be kept**: max residual +12.7094 % at N=52 over the 64 points with N≤64; +21.767 % at N=512.

**[E19] apendice.tex:89 — C: supporting — V: THESIS_WRONG (upheld, fix revised)**
- Current: `The foundation-model rows are uniformly near-white --- within a few percent of the per-cell optimum everywhere --- while the baseline rows darken as bins shrink.`
- Replace: `The Chronos-2 and Toto-2 rows are uniformly near-white --- within $3\%$ of the per-cell optimum in every cell --- and TimesFM within $6\%$ outside the \SI{1}{\second} column, where it reaches $22\%$ above best on images; the baseline rows darken as bins shrink.`
- DB (max rel-to-column-best over `forecast_metrics`, `candidate='point' AND h=-1 AND span='common'`): **toto ≤ 1.006**, **chronos ≤ 1.030**, timesfm 1.010 (1 min) / 1.030 (30 s) / 1.032 (45 s) / 1.056 (15 s) / **1.220 (1 s)** — driven by (images,1 s) 1.2198, (ctx,1 s) 1.1139, (gen,1 s) 1.0965. Baselines at 1 s: ewma ≤ 1.479, naive 1.588, holt_winters 2.198.
- **Write 3 %, not 2 %**, for the Chronos+Toto blanket (chronos reaches 1.030). On a shading scale reaching 2.20, a cell at 1.22 is not white.

**[E20] apendice.tex:90 — C: supporting — V: DEFINITIONAL (upheld)**
- Current: `Toto-2 with covariates carries most column wins at \SI{15}{\second} and \SI{1}{\second}; Chronos-2 and TimesFM take the coarse-bin columns.`
- Replace: `Toto-2 carries every column win at \SI{15}{\second} and \SI{30}{\second} and three of four at \SI{1}{\second} (with covariates except on images); Chronos-2 and TimesFM take three of four at \SI{1}{\minute} and two of four at \SI{45}{\second}. Every one of these margins is within $2\%$ of the column best.`
- DB (argmin per column over `forecast_metrics`): 15 s → toto-cov ×4; 1 s → toto-cov (ctx, gen, requests), toto-uni (images); **30 s → toto ×4**; 45 s → chronos-uni (ctx, requests), toto-cov (gen), toto-uni (images); 1 min → timesfm-uni (ctx), toto-cov (gen), chronos-cov (images), chronos-uni (requests). Margins: chronos max rel 1.017, timesfm 1.010. No number is wrong; the second clause over-scopes.

**[E21] apendice.tex:191 — C: supporting — V: DEFINITIONAL (upheld, fix revised)**
- Current: `\texttt{torch.compile} (max-autotune) accelerates the HuggingFace forward by $1.2$--$1.4\times$`
- Replace: `... by $1.2$--$1.4\times$ in the batched regime ($N{\ge}8$; only $1.06$--$1.17\times$ at $N{\le}6$)`
- DB (SDPA `anchor_dense_sdpa_2400` ÷ `vit_compile_dense`, same N): N=1 1.1213, 2 **1.0627**, 4 1.1514, 6 **1.1708**, 8 **1.2035**, 12 1.3210, 16 1.3411, 24 1.3986, 32 1.3646, 48 1.3751, 64 1.3802, 96 1.3897, 128 **1.4022**.
- At N≥8 the range is 1.2035–1.4022, bracketing exactly to the published 1.2–1.4. **Small-N band is 1.06–1.17, not 1.06–1.15** (R46). Scope only; no number changes.

*(apendice.tex:124, :150, :151, :185, :275, :301, :348 — all overturned to CONFIRMED; R28, R7, R8, R11, R27, R40. apendice.tex:215 upheld INSUFFICIENT_DATA — no edit, see §5.6.)*

### 1.6 trace-eda.tex — 1 edit

**[E22] trace-eda.tex:246 (sentence at :244) — C: headline — V: THESIS_WRONG (upheld)**
- Current: `Pearson $r$ against request rate is $0.36$ for images versus $0.81$ for decode`
- Replace: `$0.35$ for images versus $0.81$ for decode`
- DB: `SELECT script, metric_path, value_num FROM provenance.eda_metric WHERE metric_path IN ('gen_signal.constant_fraction_vs_req.r2','pearson_1min.gen_vs_req','pearson_1min.img_vs_req');` → 0.6535040521227362 (→ 0.654 ✓), 0.8121338734126078 (→ 0.81 ✓), **0.3546002012649865 (→ 0.35)**.
- Four adversarial rescue attempts all failed: no ordinary convention reaches 0.36 from 0.3546; no alternative Pearson row exists; the caption fixes the scope as 1-minute windows; `d_signals` and `e_comprehensive` agree (0.3546 / 0.355). The published 0.36 is reachable only by re-rounding the already-3-dp 0.355 — the forbidden round-twice pattern (R5).
- **Bonus consistency:** 0.35² = 0.1225 now matches the quoted image-side R² = 0.123 at :241 to three digits; 0.36² = 0.1296 did not.

*(trace-eda.tex:38, :47, :136, :317 — all overturned to CONFIRMED; R38, R36, R37. :411 overturned to CONFIRMED with a recommended rhetorical weakening — see §3.6 [C14].)*

### 1.7 validation.tex — 2 edits

**[E23] validation.tex:122 — C: headline — V: THESIS_WRONG (revised from INSUFFICIENT_DATA)**
- Current: `Mixed prefill+decode passes, the only samples that inform aggregated capacity, are rare at calm load: zero arrived in five minutes at 2\,req/s, leaving the capacity model unready.`
- **Weaken, do not restate a new headline number:** `Mixed prefill+decode passes, the only samples that inform aggregated capacity, are rare at calm load: only a handful arrive --- across the archived runs 2--3 of the first ${\approx}200$ tracking-mode samples over five minutes at ${\approx}2$\,req/s were mixed (${\approx}1\%$) --- too few to make the capacity model ready.`
- Source: the tracking-mode sampler **is** archived. Classifying every `base._log_fpm` record by `sched(prefill_tok>0 AND decode_kv>0)` over the first 300 s of each archived run: **live_fc n=184, mixed=2** (first at +24.9 s), pure_prefill 3, pure_decode 138, idle 41; **live_re n=24, mixed=2**; **verify_flag n=207, mixed=3** (first at +209.9 s). Command: `zcat simulation/results/live51/live_runs/*/planner.log.gz | grep 'base._log_fpm'`.
- The parity patch adds a **separate** drain-all subscriber (`planner_live_patch._collect_fpm`), so `base._log_fpm` is unaffected by it — the pre-fix probe run need not be archived for this to be decidable.
- Rate corroborated: `SELECT requests, span_s FROM provenance.windows WHERE window_name='burst3';` → 3093/1619.7 = **1.910 rps**; `live_fc/profile_export_aiperf.json request_throughput.avg` = 1.8968 rps. "2 req/s" is a fair rounding.
- The "unready" consequence survives (`correction_ready_buckets=0`); only the literal **zero** does not.

**[E24] validation.tex:72 — C: incidental — V: THESIS_WRONG (surfaced by the intro review)**
- Current: reactive provisioned-replica-time delta printed as `$-7.6\%$`
- Replace: `$-7.7\%$`
- Sources, both unrounded: live 1798.852786 replica-s, from integrating `n_live` piecewise over `t_wall` in `simulation/results/live51/live_runs/live_re/manager.jsonl` (span 1644.5 s; reproduces the table's printed 1,799 to the unit); offline `SELECT decode_worker_seconds FROM provenance.llm_run_summary WHERE run_id='live:twin_re';` → **1948.1905283120368**.
- Arithmetic: (1798.852786 − 1948.1905283)/1948.1905283 = **−7.6654 % → −7.7 %**.
- Does **not** touch the "within 8 %" claim at intro.tex:539 / validation.tex:84, which holds either way (companion forecast delta −5.2635 %).

*(validation.tex:43, :140, :161 — overturned or rejected; R30, R31, R2.)*

### 1.8 related.tex + intro.tex — 2 edits (one applied at 2 sites)

**[E25] related.tex:206 — C: low — V: DEFINITIONAL (upheld)**
- Current: `Chapter~\ref{cap:trace-eda} finds the same signatures (Fano factor growing by nearly three orders of magnitude with window size, Hurst exponents up to ${\approx}0.93$) in a multimodal inference workload's demand signals, strongest in the vision signal.`
- Replace: `... finds the same signatures (a request-arrival Fano factor growing by nearly three orders of magnitude with counting-window size, from 1.8 at \SI{1}{\second} to 938 at \SI{1}{\hour}) and, across the per-pool demand signals, Hurst exponents up to ${\approx}0.93$, highest in the vision signal.`
- DB: `SELECT script, metric_path, signal, value_num FROM provenance.eda_metric WHERE metric_path ILIKE '%fano%' OR metric_path ILIKE '%hurst%';` → **5 Fano rows, all `signal IS NULL`** (1 s 1.763888, 10 s 7.990739, 1 min 31.864022, 10 min 186.434106, 1 h 938.123426); **7 Hurst rows, each with a signal** (images 0.932486 = argmax, gen 0.905888, ctx_multimodal 0.867544, ctx 0.859177, requests 0.828947, ctx_text_only 0.756944).
- Growth ratio 938.123426/1.763888 = 531.85 → log₁₀ = **2.726 decades** ("nearly three orders" ✓); 0.9325 → ≈0.93 ✓. **No number changes.** The only unsupported attachment is "strongest in the vision signal" applied to Fano, for which no per-signal Fano exists.

**[E26/E27] related.tex:312 AND intro.tex:167 — C: medium — V: THESIS_WRONG (upheld, magnitude revised)**
- Current (related.tex:312): `the vision pool's image rate: the burstiest of the four ... and ramping to peak within replica cold-start times in the fast half of its bursts`
- Current (intro.tex:167): `the fast half of the bursts arrive too fast`
- Replace at related.tex:312: `... in its fastest bursts (a third of the episodes reach peak within two minutes, the fastest within one, against replica cold starts of tens of seconds to minutes)`
- Replace at intro.tex:167: `a third of the bursts arrive too fast`
- Sub-claim (a) **"burstiest of the four" is CONFIRMED**: `SELECT metric_path, signal, value_num FROM provenance.eda_metric WHERE metric_path LIKE 'multi_resolution.%.cv2';` → images is the maximum at **all 17 resolutions** (1 s 25.71 vs 4.83/4.59/1.07; 60 s 3.83 vs 0.85/0.40/0.32; 3600 s 2.33 vs 0.43/0.18/0.16). **Keep it.**
- Sub-claim (b) is not supported. Onsets over the 18 published episodes (`eda_metric`, `episodes[i].onset_min`), sorted: 1, 2, 2, 2, 2, 2, 3, 6, 6, 7, 11, 13, 26, 35, 48, 53, 60, 404 → min 1, p10 1.7, **p50 6**, p90 51.6. Longest lead the archive ever exercises: `SELECT DISTINCT lead_s FROM provenance.ewma_ablation_cell;` → max **165 s (2.75 min)**. Qualifying fraction: `SELECT count(*) FILTER (WHERE onset_min<=2), count(*) FROM provenance.eda_burst_episode WHERE onset_min IS NOT NULL;` → **8/24 = 33.3 %**; on the published 18-episode set **6/18 = 33.3 %**. Not half.
- The thesis already contradicts itself in this direction at trace-eda.tex:293 and closedloop.tex:168. This **weakens** "half" to "a third"; the claim survives, its magnitude does not.
- **Do not write "~10 %" or "1.7 minutes"** (R44), and do not frame the comparison as "cold-start *leads* of 15–165 s" — that swaps a physical quantity for a simulation knob.

*(related.tex:168 upheld INSUFFICIENT_DATA — optional scope narrowing only, §5.3.)*

### 1.9 apendice_ecosystem.tex — 4 edits

**[E28] apendice_ecosystem.tex:144 — C: headline — V: cross-chapter [4a]**
- Current: attributes the `live_fc`/`live_re` runs and their aiperf exports to `cap:closedloop`.
- Replace the cross-reference with `cap:validation` (defined at validation.tex:2-4, :31). Clearest cross-chapter defect in the consistency pass; unaffected by adversarial review (which reviewed only the single INSUFFICIENT_DATA claim in this appendix).

**[E29] apendice_ecosystem.tex:127 — C: supporting — V: internal arithmetic (dangling reference)**
- Current: `\texttt{aiconfigurator} 0.10.0 (editable, data branch) and \texttt{aiperf} 0.11.0 (Table~\ref{tab:ap-env}).`
- Fix: add an `aiperf & 0.11.0 & live closed-loop client (TTFT/ITL/goodput)` row to `tab:ap-env` (apendice.tex:35-48, currently 8 body rows, **no aiperf row**), or drop the parenthetical. Adding the row is preferred — aiperf is load-bearing at :108-109 and :143-144.
- Incidental corroboration from the adversarial pass: `aiconfigurator 0.10.0 (editable)` is now directly evidenced by `ai-dynamo/dynamo/.venv/.../aiconfigurator-0.10.0.dist-info` with `direct_url.json editable=true`. The ledger string `AIC_VER=0.19.0` is a **data-branch tag**, not the package version — do not read it as a contradiction.

**[E30] apendice_ecosystem.tex:121 — C: incidental — V: internal arithmetic (git-tag fact)**
- Current: `only \texttt{-rc} release-candidate tags ahead of some minors`
- Replace: `only \texttt{-rc} release-candidate tags ahead of a few patch releases`
- Check: tags between v0.1.0 (2025-03-17) and v1.0.0 (2026-03-13) contain exactly three `-rc` tags — v0.8.1-rc0, v0.9.1-rc0, v0.9.1-rc1 — **all preceding patch releases**. No 0.x minor carries one. Explicitly **not** rejected on substance by the adversarial pass.

**[E31] apendice_ecosystem.tex:166-167 — C: low — V: cross-chapter [4b]**
- Current: `a full-serving-path run with real GPU engines behind aiperf remains future work`
- **Weaken/scope, do not delete:** aiperf is already in live use two paragraphs above. Write `a full-serving-path run with real GPU \emph{engines} (rather than TP2 mockers) behind aiperf remains future work`.

*(apendice_ecosystem.tex:125 — overturned to CONFIRMED; R41.)*

### 1.10 closedloop.tex — 2 edits (internal arithmetic only)

All 15 provenance mismatches were overturned. Both edits below come from the internal-arithmetic pass and
were not contradicted by any chapter review.

**[E32] closedloop.tex:230 — C: headline — V: internal arithmetic (self-contradiction)**
- Current: `costs 1.09$\times$ static, with no rating below $\rho{=}25$ bringing it under the static fleet ($\rho$-frontier 1.32/1.09/0.94/0.83$\times$ at $\rho\in\{10,15,20,25\}$)`
- Replace: `costs 1.09$\times$ static, and only at $\rho{\geq}20$ does it come under the static fleet at all ($\rho$-frontier 1.32/1.09/0.94/0.83$\times$ at $\rho\in\{10,15,20,25\}$)`
- Inline arithmetic: the parenthesis itself gives **0.94× at ρ=20 < 1.00**, contradicting "no rating below ρ=25".

**[E33] closedloop.tex:240 — C: headline — V: internal arithmetic ("to the digit" is false)**
- Current: `The Chronos control reproduces the committed figures to the digit throughout (burst3 \SI{589}{\milli\second}; week 0.62$\times$; $\rho$-frontier 0.89/0.62/0.48/0.40$\times$; ...)`
- **Weaken:** `reproduces the committed figures to within run noise ($<1\%$) throughout (burst3 \SI{588}{\milli\second}; week 0.62$\times$; $\rho$-frontier 0.89/0.62/0.48/0.40$\times$; the p50 arm fails at \SI{2735}{\milli\second})`
- Inline arithmetic: 589 vs the committed 588.4 floor (316.4 + 272); p50 2759 vs the committed 2,735 at :470 → **+0.88 %**. Only "week 0.62×" and the ρ-frontier are digit-exact. See §3.3.

---

## 2. DB CORRECTIONS TO MAKE

In every case below **the thesis is right and the database is stale or absent.** No thesis edit.
Groups §2.1-§2.8 carry over from the first pass with adversarial amendments; §2.9-§2.12 are new,
surfaced by chapter reviews that went to disk when the DB came up empty.

> **§2.1 APPLIED 2026-07-20** — `provenance/schema/22_corrections.sql` (idempotent; re-runnable).
> All four outstanding actions are done, each as a *visible supersession* (sibling `_corrected` column +
> `provenance.grid_correction` row + `_effective` view), never an overwrite:
> 1. `grid_window.overprovision_vision_x` steady24h **8 → 4**;
> 2. the burst windows recomputed: 2.67/2.0/2.29/2.29/1.0/2.67 → **1.33/1.0/1.14/1.14/1.0/1.33**;
> 3. `grid_run_summary.static_encoder_workers` **16 → 8** (new `grid_run_summary_effective`);
> 4. `silicon_multiworker` burst5 — **Q8 ANSWERED**: it is the *same* artifact, not an independent
>    confirmation (`rerun-stability-e2e.md:116-129`). `collector_multiworker_window` burst5
>    `aic_feasible_cstar` **16 → 8**, `silicon_feasible_cstar` **16 → 15**, `worker_inflation_x`
>    **1.0 → 1.88**, `silicon_p99_at_aic_cstar` **783.6 → 1257.1**. The **fleet** silicon `C* = 16` is
>    UNCHANGED — only its provenance moves, from burst5's artifact to burst2's genuine measured knee.
>
> §2.2–§2.12 are ingests of artifacts not yet in the store and remain **OUTSTANDING**,
> except as amended below. **§2.4, §2.5 and §2.11 are APPLIED (GROUP C, 2026-07-20).**

> **GROUP C APPLIED 2026-07-20** — §2.4, §2.5, §2.11.
> Schema `provenance/schema/25_group_c.sql` + `26_group_c_checks.sql`; loader
> `provenance/loader/load_group_c.py` (kind **K31**). New checks **C401–C407, all passing**.
> Idempotent: verified over three consecutive passes (second and third load 0 files / 0 rows).
>
> **§2.4 — the derivation is now recomputable, not just its outputs.** Three tables:
> `capacity_belief_sample` (5,445 planner ticks from all 20 riders44 logs, degenerate ticks
> **flagged, not dropped**), `capacity_knee_probe` (12 rungs), `capacity_derivation` (3 rows).
> Everything published reproduces from the archived artifacts:
> * belief = **10.0700** exactly = median engine_rps over the **86** non-degenerate ticks of
>   `fc_lead60.log`. **The population is part of the claim**: pooling all 20 logs gives 8.94 and
>   the four `fc_lead*` logs give 9.84, so the ledger's "median engine_rps" is only 10.07 for
>   this one run. Recorded rather than smoothed.
> * burst1 `r_tail` = 3.2466/2 = **1.6233** req/s (s=1.5 PASS 905.86 ms; s=2.0 → 2.1643 FAIL
>   1078.61 ms) → published **1.62**. C402 additionally asserts a higher rung *failed*, without
>   which the "knee" would only be a lower bound on the knee.
> * burst4 bracket **[1.2588, 1.4386]** (6.22 FAIL 1103.91; 7.0 PASS 792.01; 8.0 PASS 753.79) →
>   published **[1.26, 1.44]**. burst4 is only ever *bracketed*, never measured — `r_tail_method`
>   records this, which is why the thesis correctly prints an interval for it and a point for burst1.
> * scale = 10.07/1.2588 = **8.0** adopted; the strictly-required 10.07/1.4386 = **7.0**; margin
>   **1.1429** → published "≈14 %".
> * The two pre-bugfix burst4 probes are ingested `is_superseded=true` with the reason, per the
>   never-destroy rule, rather than omitted.
>
> **One honest discrepancy, recorded not reconciled:** the published belief band "p10–p90 8.5–12.8"
> reproduces under the *order-statistic* percentile convention (8.45 / 12.83) but **not** under
> linear interpolation (8.46 / **12.66**, which rounds to 12.7). Both are stored side by side
> (`belief_p10_rps`/`belief_p90_rps` vs `belief_p10_disc_rps`/`belief_p90_disc_rps`) so the reader
> can see which the thesis used. **No thesis edit**: the band is a dispersion note, and the
> derivation consumes only the median, which is 10.07 under every convention tested.
>
> **§2.5 — ladder configuration backfilled.** `lead_s=60`, `window_name='burst1'`, `tp=2` on the
> four `riders:ladder_*` rows, from `run_44_riders.sh:15,32`. The loader writes **only over NULL**
> and aborts on any non-NULL value; all 12 changes are recorded in the new
> `runs_config_backfill` with file:line evidence, and **C405** asserts every one replaced a NULL
> and still matches `runs`. Generating command recorded in `grid_command` (4 rows) plus a
> `ledger_entry`. Ladder values reproduce: gpu_hours 18.638/19.199/19.413/20.379 → published
> 18.6→20.4; TTFT p99 1615.49–1619.61 → published 1,616–1,620.
>
> **§2.4/§2.5 COMPLETION 2026-07-20** — `provenance/schema/29_riders_probe_config.sql`;
> `load_group_c.py::_load_probe_config`. The first GROUP C pass backfilled configuration on the
> four *ladder* rows only, and left the **sixteen non-ladder riders runs — the derivation's own
> INPUT runs — carrying NULL** `window_name`/`lead_s`/`n_replicas`/`arrival_speedup`. The effect
> was silent: `capacity_knee_probe.window_name` said `burst1`, `runs.window_name` said nothing, so
> `runs WHERE window_name='burst1'` returned *none* of the probes that back closedloop.tex:328–337.
> Now backfilled under the same NULL-only rule (51 further `runs_config_backfill` rows, **63 total
> over 6 columns**), plus `policy`/`n_replicas` on the ladder rows. Every value is re-derived from
> the archived artifact, not asserted:
> * `window_name` from each report's own `num_requests` against `provenance.windows` (64,804 =
>   burst1, 25,639 = burst4, both unique) — new check **C408**.
> * `arrival_speedup` on the three `tp2knee_*` rungs confirmed **twice**: it equals
>   `capacity_knee_probe.arrival_speedup` *and* compressing the burst1 span by it reproduces the
>   report duration to within 0.008 % (29,939.3 / 1.25 / 1.5 / 2) — new check **C409**.
>
> **C405 was rewritten**, not weakened: its original hardcoded `CASE column_name WHEN 'lead_s' …
> WHEN 'tp' … WHEN 'window_name' … ELSE NULL` resolved the three new columns to NULL and so
> reported healthy backfills as defects. Replaced with a total `to_jsonb(r)->>column_name` lookup
> (numeric-aware compare); it now covers **every** column of `runs`, catches everything the old
> one did, and was confirmed red under an injected overwrite (rolled back). **Deliberately NOT
> filled:** `lead_s` and `policy` stay NULL on the three `tp2knee_*` rows — no archived file states
> a startup_time or a planner mode for the knee probes, and guessing would invent a dimension. New
> view `v_riders_probe_config`. Idempotent over three consecutive passes; C401–C403, C405–C409 all
> green; loader `selftest.py` green.
>
> **§2.11 — all three artifacts ingested.**
> 1. AIC speed-of-light fallback → `collector_scalar` (11 rows): SOL 0.00605 ms vs rtx_5090
>    measured 0.03580 ms = **5.9174×** → published "≈5.9×" (intro.tex:311).
> 2. Fabric conditional → `handoff_gbps`/`handoff_rtt_ms` **promoted from the `metrics` jsonb to
>    first-class columns** on `encoder_run_summary` (1,117 rows), plus `v_fabric_sensitivity`.
>    §2.11's premise that this "needs a bandwidth dimension" was half-right: the ds4 stats files
>    **were already ingested** (`misc:fc_p90_L30_ds4` carries handoff p99 1087.406 and
>    encoder_delay p99 1403.774 exactly); what was missing was only that the bandwidth was
>    unqueryable. **No re-ingest was needed and none was done.**
> 3. Factoring invariance → `encoder_factoring_probe` (8 rows), keyed on the
>    `(batch_size, images_per_request)` pair that `collector_encoder_fn` cannot express.
>    All deltas 0.000000 ms. `f(1)`=8.162 / `f(64)`=316.369 ms match twopool.tex and are
>    independently corroborated by `collector_encoder_fn.aic_pred_ms`; the contemporaneous note's
>    7.822/314.498 is an earlier AIC data version and is labelled as such, not discarded.
>
> **NEW DEFECT FOUND, and deliberately left failing-visible rather than hidden (C407).** C404 was
> first written as "no run at 25 Gbps violates the 1 s bound on handoff alone" and **failed: 12 do.**
> All 12 are `g6:u896*` — a post-manuscript *defence* resolution sweep whose payload is 784
> post-merge tokens/image (896²), 4× the thesis's 196 (448²), so at 25 Gbps they carry the same
> bytes/s as the thesis's 6.25 Gbps arm and land on the identical 1087.406 ms. **This confirms the
> physics rather than contradicting the thesis claim**, which is about the uniform-448²
> configuration. C404 is therefore scoped to thesis runs *and* C407 pins the excluded set to
> exactly those 12, so a future thesis-run violation goes red even though C404 stays green.
> **The underlying defect is real and is NOT fixed here (out of §2.11 scope):**
> `encoder_run_summary.image_px` reads **448 on all 12 g6 rows** although the mixture is 896² —
> the simulator emits `image_px` as a default and the true payload lives in the un-ingested
> `<stem>.jsonl.g6mix.json` sidecar. **`image_px` must not be used to reason about g6 payload.**
> Ingesting those sidecars would let C404 be restated as one physical law with no exclusion at all.
>
> **§2.8 + §2.11 RE-VERIFIED AGAINST THE LIVE DB 2026-07-20** (independent pass; the notes above
> were re-derived, not trusted). All eight checks — C010 and C401–C407 — executed from
> `check_definition.sql_text` and returned **passed = true**. Values confirmed digit-exact:
> ewma_cal_coverage eval add 0.9012529 / mult 0.8783340 / wsc 0.8765972 / native 0.9288860
> (the add/mult/wsc spread *is* closedloop.tex:218's 0.88–0.90); C010 re-measures **0 point
> disagreements and 0 p90 ties** over 38,388 aligned rows, which is the fact that makes coverage
> the only discriminator between the three arms; SOL 0.00605 vs 0.03580 → 5.917355×; ds4
> handoff p99 **1087.406** / encoder_delay p99 **1403.774** at 6.25 Gbps; all 8 factoring rows
> 316.369 ms with delta 0.000000. `load_group_c.py` re-run twice → **0 files / 0 rows** both passes.
>
> **One standing-rule defect found and fixed:** the Group C ingest left 5 columns without a
> `COMMENT`, among them `encoder_factoring_probe.probe_id` (created *by* §2.11) and
> `encoder_run_summary.image_px`. The `image_px` g6 warning three lines above existed **only in
> this markdown**, where a SQL-only reader would never meet it; it is now a COMMENT on the column.
> Fix: `provenance/schema/26a_group_c_comment_gaps.sql` (idempotent, applied twice).
> **Still not done, stated plainly:** `encoder_run_summary` retains 20 uncommented columns, all
> pre-existing and outside §2.8/§2.11 scope; the `g6mix` sidecars remain un-ingested, so C404
> keeps its thesis-run scoping and C407 keeps its 12-row exclusion pin.
>
> **GROUP A APPLIED 2026-07-20** — §2.2, §2.7.
> Schema `provenance/schema/23_runtime_build_and_actuation.sql` + `24_actuation_correction.sql`;
> loader `provenance/loader/load_runtime_build.py` (kinds **K40/K41/K42**). New checks
> C507–C509, all passing. Idempotent (digest-verified over two full passes); `--only K7
> --reload` reproduces the corrected state exactly. **Two premises in this section were
> themselves wrong, in the direction that matters:**
>
> 1. **§2.7's premise that the target-time grid is not ingested is FALSE.** It was ingested
>    MISLABELLED. Of the 1,172 `factorial_cell` rows only 600 are issue-time; 572
>    (`results_44.jsonl` 560 + `pilot_results.jsonl` 12) are the target-time harness carrying
>    an issue-time label, and were therefore being **silently pooled** with the issue-time
>    rebuild inside `current_factorial` and every view built on it — precisely the failure
>    §2.7 exists to prevent. Root cause: `loaders.load_factorial` inferred actuation from the
>    substring `"target"` in the *path*, which neither file contains. Corroborated before any
>    document was consulted, by check C504's own note (`factorial_cell readiness: strict=300
>    warm=300 NULL=572` — readiness is an issue-time-only axis) and by the lead sets
>    ({15,30,45,300} vs {15,30,45,165}). Applied as a visible supersession: actuation
>    relabelled, `is_current=false`, run_id renamed `factorial:issue-time:*` →
>    `factorial:target-time:*` (the wrong label was baked into the primary key), all 572 old
>    identifiers preserved in the new `provenance.run_id_alias`, reasoning in
>    `provenance.ingest_correction` (IC001/IC002). No measured value touched.
>    `loaders.actuation_of()` now classifies by explicit artifact identity so a `--reload`
>    cannot re-mint the mislabelled rows. Sweep manifests ingested as
>    `provenance.sweep_manifest{,_cell}` (5 manifests / 747 cells), with
>    `sweep_manifest_coverage` turning "requested but never returned" into a fact:
>    cells_44 560/560, wave1 60/60, pilot 12/12, **cells_week_canary 0/3** (all three errored
>    in the converter), **cells_week 0/112**. C505 widened `{issue-time}` →
>    `{issue-time, target-time}`: an EXTENSION its own note anticipated, not a relaxation; a
>    third value still fires.
>    *Flagged, not hidden:* the target-time reactive ρ=15 cells at leads 15/30/45 are
>    superseded AS A GRID but still back thesis Tab. 7.3 and the A2 animation, so a Tab-7.3
>    query must now filter `actuation='target-time'`; those 16 runs carry `runs.feeds` naming
>    the table they still feed.
>
> 2. **§2.12's "runtime_build='wheel' is currently unattested" is FALSE.** There is a wheel
>    marker. The KVBM builder logs `Using Lineage inactive backend (Tick)` on dynamo 1.3.0 and
>    the same line *without* the suffix on the 1.2.1 wheel — a line every replay emits
>    regardless of timing model, whereas §2.12's `RustAicCallback` probe is emitted only by the
>    source build's AIC path and so cannot separate "wheel" from "no AIC at all". Cross-checked
>    over all 1,219 archived logs: **498 agree, 0 disagree**; the marker additionally attests
>    **119 wheel logs** and one source log the other probe is blind to by construction
>    (`srcbuild/run_poly.log` — a poly run executes no AIC callback).
>    `runs.runtime_build` is now **495 source / 110 wheel / 2,446 NULL** (was 493 / 0 / 2,556);
>    `sweeps:llm_head2k_{poly,aic}_s1` = wheel 1.2.1, `srcbuild:*` = source 1.3.0, so R4/R12
>    and [E14] are a one-line query. The column and its `'source'|'wheel'` vocabulary are
>    §2.12's and were adopted rather than duplicated; this pass added only
>    `runs.runtime_build_evidence` (which log attests the row). The 2,446 NULLs are deliberate
>    — encoder-pool / pure-Python runs never load a dynamo runtime, and runs without an
>    archived log have no evidence. **Never guessed**; C509 fails if a build is ever asserted
>    without evidence.
>    The srcbuild reports are ingested (`srcbuild:llm_head2k_{poly,aic}_src`; K1 had missed them
>    because its glob is `*.report.json` and these are `*_src.json`) and reproduce **every**
>    published `tab:sim-poly-aic` cell exactly. Supersession is METRIC-scoped
>    (`provenance.metric_supersession`, 12 rows) rather than run-scoped, because the wheel rows
>    remain the legitimate s=1 anchor of the Phase-2 speedup knee sweep; both sides and the
>    published value are resolved by `provenance.llm_head2k_poly_aic_effective`.
>
> **Not done here:** §2.7's later bullets (the 96-cell issue-time week surface, the p50 half).
> `week_matrix` results are not in `factorial_cell` at all — which cells_week's 0/112 coverage
> row now makes visible — but ingesting them is a separate pass.

> **§2.7 WEEK-SURFACE bullets APPLIED 2026-07-20.** The separate pass above is done.
> Schema `provenance/schema/30_week_surface_coverage.sql`; loader
> `provenance/loader/load_week_matrix_cells.py` (kind **K7w**); three edits in
> `provenance/loader/loaders.py`. Both families are now in `factorial_cell`:
> - **week_matrix — 112 cells (96 forecast + 16 reactive), target-time.** It is the one
>   factorial family with no `*_results.json`: `run_week_matrix.sh` deletes the per-request
>   jsonl and keeps only `<tag>.jsonl.stats.json`, so `load_factorial`'s results-file glob
>   never saw it. The 112 spine rows already existed (K3+K4, repair3); what was missing was
>   the graded PROJECTION, now built from the stats files. `cells_week` coverage 0/112 → 112/112.
> - **week_surface_issuetime — 96 cells (BOTH p50 and p90), issue-time.** This file WAS
>   ingested, silently as K7 `n_rows=0`: its flat records carry no `window` key, so
>   `_norm_cell` rejected all 96 without raising. `_norm_cell` now handles that shape and
>   takes the window from the explicit `_FAMILY_DIMS` identity table. New manifest
>   `cells_week_surface_issuetime` 96/96.
>
> ACTUATION was assigned by `loaders.actuation_of()` — the explicit identity table extended
> with `_TARGET_TIME_DIRS` (week_matrix → target-time; evidence: `run_week_matrix.sh:5` uses
> `forecast_schedule.py`, leads {15,30,45,300}) — **never** a path substring, the heuristic
> that mislabelled 572 cells. week_surface_issuetime → issue-time
> (`forecast_schedule_issuetime.py`, leads {15,30,45,165}); its successor docstring states
> "the archived run_week_matrix.sh was target-time at L=300"
> (`run_44_week_surface_issuetime.py:6-7`). week_matrix is target-time and therefore
> SUPERSEDED: its 112 runs are demoted `is_current=false`, so **C507 still holds —
> `current_factorial` contains exactly one actuation (issue-time)**. `factorial_cell`
> 1172 → 1380 rows; `current_factorial` 600 → 696 (+96, the issue-time surface only). New
> check **C510** (no factorial *results* file ingested with 0 cells) added and passing;
> loader idempotent (run twice, byte-identical); `selftest.py` 3/3 green. No thesis number
> changed — this is a data-layer completion.

> **GROUP B APPLIED 2026-07-20** — §2.3, §2.6, §2.10.
> Schema `provenance/schema/23_stage_conditional.sql`, `24_live_arm.sql`,
> `25_reprice_harness.sql`; loader `provenance/loader/load_live.py` (kind **K50**,
> registered in `main.py`). 13 new checks C210–C213, C220–C225, C230–C232, all passing.
>
> **§2.3 was already satisfied — the OUTSTANDING status was stale.** All four reprice
> stats files were ingested long ago by **K21**
> (`load_collector_silicon.load_encoder_stats_file`, reached by its
> `glob(phaseE_physical_anchor/*.stats.json)` registry line) into
> `provenance.collector_encoder_stats`. Verified present and exact: 605.612 / 589.301 /
> 692.008 / 646.943 ms, `provisioned_worker_seconds` 2,410,754.7 (both winsched arms) and
> 3,869,278.8 (both static-C8 arms), `encoder_batch_images` = 64, and
> `collector_kernel_ledger` loaded. **No re-ingest was performed** — re-ingesting correct
> rows is pure risk. What was added instead is the thing §2.3 actually lacked: the numbers
> as *recomputable checks* (C230 the four published p99s under rounding, C231 the
> reprice-pair invariant that both arms share a schedule and so share
> `provisioned_worker_seconds`, C232 the 0.388 % harness-vs-simulator delta against the
> thesis's own 0.5 % bound), plus the 2×2 view `provenance.v_reprice_harness`.
>
> **§2.6 was already ingested — also stale — but had a real residual.** The
> stage-conditional grid was loaded by **K28** (`load_residual.load_rerun_b1` →
> `rerun_b1_run` / `rerun_b1_window` / `rerun_b1_curve_point`, 7 windows, 140 curve
> points). All four deltas §2.6 names reproduce exactly (burst1 6→7, burst3 7→8,
> burst4 7→8, burst6 6→8; GPU-hours 49.9→58.2, 3.1→3.6, 22.1→25.2, 8.2→10.9). Two things
> were genuinely outstanding and are now applied:
> 1. **burst5's stage-conditional row was computed against the pre-§2.1 C\* = 16.** The
>    artifact predates the supersession, so burst5 reported a 0-worker delta against a
>    baseline that no longer stands. Superseded visibly (sibling `_corrected` columns +
>    `grid_correction` row + `rerun_b1_window_effective`): against the corrected published
>    C\* = 8, the smallest C clearing 1,000 ms on image-bearing requests is **C = 8 at
>    852.4 ms** (C = 7 is 1037.5 ms) — matching §2.6's own figure. The delta really is 0,
>    but 0 against 8, not against 16.
> 2. **Only burst1 had a `grid_correction` row**; burst3/4/6 had none, so the ledger showed
>    one of four. Added as `alternative_metric` — *not* supersessions.
> `grid_window.c_star` is untouched. Per the standing instruction, the stage-conditional
> grid is kept **separate** from `grid_window.c_star` and every COMMENT on the new objects
> says so explicitly: it is a **different metric**, not a correction.
>
> **§2.10 was the only genuine ingest** — nothing under
> `simulation/results/live51/live_runs/` was in the store. New tables `live_arm`,
> `live_arm_metric`, `live_worker_event`, `live_spawn_latency`, `live_fpm_pass`; view
> `v_live_anchor`. Every §2.10 quantity reproduces to full precision: TTFT p99
> 695.16032053 / 3531.453221559999; ITL p99 11.469605181217391 / 150.74457055235087;
> replica-seconds 6062.954568 (span 1643.6 s) / 1798.852786 (span 1644.5 s); spawn→
> registered 0.954–0.996 s, mean 0.9858 s, n = 5; mixed-pass 2/184, 2/24, 3/207. The two
> derived definitions the audit stated only in prose are now pinned in code and comments:
> *mixed pass* = an FPM scheduler pass with `prefill_tok > 0 AND decode_kv > 0`, censused
> over the first 300 s of FPM logging; *spawn→registered* = a **non-initial** spawn paired
> to the first following `Discovery Added` (initial spawns fire before the planner is
> subscribed and measure ~3.3 s of planner startup, not registration). `runs.tp = 2`
> backfilled on all live rows from `engine_args.json`. The **ITL mapping** §2.10 flags is
> now enforced structurally, not just documented: `live_arm.itl_p99_ms` is aiperf
> `inter_token_latency` = **TPOT**, the true per-chunk ITL is carried separately as
> `chunk_latency_p99_ms`, the view column is named `tpot_p99_ms`, and C222/C223 fail if the
> two are ever wired to the same field — the exact confusion that produced R16.
> The third sibling arm `verify_flag` is ingested but flagged `is_thesis_arm = false`: a
> planner feature-flag control, not a tab:val-anchor row.

### 2.1 The burst5 `C*` supersession — MOSTLY ALREADY DONE; two derived columns remain

Affects: baselines.tex:81, 94, 115, 118, 120, 252; conclusion.tex:24, 25; apendice.tex:301;
aiconfigurator.tex:363.

**Status change from the first pass:** the adversarial reviews of *three* chapters (apendice, conclusion,
baselines) independently confirm the correction is **already ingested**:
```sql
SELECT window_name, c_star, c_star_corrected, is_superseded, tp_star FROM provenance.grid_window;
-- burst5: c_star=16, c_star_corrected=8, is_superseded=t
SELECT * FROM provenance.grid_window_effective ORDER BY 1;
-- c_star_effective = 6,8,7,7,8,6 (bursts), 2 (steady24h);
-- correction_source = /home/gio/tese/verification/rerun-stability-e2e.md on the burst5 row
```
Independent p99-only confirmation: `SELECT encoder_workers, delay_p99_ms, feasible FROM provenance.grid_vision_point WHERE window_name='burst5' ORDER BY 1;` → C=4 **1548.410 ms** (infeasible vs the 1,000 ms bound), C=8 **759.524 ms** (feasible). 8 is the smallest feasible grid point.

**DO NOT** overwrite `grid_window.c_star` or `grid_vision_point.feasible` (R40): those columns are the
intentional raw pre-correction record of the untouched `grid_summary.json` ingest.

**Outstanding actions (2 derived columns only):**
1. `grid_window.overprovision_vision_x` for `steady24h`: **8 → 4**. It is arithmetic off the superseded
   static C=16 (16/2), not a measurement. Corrected: deployable 8 / steady-optimal 2 = **4.0**.
   (`overprovision_llm_x = 2` is confirmed unchanged: TP2×2 = 4 GPUs on bursts vs TP1×2 = 2 on the calm day.)
2. Recompute the **burst-window** `vision_x` values in the same raw block (currently 2.67/2.0/2.29/2.29/1.0/2.67,
   all derived from C=16) against the corrected per-window set.
3. `grid_run_summary.static_encoder_workers`: **16 → 8** — max over the corrected per-window set {6,8,7,7,8,6},
   attained at burst2 and burst5. Cross-check: `rerun_b1_results.json → corrected_image_cstar` = {b1 7, b2 8,
   b3 8, b4 8, b5 8, b6 8, steady 2}, max 8. **Verify first** whether the `grid_window`-style
   `_corrected`/`is_superseded` treatment has already been applied here too; if so, apply the same pattern
   rather than overwriting.
4. `silicon_multiworker.json → silicon_cstar = 16` needs the same treatment — but see **Q8** first: it may be
   the same artifact rather than an independent confirmation.

### 2.2 twopool `srcbuild` runtime rows (5 claims) — ingest, do not edit the thesis

twopool.tex:61, 103, 104, 105, 106 quote the **source-built** in-core runtime, which the chapter says
explicitly at :58-66 and which the adversarial pass confirmed is the artifact backing every cell.
```sql
SELECT run_id, mean_ttft_ms, p99_ttft_ms, max_ttft_ms, mean_itl_ms, max_itl_ms,
       mean_e2e_latency_ms, p99_e2e_latency_ms, mean_output_token_throughput_per_user
  FROM provenance.llm_run_summary WHERE run_id IN ('sweeps:llm_head2k_poly_s1','sweeps:llm_head2k_aic_s1');
-- DB (wheel)   poly: 67.390 / 249.441 / 2539.914 ...   aic: 72.639 / 306.729 / 7598.103 ...
```
srcbuild (`simulation/results/srcbuild/llm_head2k_{poly,aic}_src.json`) reproduces **every** published cell:
poly 67.30122 / 248.46453 / 2539.91366 / 6.78509 / 180.69856 / 1412.95029 / 6878.76756 / 160.63317;
aic 68.23318 / 307.36448 / 4517.56828 / 7.67120 / 347.73152 / 1589.62103 / 8163.49788 / 141.95316.
Ratios 1.23699 → 1.24, 1.7786 → 1.8, 1.9244 → 1.9.

**Action:** ingest `simulation/results/srcbuild/*.json` as the current rows for the tab:sim-poly-aic metrics;
set `superseded_by` on `sweeps:llm_head2k_{poly,aic}_s1` **for those metrics**; add a runtime-build column so
wheel and srcbuild rows are distinguishable. This is the root cause of R4/R12 and of [E14].

### 2.3 Reprice harness (phase-E physical anchor) — 4 stats files, 5 closedloop claims

closedloop.tex:606, 621, 635, 638 all verified from archived files that are **not ingested**:
- `.../winsched_treatment_vllm.stats.json → encoder_delay_ms.p99` = **605.612** (thesis 606)
- `.../winsched_ctrl_aic.stats.json` → **589.301** (thesis 589); DB corroborates via
  `SELECT p99_ms FROM provenance.ewma_ablation_cell WHERE model='chronos' AND window_name='aggregate' AND readiness='warm' AND rho=15 AND lead_s=30;` → 589.301
- `.../static_c8_treatment_vllm.stats.json` → **692.008** (thesis 692); `.../static_c8_ctrl_aic.stats.json` → **646.943** (thesis 647)
- `provisioned_worker_seconds` = 2,410,754.7 in **both** winsched files; 3,869,278.8 in both static-C8 files
- Harness delta: 646.943 vs `SELECT encoder_delay_p99_ms FROM provenance.encoder_run_summary WHERE run_id='misc:week_static_C8';` = 644.44 → **0.388 % < 0.5 %**, as the thesis states.

Also ingest `collector_kernel_ledger`'s source and the same directory's `encoder_batch_images` (=64), which
[E18] depends on.

### 2.4 Riders knee / belief derivation (closedloop.tex:328, 331, 337)

`results-ledger.md:147-148` records belief = **10.07 rps/TP2-replica** (p10–p90 8.5–12.8), and
`x8 = belief/1.26 = binding-window knee + ~14 % capacity margin`. DB corroborates arithmetically:
```sql
SELECT run_id, p99_ttft_ms FROM provenance.llm_run_summary WHERE run_id LIKE 'riders:%';
-- tp2knee_s1.5 905.86 PASS | tp2knee_s2 1078.61 FAIL
-- fc_scale6.22_burst4_v2 1103.91 FAIL | fc_scale7.0_burst4_v2 792.01 PASS | fc_scale8.0_burst4_v2 753.79 PASS
```
10.07/6.22 = 1.619 → 1.62 req/s (burst1); 10.07/8.0 = 1.259 and 10.07/7.0 = 1.438 → the published [1.26, 1.44].
**Action:** ingest the `riders44` knee/belief derivation and the tp2knee offered-rate mapping. (This is what
makes R20 checkable rather than arguable.)

### 2.5 Riders ladder configuration (baselines.tex:168, 181)

```sql
SELECT run_id, window_name, lead_s, tp FROM provenance.runs WHERE run_id LIKE 'riders:ladder%';
-- lead_s NULL, window_name NULL on all four rows
```
Settled by `simulation/run_44_riders.sh:3` and `:32` (`STARTUP_TIME=60 AIC_TP=2`, trace
`results/grid/traces/grid_burst1_C6.jsonl`, num_requests 64,804 = `windows.burst1`).
Ladder values reproduce: gpu_hours 18.638/19.199/19.413/20.379 → thesis 18.6→20.4; p99_ttft
1615.49/1615.99/1616.60/1619.61 → thesis 1,616–1,620.
**Action:** re-ingest with `lead_s=60`, `window_name='burst1'`, `tp=2`, and record the generating command in
`provenance.grid_command` / `ledger_entry`.

### 2.6 Stage-conditional vision grid (baselines.tex:92, 93)

`provenance.grid_vision_point` is mixed-only; `factorial_cell.readiness` is an unrelated axis.
Decided by `verification/rerun_b1_results.json` (mixed → image C*, and 5090-hours):
burst1 6→7 (49.9→58.2), burst3 7→8 (3.1→3.6), burst4 7→8 (22.1→25.2), burst6 6→8 (8.2→10.9) — **exact match**
on all four counts and all four GPU-hour figures, including the non-obvious burst6 +2 step (at C=7
image-bearing p99 = 1049.1 ms, still over 1,000). Unchanged: burst2 8→8 (946.8 ms), steady 2→2 (733.6 ms),
burst5 0 delta (852.4 ms at the corrected C=8).
**Action:** ingest the stage-conditional vision grid from `verification/rerun_b1_results.json`.

### 2.7 Sweep manifests not loaded (closedloop.tex:83, 393, 515; intro.tex:476)

- **560-cell target-time grid — now confirmed on disk.** `wc -l simulation/results/cells_44.jsonl` = **560** and
  `results_44.jsonl` = **560**, exactly; a sample cell matches the closedloop.tex:81-83 description.
  `SELECT actuation, count(*) FROM provenance.factorial_cell GROUP BY 1;` returns issue-time only (1,172 cells)
  — the expected state, since the target-time grid is declared superseded by the 60-cell issue-time rebuild.
  **Action:** ingest both files with `actuation='target-time'`, `is_current=false`, so the superseded grid is
  **auditable rather than invisible**.
- 96-cell issue-time week surface (3 models × 2 quantiles × 4 ratings × 4 leads) — `results-ledger.md:423`
  ("p90 48/48 pass, p50 0/48"). Only 19 combinations are in `provenance.runs`.
- The p50 half (48 cells) — ledger:295. Direction corroborated: every ingested week-scale p50 encoder run has
  p99 2,735–4,688 ms.

### 2.8 EWMA calibration coverage (closedloop.tex:218)

`results-ledger.md:581`: calibrated on the 1.4-day context (n=6144) by three schemes; eval coverage
add 0.901 / mult 0.878 / wsc 0.877 / native 0.929 → published band **0.88–0.90** at its own precision.
The three schemes exist as `ewma-add`/`ewma-mult`/`ewma-wsc` in `provenance.ewma_ablation_cell`; the coverage
artifact does not. **Action:** ingest it.

> **§2.8 RESOLVED 2026-07-20 — NO INGEST WAS NEEDED; the ledger entry above was stale.**
> `provenance.ewma_cal_coverage` **already** carries all four schemes × both splits (8 rows), matching
> `ewma_cal_manifest.json` to full stored precision — eval add **0.9012529**, mult **0.8783340**,
> wsc **0.8765972**, native **0.9288860**; calib 0.8984375 / 0.8984375 / 0.9000651 / 0.9407552;
> `nominal` 0.9, `n_calib` 6144. The table and all five columns were already `COMMENT`ed. So
> closedloop.tex:218's **0.88–0.90** band is DB-verifiable as it stands: it is the add/mult/wsc *eval*
> spread at published precision. No thesis edit, no ingest.
>
> What was genuinely missing is the fact that makes coverage *load-bearing*, now recorded as check
> **C010** (`schema/23_forecast_covariate.sql`): the three arms are **point-identical**. Measured over
> the 38,388 aligned `(origin,h,variate)` rows of `ewma_cal_{add,mult,wsc}_images.parquet`:
> **0** rows differ in `point`; **38,388** differ in `p90`, on both add-vs-mult and add-vs-wsc.
> This is by construction — conformal calibration rescales the interval and never moves the point
> forecast — so **no point-error metric (WAPE/MAE/RMSE) can rank these arms at all**, and
> `ewma_cal_coverage` is the *only* evidence in the store that separates them. That is the sentence
> §2.8 should always have carried.

### 2.9 NEW — `provenance.forecast` is a partial ingest (5.3 M rows short)

```sql
SELECT count(*) FROM provenance.forecast;                        -- 16,657,524
SELECT coalesce(mode,'cov'), resolution, model, count(*) FROM provenance.forecast GROUP BY 1,2,3;
-- covariate-mode POINT rows exist ONLY at 15 s (chronos/timesfm/toto 161,232 each + ewma 38,388 = 522,084)
```
…whereas `provenance.forecast_metrics` carries cov-mode metrics at **all five** resolutions. On-disk pyarrow
counts over `predictors/results/*.parquet` = 16,734,300, plus the reassembled covariate parquets
(chronos 2,593,680 + toto 2,675,520 = 5,269,200) = **22,003,500** total; 21,888,336 excluding `ewma_cal_*`;
**21,565,872** excluding `*_expctx` as well.
**Action:** ingest the missing cov-mode point partitions at 1 s/30 s/45 s/1 min, then re-adjudicate
intro.tex:431's "21.4 million" (Q1). Until then the DB count must **never** be substituted (R29).

> **§2.9 APPLIED 2026-07-20 — `schema/23_forecast_covariate.sql`. Q1 ANSWERED; intro.tex:431 needs no edit.**
>
> **The gap was larger than stated.** `select count(*) from provenance.forecast where mode='cov'`
> returned **0** — the entire covariate mode was absent at *every* resolution, not just at
> 1 s/30 s/45 s/1 min. The rows the entry above mistook for cov-mode 15 s data are the **NULL-mode**
> rows, which are two unrelated post-manuscript families: the 12 `*_expctx` expanding-context
> reforecasts (40,308 each = 483,696) and the 3 `ewma_cal_*` variants (38,388 each = 115,164).
>
> **Root cause — not a loader bug.** `{chronos,toto}_covariates.parquet` are the only forecast
> artifacts stored split+gzipped (`.parquet.gz.part00/01`, commit 925b399 "keep the repo LFS-free"),
> and `load_forecast` globs `*.parquet`, which cannot match `*.parquet.gz.part00`. The archive was
> complete; only the reassembly step was missing. The reassembled paths are gitignored
> (`.gitignore:85-86`) — reassembly on demand *is* the intended workflow (cf. `_ensure_covariates()`,
> `figuras_new/predictors.py:78-85`). **No loader change was required and none was made.**
>
> | | rows |
> | --- | ---: |
> | before | 16,734,300 |
> | added (`main.py --only K10`, 55 s, 2 files) | **5,269,200** |
> | after | **22,003,500** |
>
> Idempotency verified: the second `--only K10` run loaded **0 rows / 0 files**.
>
> **Per (model, mode, resolution)** — all mode `cov`, matching the archived parquets exactly:
> chronos 1s 2,386,896 · 15s 128,976 · 30s 48,336 · 45s 21,456 · 1min 8,016 (= 2,593,680);
> toto 1s 2,403,264 · 15s 145,344 · 30s 64,704 · 45s 37,824 · 1min 24,384 (= 2,675,520).
>
> **File-by-file reconciliation: exact.** 41 forecast parquets on disk, 41 `source_tag` groups in the
> DB, **zero** count mismatches, both sides totalling **22,003,500** — the ledger's own on-disk figure.
> No file is absent. `source_tag` is now non-NULL on every row, so it is a total key.
>
> **Q1 ANSWERED — intro.tex:431's "21.4 million archived rows" is EXACT, not approximate:**
>
> | inclusion rule | rows |
> | --- | ---: |
> | all files | 22,003,500 |
> | excl `ewma_cal_*` | 21,888,336 |
> | excl `ewma_cal_*` and `*_expctx` | **21,404,640** |
> | `mode IN ('uni','cov')` (thesis-run corpus) | **21,404,640** |
>
> The two natural exclusion rules **coincide** and land on 21,404,640 = "21.4 million" exactly, with no
> rounding slack. **R29 is now fully discharged: no weakening to "over 21 million" is needed.** Note this
> *refutes* §2.9's own 21,565,872 figure for that exclusion rule. Canonical accessor added:
> `provenance.v_forecast_thesis_corpus` — use it for archived-row claims; `count(*)` over the base
> table (22,003,500) over-counts by including post-manuscript artifacts.
>
> **This was not cosmetic — it un-vacuumed a check.** C006 recomputes `forecast_metrics`
> WAPE/MAE/RMSE from raw rows and joins on `rc.md = coalesce(m.mode,'~')`, i.e. it is mode-aware.
> With cov rows absent, all **360** cov-mode metric cells (span=`full`, h ∈ {1,4,12}) failed to join and
> were **silently dropped**: C006 verified 1,080 cells while reporting as a full check. It now verifies
> all **1,440**, and all 1,440 pass — a check made honest with **no** change to its tolerance or
> population predicate. (The 1,080 figure is deductive, not an observed pre-ingest reading: C006's join
> demands mode equality, and `cov` had zero rows, so exactly the 1,080 `uni` cells could join. The
> 360/1,080 split is measured.) New guard **C009** pins the 10 cov partitions to the archived counts.
>
> **Regression status.** `check_all()` = 56 enabled checks; 8 fail, **all pre-existing**: errors C002
> (median TTFT, 1 of 178 runs) and C603 (a16/a16_ft/g2/g4 partitions); warns C107, C207, C302, C306,
> C404, C601. This pass wrote only to `provenance.forecast` (+ `check_definition`, one view, three
> comments); none of the 8 reads `provenance.forecast`, so none is attributable here. Flagged, not
> adopted — note C002 and C603 have gone red since the 2026-07-19 ledger entry recorded no
> error-severity failures.

### 2.10 NEW — live-arm artifacts are all recoverable and none are ingested

Every "live" half of `tab:val-anchor` was verified this pass from disk. Ingest as a `live` arm so the table
becomes fully DB-checkable:
| Quantity | Source | Value |
| --- | --- | ---: |
| live_fc TTFT p99 | `live_runs/live_fc/profile_export_aiperf.json` | 695.16032053 ms |
| live_re TTFT p99 | `live_runs/live_re/profile_export_aiperf.json` | 3531.453221559999 ms |
| live_fc ITL p99 (aiperf) | same | 11.469605181217391 ms |
| live_re ITL p99 (aiperf) | same | 150.74457055235087 ms |
| live_fc replica-seconds | integrate `n_live` over `t_wall`, `live_fc/manager.jsonl` | 6062.954568 (span 1643.6 s) |
| live_re replica-seconds | same, `live_re/manager.jsonl` | 1798.852786 (span 1644.5 s) |
| spawn→registered latency | `planner.log.gz` `Discovery Added` paired to `manager.jsonl` spawns | 0.954–0.996 s, mean 0.9858 s (n=5) |
| mixed-pass rates | `planner.log.gz` `base._log_fpm`, first 300 s | live_fc 2/184, live_re 2/24, verify_flag 3/207 |

**Also document, in the ingest notes:** `tab:val-anchor`'s "ITL p99" maps to **`p99_tpot_ms`**, not
`p99_itl_ms`. This single mapping error manufactured a phantom 8 ms discrepancy and drove R16.
Backfill `runs.tp = 2` on the 7 `experiment='live'` rows from `simulation/live51/engine_args.json`
(`"aic_tp_size": 2`).

### 2.11 NEW — three archived artifacts that answer "unverifiable" claims

| Claim | Artifact to ingest | Value |
| --- | --- | --- |
| intro.tex:311 — AIC SOL bound ≈5.9× optimistic | `collector_artifacts/phaseB_fallback_trace/result.txt` | SOL 0.00605 ms vs measured 0.03580 ms → **5.917×**. Ingest into `provenance.collector_scalar`. |
| intro.tex:514, 516 — fabric conditional | `simulation/results/aggregate44/fc_p90_L30_ds4.jsonl.stats.json` | `handoff_gbps` 6.25, `handoff_ms.p99` **1087.406**, `encoder_delay_ms.p99` **1403.774**. Needs a bandwidth/payload dimension (or arm label `ds4_25gbps`) on `provenance.composed_e2e`. |
| twopool.tex:118 — factoring invariance | `progress/phase2-simulation.md:106-109` ("delta 0.000000 ms") | Ingest with an explicit `(batch, images_per_request)` key. |

### 2.12 NEW — missing configuration columns (blocks future audits)

| Column | Current state | Action |
| --- | --- | --- |
| runtime version | `runs.engine` NULL on 2,204 of 2,206 rows; `commit_sha` NULL on **all**; no dynamo/aic version field anywhere in the schema | Add a runtime-version + commit column. This is the *only* reason related.tex:168, tese.tex:256 and apendice_ecosystem.tex:125 are unadjudicable. |
| `runs.tp` for `pool='encoder'` | NULL on all 1,278 rows | Backfill TP=1 — see §5.1 |
| AIC f(N) at 320²/640²/896² | vLLM present, **AIC absent** (`aic` exists only at 224/336/448/672) | Persist alongside `vllm_multires.json` — apendice.tex:215 is unverifiable purely for want of this |
| spectral fit band | peak metrics tagged `window_bin='10min'`; band endpoints only in code | Persist f_lo = 1/43200 Hz, f_hi = 1/600 Hz from `f_fourier.py:73`, plus the full periodogram peak list (the stored top-8 truncation caused two false INSUFFICIENT_DATA verdicts) |
| g3_32b reports | `defense/anim/data/g3_32b/reports/*.report.json` not ingested (26 × 235B-TP8, 95 × 32B, the 8B TP1 s1) | Ingest, clearly tagged **post-manuscript defence material** so no future pass mistakes them for thesis runs (R26) |

---

## 3. DENOMINATOR / DEFINITION CLARIFICATIONS

Numbers right; wording ambiguous. Nothing here is an error correction.

### 3.1 The headline 0.62× — the ONE denominator actually computed

**The computed quantity, and nothing else:**
```sql
SELECT ratio_vs_static, ws, denom_static_c8_ws, p99_ms, feasible
  FROM provenance.ewma_ablation_cell
 WHERE model='chronos' AND window_name='aggregate' AND quantile='p90'
   AND rho=15 AND readiness='warm' AND lead_s=30;
-- 0.6231 | 2,410,754.7 ws | 3,869,278.4 ws | 589.301 ms | t
```
> **0.62× = (provisioned encoder-worker-seconds of the Chronos p90 forecast policy, ρ=15, L=30 s, warm
> readiness, over the 5.60-day covered span) ÷ (provisioned encoder-worker-seconds of the *deployable
> static* fleet, C = 8, over the same span).**
>
> "Deployable static" = the single static configuration feasible on **every** window (baselines.tex:118-119),
> i.e. max over the corrected per-window C* set {6,8,7,7,8,6} = 8. One RTX 5090-class GPU per encoder worker
> (baselines.tex:17-19), so worker-seconds ≡ GPU-seconds here — confirmed exactly by
> `grid_window_effective.gpu_hours_rtx5090_effective = span_h × c_star` (burst1 8.316 × 6 = 49.896 → 49.9;
> steady24h 23.999 × 2 = 48.0).

Derivation at closedloop.tex:465-469: 2.41 M / 3.87 M = 0.6227 → 0.62.
Lead-invariance across the realizable archive range: L=15 0.6231, L=45 0.6229, L=165 0.6220 (warm);
strict readiness 0.6202 / 0.6171 / 0.6140 / 0.5877 → the published **0.59–0.62** band.
**19 sites, all numerically consistent:** tese.tex:67 (EN), tese.tex:112 (PT "0,62"), intro.tex:50, 271, 481,
514; baselines.tex:98; closedloop.tex:242, 265, 465-469, 481, 500, 530, 630, 666; conclusion.tex:81, 95;
related.tex:361; apendice.tex:11, 333.

**Every phrasing in circulation, and whether it is accurate for that denominator:**

| # | Phrasing | Sites | Accurate? |
| --- | --- | --- | --- |
| A | "provisioned worker-time" | closedloop.tex:465-469 (source) | **Yes — canonical** |
| B | "worker-time" (no "provisioned") | closedloop.tex:242, 481, 500 | **Yes.** ≡ A; drops a disambiguation, not the referent |
| C | "GPU-time" | intro.tex:481; conclusion.tex:81 | **Yes.** ≡ A/B by baselines.tex:17-19 and by the `grid_window_effective` identity above. Not a unit mismatch (R33) |
| D | PT "tempo de GPU da menor frota estática viável" | tese.tex:112 | **Yes — arguably the clearest of the five**, since it names the feasibility qualifier inline |
| E | bare "static" | apendice.tex:11, 333; related.tex:361 | **Yes**, pinned by the table row "Static C=8 (deployable) … 3.87 Mworker-s … 1.00×" |
| F | "best static encoder fleet's GPU-time" | conclusion.tex:95 | **Yes — overturned to CONFIRMED.** The cheapest static fleet (C=2, 1,209,599 ws) **fails** at enc p99 2,904.6 ms, so "best" cannot denote it in a passing-fleet comparison. Reads naturally as best *deployable* = C=8 = the denominator used |
| G | "roughly two-thirds" | conclusion.tex:95 | **Loose but not wrong.** 0.667 sits 7.0 % relatively above the measured 0.6231, and collides numerically with the reactive controller's published **0.67×** row in the same table |

- **[C1] OPTIONAL (not an error fix)** — conclusion.tex:95: to remove the 0.67× collision, replace
  `at roughly two-thirds of the best static encoder fleet's GPU-time (RQ4)` with
  `at 0.62$\times$ the deployable static encoder fleet's provisioned worker-time (RQ4)`.
  **Do not adopt any rewrite premised on the denominator being wrong or ambiguous** (R33) — it is neither.
- **[C2]** related.tex:361 and tese.tex:67 quote 0.62× with **no span or readiness-model qualifier**; every
  other prose site carries one. Add "over the 5.60-day covered span, warm-readiness billing".
- **[C3]** The worker-time ≡ GPU-time equivalence is established **once**, at baselines.tex:17-19, and never
  restated where a reader meeting tese.tex:67 first would find it. Restate on first use.
- **[C4]** The 0.59–0.62× sensitivity band is carried consistently with its qualifier at all six sites
  (intro.tex:274; closedloop.tex:124, 446, 498, 669; conclusion.tex:84). **No action.**

### 3.2 The two unrelated "within 8 %" claims

- twopool.tex:216-217 — **modelled vs replayed prefill TTFT p99**, 705.94 vs 651.1395 → 8.416 % against the
  replayed reference, 7.763 % against the modelled. Fix [E11] (→ 8.5 %, true under both).
- validation.tex:84 / intro.tex:539 — **provisioned replica-time**, live vs offline twin: forecast
  (6062.954568 − 6399.81123)/6399.81123 = **−5.264 %**; reactive (1798.852786 − 1948.19053)/1948.19053 =
  **−7.665 %**. Both strictly under 8 %. See [E24] for the −7.6/−7.7 printing.
- **[C5]** These are different claims about different quantities. Say which is which at each site.

### 3.3 The 588 vs 589 ms "service floor"

Derivation at closedloop.tex:452-457: f(64) = 316.4 + handoff 272 = **588.4 ms**.
- **588** at ~28 sites (intro.tex:265, 479, 514; conclusion.tex:68, 101; twopool.tex:215; baselines.tex:221-227;
  closedloop.tex:80, 92, 113, 121, 142, 202, 452, 468, 469, 472, 483, 499, 523, 531, 543, 593, 627).
- **589** at closedloop.tex:241, 254, 265, 606, 622; apendice.tex:211.
- **[C6]** **Both are defensible** — 588.37 is the analytic floor, 589.301 is the measured AIC control replay
  (`ewma_ablation_cell`, §3.1). Label them distinctly ("analytic floor 588.4 ms" / "measured AIC control
  589.3 ms") rather than harmonising to one number.
- **[C7]** closedloop.tex:622 vs :627 quote the AIC baseline as 589 and 588 **five lines apart** for the same
  schedule replay. The vLLM reprice (:622) uses the measured control; the HF-eager comparison (:627) uses the
  analytic floor. Say so, as the chapter already does for the analogous 647-vs-644 gap at :636-638.

### 3.4 The 1.4–1.6× engine ratio band

Measured 1.36–1.62 (`collector_encoder_fn`, `anchor_dense_sdpa_2400`: 1.3613 at N=8, **1.6170** at N=64).
Four summary sites say "≈1.4–1.6×" (intro.tex:249, 510; apendice.tex:194; conclusion.tex:106).
- **[C8]** Adversarially **upheld as correct** (R35): 1.36 → 1.4 and 1.62 → 1.6 at one-decimal precision, and
  aiconfigurator.tex:517 carries an explicit `\approx`. **No edit required.** Optional cosmetic tightening to
  "1.36–1.62×" — do **not** apply it as an error fix.
- **[C9]** The *precise* statements' disagreement with each other **is** real and is fixed by [E17]:
  apendice.tex:179 says 1.61, aiconfigurator.tex:274 says 1.62. After [E17] they agree.
- **[C10]** closedloop.tex:616's separate "1.4–1.6×" is **CONFIRMED and untouched**: it names HF-transformers
  **eager** (`engine='eager'`), and eager÷vllm at 448², N≤64 spans **1.366 (N=2) – 1.591 (N=24)**, median ~1.44,
  1.538 at N=64. The 1.617 flagged earlier is `f64_over_aic`, a different column.

### 3.5 R² = 0.123 vs 0.12

0.123 at intro.tex:146; trace-eda.tex:241, 482; related.tex:188, 335. 0.12 at tese.tex:51, 92; intro.tex:406;
trace-eda.tex:257; predictors.tex:232; related.tex:225; conclusion.tex:17.
- **[C11]** No site is wrong (0.12 is the correct 2-digit rounding of 0.12253911262014872), but the two
  roundings are mixed **inside the same chapter** three times (trace-eda :241/:482 vs :257; related :188/:335
  vs :225; intro :146 vs :406). The paired decode figure 0.654 is never rounded. Pick one precision per
  chapter. **Must never appear in an errata as a wrong value** (R32).
- **[C12]** After [E22], 0.35² = 0.1225 is consistent with 0.123 to three digits; note this in the trace-eda
  caption if the two are read together.

### 3.6 Remaining wording-only items

- **[C13] baselines.tex:109** (upheld) — `TP2$\times$2 passes every one (763--846\,ms)` is the range over the
  **five tabulated** windows. `SELECT window_name, ttft_p99_ms FROM provenance.grid_llm_point WHERE tp=2 AND llm_workers=2;`
  → burst1 763.390, burst2 766.259, burst3 845.692, burst4 792.300, burst5 781.080, **burst6 733.777**.
  burst6 sits below the floor. Preferred: `(763--846\,ms on the tabulated windows)`. The omission is
  **conservative** (makes TP2×2 look worse), so low criticality.
- **[C14] trace-eda.tex:411-413** (overturned to CONFIRMED; rhetorical weakening recommended) — every number
  is exact (`eda_metric`, `q_multires_tails`: NumImages.p50 = 1 vs global 0.5; ContextTokens.p50 = 1210 vs
  1124; GeneratedTokens.p50 = 105 vs 98; multimodal_share 0.7770 vs global 0.500), but 1210/1124 = **+7.65 %**
  and 105/98 = **+7.14 %** stretch "within a few percent", and "ordinary-composition" is undercut by the
  multimodal share. Suggested: `carry near-ordinary per-request work: median 1 image, and median context and
  generation about 8\% above the global medians (\num{1210} vs.\ \num{1124} tokens; \num{105} vs.\ \num{98}
  tokens). They are somewhat more multimodal than the trace as a whole (77.7\% image-bearing against 50.0\%),
  but high request rate still does not imply heavy per-request work.` Minimal safe edit: change only
  "within a few percent" → "about 8 % above". **Scope check passed:** `q_multires_tails.py:106-131` computes
  both p50 and p50_global over **all** requests — there is no denominator mismatch (R39).
- **[C15] baselines.tex:143** (upheld) — `tab:base-tp`'s caption says "at its static-optimal encoder count",
  but the only archived burst5 TP rows are at C=16 and C=32 while `tab:base-grid` now publishes burst5 C*=8.
  The cells are exact (1315.599→1316, 781.080→781, ratio 1.6844→1.68). **Soften to "at its archived
  static-optimal encoder count"**, or re-run at C=8 (**Q4**). Sensitivity is small (burst5 C16→C32 moves
  TP2×2 by 0.17 ms; burst1 C6→C8 moves it 763.390→770.301, 0.9 %). **Do not "fix" the 1316/781 cells.**
- **[C16] baselines.tex:123** (upheld) — `SELECT family, count(*), count(*) FILTER (WHERE feasible) FROM provenance.grid_closeout_variant GROUP BY family;`
  → router 28/28, binding 7/7. The 7 binding rows carry `variant_knob IS NULL` — they are not router-knob
  perturbations. Replace with `(35 corner re-runs --- 28 router-knob variants plus 7 binding-fleet checks;
  no frontier movement)`. Count 35 and the no-movement claim are exact; only the attribution over-counts by 7.
- **[C17] baselines.tex:115** — the numeric part is a DB issue (§2.1); the wording point stands independently:
  **8/2 = 4× is not an "order-of-magnitude" missizing.** Reword. It cross-references `cap:trace-eda`, whose own
  claim should be checked *there*.
- **[C18] baselines.tex:159** (overturned to correct) — 500/50 confirmed at `simulation/run_32_reactive.sh:24`;
  measured margins: TTFT 126.40–322.18 ms (**1.55–3.96×**), ITL 6.909–9.291 ms (**5.38–7.24×**) over 14 rows.
  The published "2–4×" is the one-significant-figure rendering of the TTFT band. **Not wrong** (R21). Optional
  clarity: `with 1.6--4$\times$ margin on window-mean TTFT and 5--7$\times$ on ITL`.
- **[C19] baselines.tex:49** (upheld, downgraded) — `experiment='reactive'` has `lead_s` exactly {15, 30, 45,
  300}; the extra leads (60/120/165) belong to `experiment='factorial'`, which this chapter never mentions.
  **No edit required**; optional `(the leads tabulated here; the archived factorial also covers 60/120/165\,s)`.
- **[C20] trace-eda.tex:38 and :47** (overturned to CONFIRMED) — 277 and 66.427 both reproduce **exactly**
  under one consistent definition: (median ctx at k − text-only median 792)/k, from
  `context_tokens_by_numimages.{0,1,529}.median` = 792 / 1069 / 35932. **No edit required.** Optional
  non-numeric clarity: `(${\approx}277$ tokens per image above the \num{792}-token text-only median at one
  image, falling to ${\approx}66$ at 529)`. **Do not attach the ratio definition** (R38).
- **[C21] twopool.tex:311** (overturned to CONFIRMED) — the subjunctive "would overprovision … by that factor"
  explicitly forwards the measured separation: language knee s=2 (ITL p99 67.334 PASS / 109.513 FAIL) against a
  vision pool uncrossed through s=32 (encoder delay p99 787.18 < 1,000) → 32/2 = 16, and the thesis states the
  weaker, correct ">10". **No edit.**
- **[C22] twopool.tex:436** (overturned to CONFIRMED) — the sentence states its own derivation ("scales roughly
  with patch count") and reports exact patch-count ratios (448/224)² = 4.00 and (672/448)² = 2.25. Measured AIC
  anchors at N=64: 74.885 / 317.299 / 787.718 → 4.237 and 2.483, i.e. 6 % and 10 % off in the same direction,
  which "roughly" encodes. **No edit** (R25). Optional: append `(measured $4.2\times$ and $2.5\times$ at $N{=}64$)`.
- **[C23] apendice.tex:124** (overturned to CONFIRMED) — the lock command **is** archived
  (`ENCODER_ANCHOR_SUMMARY.md:92`) and matches the stated target 2400/14001 literally. **Do not weaken**
  (R28). Optional provenance improvement: :130-131's "no lock-command log were captured" is now too weak and
  could cite that file. The genuine defect is at :28 ([E16]).
- **[C24] predictors.tex:191** (overturned to CONFIRMED) — ARIMA 0.52132 → 0.521, best FM 0.51530 → 0.515,
  EWMA 0.52170 ("ties the classical baselines"), constant 0.61800 = naive 0.61800. Gap 0.00602 = 0.602 points.
  "About a WAPE point" is a one-significant-figure statement. **Optional** precision polish only, never an
  errata entry (R24).
- **[C25] predictors.tex:335 / trace-eda.tex:290** (overturned to CONFIRMED) — 18 episodes, exact median
  **6.5 min**, p10 = 2, min = 1; the published 6 is the floor and the **conservative** direction for a scaling
  budget. **No edit** in either file (R17).
- **[C26] closedloop.tex:411** (overturned to CONFIRMED) — "provisioning cadence" is defined as 1-minute bins
  at predictors.tex:162 and :383, and the generator pins it. At 1 min the blue+yellow spread is
  0.53992 − 0.51533 = **0.0246 → 0.02**. **No edit.** Optional: write "(1-minute bins)" in the caption.
- **[C27] closedloop.tex:112** (overturned to CONFIRMED) — the sentence at :112-116 already carries both scope
  qualifications: burst1/3/4/5 each a **single** value 588.37 under both warm and strict readiness;
  steady24h warm 548.363–685.323, strict 564.047–733.643. **No edit.**
- **[C28] validation.tex:140** (overturned to CONFIRMED) — 24 and 8 are literally exact for the **offline
  episode replays** the clause names (`episode_twins/burst4_fc.log`: "clamped 24 replicas (= 24 GPUs) → 8
  replicas (= 8 GPUs)"; offline `max_gpu_budget` is in replica units). The anchor is separately and correctly
  capped at 4 (`twin_fc_p90_cap4`, 13 clamp events, 6,399.81 replica-s → the table's 6,400). **No edit**
  (R31). Optional clarity: insert "offline" before "episode replays".
- **[C29] conclusion.tex:41 and :60** (noted by the reviewer, out of its scope) — :41's unqualified 12.8 %
  wants the `across the $N\le64$ serving regime` scope that :104 and :121 already carry; :60's "every cold-start
  lead from 15 to 165 seconds" describes a **four-point discrete ladder** {15, 30, 45, 165} s as a continuum.

---

## 4. LIMITATIONS THAT THE NEW DATA GENUINELY RETIRES

Source of new measurements: `defense/anim/NEW-MEASUREMENTS.md` and the run directories it names.
Enabling change: `ai-dynamo/dynamo` commit `70c965db26` (`PlannerReplayBridge.report_jsonl_path`).

**Strictness rule applied:** an item is "retired" only if the new measurement covers the *same* claim at the
*same* or greater scope. Partial closures get **weakened** wording, never deletion.
**One fully retired; four partially closed.**

### 4.1 RETIRED IN FULL — "modelled reconstruction rather than a request-linked replay measurement"

- **Current text (twopool.tex:216-221):** the composed ingress→first-token p99 (~1.30 s) is
  `a modelled reconstruction rather than a request-linked replay measurement`, built from each request's
  replay-recorded encoder delay **plus its AIC-modelled prefill** (706 ms modelled vs 651 ms replayed).
- **New evidence (A12, `defense/anim/data/a12_runs`, 20 cells):** each request's **own** encoder delay
  (recovered from the seam) joined to its **own** replayed TTFT — a request-linked join with arrival alignment
  asserted < 1 ms. burst3 forecast composed E2E p99 = **1,239.5 ms** (enc 588.4 + TTFT 651.1), i.e. the
  modelled ≈1.24–1.30 s band is now **measured**, landing on the lower (1.24 s) estimate the chapter already
  published as the alternative at :222.
- **Action:** replace the "modelled reconstruction" caveat with the measured figure and cite A12. Keep the
  modelled-vs-replayed 706/651 sensitivity as a *method note* (and apply [E11]), because it licenses the older
  per-window numbers that were **not** re-run under A12.
- **New finding not in the thesis, worth adding:** reactive composed E2E = **21,868 ms** (encoder 16,079 ms
  compounds into language 10,574 ms) — per-pool grading **understates** the composed failure. Strengthens
  RQ1/RQ4.

### 4.2 PARTIALLY CLOSED — "the warm-up hole is the price of zero-shot honesty" (1.4 days ungraded)

- **Current text (closedloop.tex:47-53, :67; trace-eda.tex:176; baselines.tex:37):** the first **1.4 days** are
  consumed as forecast context and never graded; 5.60 days form the evaluation span.
- **New evidence:** expanding-context archives (`predictors/benchmark_expctx.py`, 12 parquets) grow the context
  as history accrues → first forecast at **12:03:00 (3 minutes in)** for all three models; per-model coverage
  75.0/87.3/93.2 % → **99.96 %**. A15 (3 runs) grades each model E2E over span_expctx = **999,599 requests
  (99.96 % of 1 M)**, both pools, per-request records, at **enc p99 588.4 / TTFT p99 651.1 ms** for all three —
  identical to the fixed-context A14 runs.
- **What this does and does not retire:** it retires the claim that zero-shot honesty *costs* 1.4 days of
  coverage — under expanding context the cost is ≈3 minutes at **zero change to the SLA outcome**. It does
  **not** retire the thesis's headline numbers, which remain fixed-context.
- **Proposed weakened wording, not deletion:** keep the 1.4-day split as the definition of the **graded span
  for the results reported here**, and add: "an expanding-context variant reduces the ungraded prefix to
  ≈3 minutes (99.96 % coverage) with identical p99 outcomes (588.4 / 651.1 ms), so the warm-up hole is a
  property of the fixed-context protocol rather than of zero-shot forecasting."
- **Do not** restate 0.62× or any cost figure against the 99.96 % span (§3.1, **Q6**).

### 4.3 PARTIALLY CLOSED — the coverage question (5.60 days vs 1,000,000 requests vs 99.96 %)

Three distinct spans are now in play. They must not be conflated.

| Span | Requests | What is graded on it | Source |
| --- | ---: | --- | --- |
| 5.60-day covered span | **749,601** | every closed-loop verdict in cap:closedloop, incl. **0.62×** | closedloop.tex:47-53, :437 |
| Full trace | **1,000,000** | trace extent, EDA, static/reactive per-request pass (**A13**) | trace-eda; `a13_runs` |
| span_expctx | **999,599 (99.96 %)** | per-model E2E under expanding context (**A15**) | `a15_runs` |
| per-model max span (**A14**) | Chronos 749,601 (75 %) / Toto 872,980 (87 %) / TimesFM 931,628 (93 %) | per-model E2E, fixed context | `a14_runs` |

- **The cross-chapter pass verified `tex/` is currently clean here:** no site claims closed-loop results over
  all 1 M requests or the full 7 days; the "full 1,000,000-request" language exists only in git history and
  `defense/`. **Do not import it into `tex/`.**
- **A13** (`coverage_manifest.json`: `encoder_all_1M_covered=true`, `language_all_1M_covered=true`,
  `per_model_maxspan_covered=true`, `complete=true`) genuinely retires "no per-request whole-trace pass" — but
  only for the **static C8 / static C2 / reactive** encoder arms and the **static TP2×2 / reactive planner**
  language arms. It does **not** extend the forecast policy's cost ratio to 1 M requests (the forecast policy
  is undefined on the context prefix under fixed context).
- **Proposed weakened wording:** "every request of the trace is simulated through both pools for the
  forecast-free policies (A13); forecast policies are graded on the 5.60-day covered span, and to 99.96 % of
  the trace under an expanding-context variant (A15)." **Not** "graded over all 1,000,000 requests."
- **[C30] Residual clarity item (cross-chapter 1f):** "covered week" / "week-scale" is used for 5.60 days at
  intro.tex:50 and closedloop.tex:665 without the disambiguation closedloop.tex:437 provides. Add it.

### 4.4 PARTIALLY CLOSED — "model choice is second-order" (asserted from accuracy, not shown E2E)

- **New evidence (A14, 3 runs):** Chronos 651.1 ms / 749,601 req / 528 GPU-h; Toto 651.1 ms / 872,980 req /
  751 GPU-h; TimesFM 651.1 ms / 931,628 req. A11 week TimesFM 651.1 ms (556.88 GPU-h) matches its ledger anchor
  exactly. A12 composed E2E p99 = 1,239.5 ms for all three on burst3/5/4 and week (burst1: chronos 1239.5,
  TimesFM 1258.4, Toto 1259.2).
- **Retires:** "model-independence inferred from the accuracy benchmark" → it is now an **E2E measurement** on
  the SLA outcome.
- **Does NOT retire the cost side:** GPU-hours differ substantially (528 / 751 / 776.85 across A14/A15 arms)
  over **different spans**. Independently corroborated by the tese review: against the 537.40 GPU-h language
  denominator, Toto is **1.164×** and TimesFM **1.193×** where Chronos is 0.965× — the language-pool
  near-break-even is Chronos-specific (already disclosed at closedloop.tex:382).
- **Weakened wording:** "model choice is second-order for the SLA verdict (identical 651.1 ms p99 across all
  three, end to end); cost comparisons across models are confounded by differing forecastable spans and are not
  claimed."

### 4.5 PARTIALLY CLOSED — "reactive failure shown on the top-6 episodes only" / "remaining windows priced by the grid"

- **Current text (closedloop.tex:571-575):** `the remaining windows are priced by the grid and the knee formula
  rather than replayed end-to-end`.
- **New evidence:** A2 extra episodes (`a2x_runs`, 100 tags = e7…e18 × policy × lead) — reactive fails **9 of
  18** episodes at L=30 s; burst2/6 reactive independently reproduce thesis Tab 7.3 through the full pipeline.
  A11 (`a11_runs`, 52 cells) replays 4 burst windows + full week × {Chronos, Toto, TimesFM, reactive} × lead
  {60, 120, 300} s with planner in loop and per-request records; every L60 anchor reproduces its ledgered twin;
  reactive failure is **lead-invariant** on the language pool (burst5: 2,151/2,151/2,155 ms).
- **Retires:** the "priced by the grid rather than replayed" caveat for the **four burst windows plus the week**.
- **Does NOT retire it in general**, and one new result *sharpens* an honest limitation: **e13** (263 img/s,
  7-minute onset, isolated after the calm stretch) is a genuine **p90 forecast-miss boundary case** where
  *both* policies fail and only static C8 passes — verified identical across Chronos/Toto/TimesFM and ρ=10/15.
- **Proposed wording:** narrow the caveat to the windows still unreplayed, **and add e13 as a stated boundary
  of the p90-headroom mechanism.** Adding e13 strengthens the thesis's honesty.
- **Also new, and conservative (A2 `a2_cost_accounting.csv`, 40 cells):** costing each policy both
  bill-from-readiness (the ledgered convention) and bill-from-order (each up-step pays its warm-up) **widens**
  the forecast's advantage — reactive churns 2–5× the worker-increments, and on burst5 L165 the cost order
  **flips**. This licenses stating that **0.62× is conservative**.

### 4.6 EXPLICITLY NOT RETIRED

- **Open-loop replay** (closedloop.tex:576-578): arrivals follow the trace regardless of experienced latency;
  overload cannot shed or defer demand. Endogenous demand (abandonment/retry) is untouched by all new runs.
- **Physical-anchor gap:** correctly scoped to a *live worker* at all three sites. No new silicon run changes it.
- **Encoder-pool live-loop gap** (validation.tex:153 ≡ conclusion.tex:108): unchanged.
- **Language-pool "calibrated" vs "physically validated"**: the distinction is maintained and must stay.
- **Fabric/handoff assumptions** (intro.tex:514, 516; conclusion.tex:103): the **sensitivity replay now
  exists** (§2.11, `fc_p90_L30_ds4`), which is why those two claims are CONFIRMED rather than unverifiable —
  but no experiment measured *transport*, and no DB column is parameterised by link speed. The `≥100 Gbps
  restores the quoted numbers` half is an exact **linearity identity** (4× payload / 100 Gbps ≡ 1× payload /
  25 Gbps), not an empirical result, and should be labelled as such. See **Q5** and §5.5.

---

## 5. CLAIMS THAT REMAIN UNVERIFIABLE (125)

These are not defects. They are claims the provenance DB **cannot** settle by construction. The thesis should
be explicit about which are **asserted** and which are **measured**. Grouped by *why* they cannot be settled.

### 5.1 Architecture / analytic facts — no experiment could settle them (~35 claims)

Example: `aiconfigurator.tex:174` "Tensor-parallel communication terms are analytic and zero at TP=1" —
`SELECT pool, tp, count(*) FROM provenance.runs GROUP BY 1,2;` shows `tp` NULL for every encoder row, but
**a populated tp=1 would record the configuration, not the analytic zero**. Also: encoder block count,
projector output dim (5120/4096 = 5/4), DeepStack merger blocks, patch count (448/16 = 28, 28² = 784), vision
tokens per image (784/4 = 196), tower parameter count (576 M × 2 B = 1.15 GB), model-family dims, Qwen3-VL
variants, KVBM tier count, Dynamo planner default targets, WAPE's algebraic properties.
**Recommendation:** keep; mark as architectural/analytic in text ("by construction", "from the checkpoint
config") rather than implying measurement. Backfill `runs.tp` anyway (§2.12).

### 5.2 Collector / profiler artifacts not modelled in `provenance.*` (~45 claims)

The whole `aiconfigurator.tex` kernel-ledger block (:288-296, :425-455, :513) plus :18, :36-37, :99-118,
:133-152, :185-204, :248, :500-524; `apendice.tex:215`. These live in `collector_artifacts/` and AIC's
`systems/data/rtx_5090/vllm/0.22.0/`, not in a run row. Several carry internal arithmetic checks that **do**
hold (9.624+1.736 = 11.360; 1.736/11.360 = 15.28 %; (1.342−1.300)/1.300 = 3.23 %; 0.459/9.624 = 4.77 %;
168.6/182 = 92.6 %) and two that **do not** — [E4] and BLOCKED-1.
**Recommendation:** cite the specific collector artifact path at each site; ingest the kernel ledger (§2.3).
**Special case — apendice.tex:215** (upheld INSUFFICIENT_DATA): the AIC denominator at 320²/640²/896² exists in
**no** archive (`aic` covers only 224/336/448/672), so neither the 1.09–1.11 means nor the 15.5 % bound is
reconstructible **or refutable**. Absence of the artifact is not evidence the numbers are wrong. Either persist
the AIC f(N) curve at those resolutions (§2.12) and re-verify, or, before submission, weaken the sentence to
cite only the resolutions with an archived AIC curve (224², 448²). **Do not change the numbers.**

### 5.3 Software / hardware versions and environment (~15 claims)

`related.tex:168` (Dynamo v1.3.0), `tese.tex:256`, `apendice.tex:39-52`, `apendice_ecosystem.tex:119-127`,
`aiconfigurator.tex:53-96`. `SELECT count(*) FROM provenance.runs WHERE engine IS NOT NULL;` → **2 of 2,206**;
`commit_sha` NULL on all; **no version field exists anywhere in the schema**.
- These are legitimately asserted from the environment record. Add the version field (§2.12) so future audits
  can check them.
- Two are checkable **outside** the DB and are wrong: [E16] (SM 2407 MHz) and [E30] (`-rc` tags).
- One is checkable outside the DB and is **right**: apendice_ecosystem.tex:125 (R41) — two independent
  site-packages carry `ai_dynamo-1.2.1.dist-info` with no `direct_url.json` (a built wheel), and
  `ai_dynamo-1.3.0.dist-info` carries `direct_url.json editable=true` pointing at a tree whose `pyproject.toml`
  declares `version = "1.3.0"`. Both post-1.0 (v1.0.0 tagged 2026-03-13).
- **related.tex:168** (upheld INSUFFICIENT_DATA): only the phrase "**this thesis's simulations**" (unqualified)
  overreaches, since apendice.tex:42 records the 1.2.1 wheel as the Phase-2 baseline runtime. If edited, make
  it a **narrowing**, not a new claim, and apply the identical narrowing at tese.tex:256 or not at all.

### 5.4 External citations and third-party results (~15 claims)

`related.tex:56, 57, 104, 153, 155, 174, 213, 289`; `intro.tex:442` (PR #1312); `aiconfigurator.tex:121`;
`apendice.tex:382` (commit b55dd0b7 — **partially corroborated**: the commit exists in the local
`ai-dynamo/aiconfigurator` history with the described patch_embed GEMM change).
**Recommendation:** verify PR numbers with `gh pr view` before submission; otherwise leave as citations.
`related.tex:56` carries a separate internal 1−1/G arithmetic mismatch with its own 3.3–5.5× parenthetical —
decouple the two figures **without naming a stage** (R47).

### 5.5 Derived analyses with no provenance column (~15 claims)

Threshold-crossing / detection-lead / false-alarm analysis (closedloop.tex:153, 156, 157, 171, 172, 175, 178,
209; conclusion.tex:65); handoff payload size (closedloop.tex:584); forecast inference cost (closedloop.tex:564
— note [E7] changes the per-forecast figure this rests on); rhetorical/structural counts (related.tex:9, 33,
182, 326, 355; apendice_ecosystem.tex:13, 22, 26, 70, 85, 146, 155).
**Fabric bandwidth is no longer in this group** — the `fc_p90_L30_ds4` sensitivity replay exists (§2.11) and
both intro.tex:514 and :516 are CONFIRMED against it. What remains is that no DB row is parameterised by link
speed, and the "≥100 Gbps restores it" half is an identity rather than a measurement. **State it as an
explicitly labelled analytic modelling assumption** (§4.6, **Q5**).

### 5.6 INSUFFICIENT_DATA that became verifiable (41 → 6 genuine gaps)

The adversarial pass overturned the **great majority** of the 41 INSUFFICIENT_DATA verdicts to CONFIRMED,
simply by consulting the archived artifact on disk instead of stopping at an empty query. Of the original 41,
only these remain genuinely undecidable:

| Site | Why still undecidable | Instruction |
| --- | --- | --- |
| intro.tex:431 (21.4 M rows) | ~~On-disk archive brackets it at 21.57–22.00 M; the DB is a partial ingest~~ **RESOLVED 2026-07-20:** the §2.9 ingest makes the DB reconcile to the archive file by file; `mode IN ('uni','cov')` = **21,404,640** = 21.4 M exactly | **NO EDIT** — now *verified in-store*, not merely un-refuted. The R29 weakening is **no longer needed**. §2.9, **Q1 answered** |
| intro.tex:448 (~17 % unlocked-clock inflation) | The unlocked dataset was **recollected and overwritten** (aiconfigurator.tex:84). Surviving proxies disagree: 11–19 % via the encoder_fn proxy, **27.3 %** via the one surviving kernel shape | **NO EDIT.** Honest remedy if forced: weaken to "well over 10 %". Locate a backup of the pre-relock collection |
| apendice.tex:215 (320²/640²/896²) | No archived AIC denominator at those resolutions | See §5.2 |
| related.tex:168, tese.tex:256 (runtime version) | No version field in the schema | See §5.3 |
| twopool.tex:118 (factoring probe) | No `(batch, images_per_request)` dimension in `collector_encoder_fn` | **NO EDIT** — corroborated contemporaneously at `progress/phase2-simulation.md:106-109` ("delta 0.000000 ms"). Ingest per §2.11 |
| trace-eda.tex:136, :317 | *Resolved* — both CONFIRMED by recomputation and by reading `f_fourier.py:73`. Listed only so nobody re-opens them | **NO EDIT, do not hedge** (R36, R37) |

**For every remaining item: either cite the artifact explicitly in text, or soften the claim. Never edit a
number off a truncated store.**

---

## 6. OPEN QUESTIONS

Stated as questions. None should be answered by guessing. Two of the previous nine are now **answered** and
retired; three are new.

**Q1 — What is the inclusion rule behind "21.4 million rows"? — ANSWERED 2026-07-20 (§2.9 ingest).**
intro.tex:431. The premise of the question was an artifact of the partial ingest. With the 5,269,200
covariate-mode rows loaded, `provenance.forecast` holds 22,003,500 and reconciles to the on-disk archive
file by file (41 files, zero mismatches). The inclusion rule is **the thesis-run corpus,
`mode IN ('uni','cov')`** — excluding the two families written *after* the manuscript (`*_expctx`
reforecasts, `ewma_cal_*` variants) — and it gives **21,404,640**, i.e. "21.4 million" **exactly**.
Excluding `ewma_cal_*` and `*_expctx` by filename gives the identical count, so the two natural readings
agree. The earlier **21,565,872** figure quoted here was wrong. **No edit to intro.tex:431; R29's
proposed weakening to "over 21 million" is unnecessary.** Canonical accessor:
`provenance.v_forecast_thesis_corpus`.

**Q2 — Is aiconfigurator.tex:444's 0.25 ms the absolute elementwise+layernorm time, or the excess over
prediction?** :293 and `collector_kernel_ledger` both give **1.18 ms** absolute at the same shape (448², N=1,
HF-eager). Ratio 4.7×. BLOCKED-1 cannot be resolved without this.

**Q3 — What is the predicted GEMM subtotal at 448²/N=1?** Without it the :452 residual ledger cannot be shown
to close (max attributed **0.597 ms** vs a **1.095 ms** gap). *Is the missing ≈0.5 ms a fifth term, or is one
of the published attributions understated?* [E4] weakens the claim in the meantime.

**Q4 — Should `tab:base-tp` be re-run at the corrected burst5 C\*=8?** The cells are exact at C=16 and the
sensitivity is ≈0.2–0.9 %, but the caption promises "at its static-optimal encoder count". *Re-run, or soften
the caption?* ([C15] proposes softening as the low-risk option.)

**Q5 — What is the actual inter-pool fabric in the deployment being modelled?** The 4×-payload sensitivity
replay now exists (`fc_p90_L30_ds4`: handoff p99 1,087.4 ms, encoder delay p99 1,403.8 ms), so intro.tex:514/516
are CONFIRMED — but no experiment measured *transport*, and the "≥100 Gbps restores the quoted numbers" half is
an exact linearity identity rather than a measurement. *Can a bandwidth sweep be added, or must this remain an
explicitly labelled modelling assumption?*

**Q6 — Does the 0.62× hold on the 99.96 % expanding-context span?** A15 shows identical SLA outcomes
(588.4 / 651.1 ms) at 99.96 % coverage, but no re-priced cost ratio exists for that span. *Is a re-price
planned, and would it move 0.62×?* Until answered, keep the cost claim on the 5.60-day span (§4.3).

**Q7 — NEW. How should the 0.9650 tie be printed?** The language-fleet ratio is **0.96501–0.96503** under all
three legitimate denominators — the exact 2-dp tie point, with inter-denominator spread (3e-5) larger than the
distance from the tie (1.5e-5). Two chapter reviews reached opposite conclusions; this ledger adopts **retain
0.96×** (R18) because closedloop.tex:373-375 prints 0.96 beside its own operands and is CONFIRMED. *Would the
author rather print **0.965×** at all four sites simultaneously (tese.tex:68, 114; conclusion.tex:85;
closedloop.tex:375), which is unambiguous and consistent?* **Whatever is chosen must be applied to all four
sites in one edit, or to none.**

**Q8 — NEW. Is `silicon_multiworker.json`'s `silicon_cstar=16` an independent confirmation or the same
artifact?** `verification/rerun-stability-e2e.md:120-122` says both cost models find burst5 non-divergent at
every C≥8 and that the silicon C*=16 is **also** an artifact. *Does the silicon path share the endpoint-backlog
heuristic (`trace_to_two_pool.py:528-534`), or did it reproduce 16 independently?* Determines whether §2.1 needs
a second correction.

**Q9 — NEW. Which runtime should `tab:sim-knees` cite?** Its polynomial steady cell prints **249**
(wheel runtime, `sweeps:llm_head2k_poly_s1` = 249.441) while `tab:sim-poly-aic` prints **248** (srcbuild =
248.465) for the **same run**. [E14] harmonises onto 248 because the chapter commits to srcbuild at :58-66.
*Confirm that tab:sim-knees was intended to be the srcbuild table too* — if it was deliberately the wheel table,
[E14] should instead become a footnote naming the two builds.

**RETIRED — old Q2 (which ITL definition backs validation.tex:161?).** **Answered.** `tab:val-anchor`'s ITL p99
is defined as (RequestLatency − TTFT)/(OSL − 1) = aiperf TPOT = `llm_run_summary.p99_tpot_ms` (forecast 9.718328,
reactive 152.681078), **not** `p99_itl_ms` (5.2875 / 160.2596). Live side from the aiperf export: 11.469605 /
150.744571. The published 11.5 / 9.7 / +1.8 ms / **18.0 %** are all exactly right (1.751277/9.718328 = 18.020 %).
Consequence: R2 — do not apply the 18.6 % "fix".

**RETIRED — old Q6 (which "26 files"?).** **Answered.** 26 = 6 models × 4 signals + 2 covariate variants —
exactly the set feeding `tab:pred-wape` and figures `pred-heatmap`/`pred-horizon`/`pred-band`/`pred-models`.
The other 13 of the 39 are 12 `*_expctx` and 3 `ewma_cal_*` files belonging to other rows. Consequence: R27.

---

## Appendix A: chapters with no surviving text defect of their own

- **tese.tex** — 3 mismatches reviewed, **0 edits**. The abstract and resumo are clean. Both 0.96× sites
  CONFIRMED (R18); the version footnote is unadjudicable (§5.3).
- **baselines.tex** — 16 reviewed, 2 THESIS_WRONG both overturned; 6 ARTIFACT_SUPERSEDED all upheld as **DB**
  defects (§2.1); 6 wording items ([C13], [C15]–[C19]). **No numeric edit to this chapter.**
- **intro.tex** — 13 reviewed, **11 overturned**; 0 THESIS_WRONG survive. Its single edit ([E27]) is the mirror
  of a related.tex fix. Its 2 remaining INSUFFICIENT_DATA items are §5.6 material; its restatements inherit
  [E1] and [C1].
- **closedloop.tex** — all 15 provenance mismatches overturned; the chapter's numbers are correct as printed.
  Its only edits ([E32], [E33]) come from the internal-arithmetic pass.
- **validation.tex** — all 3 reviewed mismatches overturned; both surviving edits ([E23], [E24]) were surfaced
  by *other* chapters' reviews going to disk.

## Appendix B: what the adversarial pass changed about method

Four method errors in the first pass account for nearly all 67 reversals. Any future audit should start here.

1. **Stopping at an empty query.** "Not in `provenance.*`" was read as "unverifiable". Going to the archived
   artifact on disk flipped the majority of INSUFFICIENT_DATA verdicts, including the entire fabric-conditional
   block, the 560-cell grid, the SOL bound, the live arm, and the spawn-latency measurement.
2. **Recomputing from printed cells.** Nine rejected fixes (R1–R6, R24, R44) were arithmetic on already-rounded
   values. Always re-read both operands unrounded.
3. **Comparing against the wrong file.** Six rejected fixes (R7–R11, R12) compared the thesis against a
   similarly-named sibling artifact. Identify the artifact from the body text *before* computing a residual.
4. **Querying the wrong column.** `runs.model` holds **forecast**-model names (hiding an entire 26-run 235B
   sweep); `p99_itl_ms` is not `p99_tpot_ms` (manufacturing a phantom 8 ms discrepancy). Confirm the column
   maps to the table's stated definition.

---

## Addendum (2026-07-21): R18 amended — 0.96x -> 0.965x; live error-count disclosure

Reviewer-caught, verified against primary artifacts before applying:

1. **Language-week ratio.** Raw operands: `simulation/results/llm_week/week_fc_p90.report.json`
   `gpu_hours = 518.6063`; static reference = 4 H100-GPUs x covered span
   (3,869,300 s / 8 = 483,662.5 s) = 537.4029 GPU-h. Ratio = **0.96502**.
   The printed `0.96x` was a mis-rounding (2-dp rounding of 0.965 is 0.97);
   corrected to **0.965x** at all 5 sites (abstract EN/PT, closedloop x2,
   conclusion). "Near-break-even" reading unchanged (strengthened). The
   request-matched 1.03x (518.6/503.7 = 1.0296) is unaffected.
   R18's original protection (against regressing to wrong-runtime values)
   remains; the protected value is now 0.965x (gate updated).

2. **Live validation populations.** aiperf exports: forecast tails over
   3,092 of 3,093 scheduled (1 InvalidInferenceResultError empty-response);
   reactive over 3,089 (4 HTTP-500 "Failed to generate completions").
   Disclosed in tab:val-anchor's caption; verdicts stated as
   latency-conditional on completed requests, not an availability grade.
   closedloop volume-of-evidence now says "scheduled requests".

### Addendum 2 (2026-07-21): billing-verb + compliance/cost-scope fixes (reviewer round 2)

1. conclusion RQ4 said the 0.62x worker-time was "billed at forecast-issue
   time" -- wrong verb: the encoder bills FROM READINESS (warm-up billed
   from order reported separately); the schedule is ACTUATED at issue time
   (closedloop's own convention). Fixed to "issue-time actuation, warm-pool
   readiness".
2. Compliance/cost merge: three sites attached the week-only 0.62x /
   "fraction of GPU-hours" saving to burst-level compliance clauses
   (conclusion RQ4, thesis-revisited, the intro thesis-statement quote).
   All three now scope the saving to the covered week and RQ4 names the
   boundary (per-burst every arm costs MORE than static). Also fixed a
   round-1 miss: conclusion RQ4 "every window" -> "every forecast-covered
   window".

### Addendum 3 (2026-07-21): v2 external audit absorbed (verified item-by-item)

All empirical claims in thesis_shortening_report_v2.md were verified against
primary artifacts/DB before application. CONFIRMED+APPLIED: intro RQ4
compliance/cost separation; cl-aggregate caption actuation-vs-integration;
0.965x scoping (Chronos-p90 + time-matched TP2x2) at promotion sites;
population enumeration (5 windows / 4 leads / 4 in-span episodes); abstract
EN/PT parity set (draft-PR status, one-live-run, hardest-burst, 5.60-day span,
worker-time units, persistence-not-causal); base-tp caption relabel (burst5
archived C=16, verified on disk; burst1-4 at C*); per-burst range population
(1.80=timesfm L30 warm b3, 2.90=timesfm warm b4, leads 15-45 verified in
factorial artifact); language folds 0.93-3.81x >1 in 6/7 (g4_folds verified);
cl-ewma floor cells REVERTED 588->589 per the harness's own artifact
(ewma_baseline_*.json p99=589.301 incl. the chronos control; my deep-verify
589->588 edit had relied on a DB population that never contained these runs)
with a cross-harness footnote; ITL 5.1->5.1-6.3; stale "remaining windows"
sentence; 3.1% dedupe + trace-token convention; AIC snapshot label +
cross-refs; manifest rows added (base-tp, cl-ewma, ledgers, folds, dynamo
registry, additive ablation, runtime logs, framework-diff, infill counts);
false pointers repaired. REFUTED (artifact evidence): P1.5's "one-minute
only" coverage narrowing -- quantile_coverage.json shows p90 coverage
0.881-0.901 at 15-SECOND bins across all models/signals, so the claim was
GROUNDED at both cadences instead. DEFERRED (structural, user decision):
ledger compaction, 200-word abstract rewrite, ~6k-word structural cut,
framework-diff deletion, question-only RQs.
