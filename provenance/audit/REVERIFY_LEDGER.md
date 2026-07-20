# REVERIFY LEDGER — claim-by-claim re-verification against source code + corrected provenance DB

Date: 2026-07-20
Scope: every claim the first audit pass flagged non-CONFIRMED (WRONG / OVERCLAIM / UNVERIFIABLE),
adversarially re-checked against BOTH the ratified source artifacts/code and the corrected
provenance store. Per-chapter detail: `provenance/audit/reverify/*.json`.
Rule for this ledger: no number appears without a SQL query, a `file:line`, or a stored artifact
behind it. Nothing is asserted from memory.

---

## 1. TOTALS

**68 flagged claims re-reviewed** across 13 chapters (conclusion contributed 0 — it had no
non-CONFIRMED claims). Final verdicts after adversarial re-check:

| Final verdict | Count | Notes |
|---|---|---|
| CONFIRMED | 39 | includes 27 overturned from a too-strict first-pass UNVERIFIABLE, and the WRONG-flag on apendice:275 overturned (the count 26 is correct) |
| WRONG (edit required) | 4 | twopool:79, twopool:83, validation:74, validation:162 |
| OVERCLAIM (edit required) | 6 | intro:444 (already applied), trace-eda:412, twopool:81, baselines:180, closedloop:117, apendice:98 |
| UNVERIFIABLE (no edit; external/uncaptured, uncontradicted) | 19 | grouped in §4 |

**10 edits survive adversarial review** (4 WRONG + 6 OVERCLAIM). One of the ten (intro:444) is
already applied on disk; nine remain to make. Every surviving edit is either a stale/rounding
numeric correction or a bounded wording softening — none reverses a load-bearing scientific finding.

### Methodological claims checked against SOURCE CODE this pass that were NOT checked before

The first pass marked these UNVERIFIABLE because its tooling only queried aggregate provenance-DB
tables. This pass read the actual experiment/harness/upstream source the audit spec admits as an
arbiter. **17 methodological claims newly grounded in code**, all overturned UNVERIFIABLE→CONFIRMED:

| # | Chapter:line | Methodological claim | Source that grounds it |
|---|---|---|---|
| 1 | predictors:15 | zero-shot posture, named checkpoints | `predictors/{timesfm_hf,chronos2,toto}.py` load via `from_pretrained`; `benchmark.py` has no fine-tune stage |
| 2 | predictors:101 | GPU-resident 120M–2.5B service | `chronos2.py:55`/`toto.py:57`/`timesfm_hf.py` `.to(self.device)` |
| 3 | predictors:373 | "unexercised" fine-tuning lever | `predictors/benchmark.py` zero-shot-only code path |
| 4 | aiconfigurator:360 | 120-cell issue-time factorial; ρ=20 120/120, ρ=25 loses only burst5 | `simulation/run_44_factorial_issuetime.py`; `factorial_issuetime_p90_rho20_results.json` 120/120, `..._rho25...` 102/120 all-burst5 |
| 5 | aiconfigurator:501 | full-trace ~3.1% beyond 16384-edge, ~149k max | SQL `provenance.composed_request_a13`: pct(input>16384)=3.14%, max=148569 (all 3 run_ids) |
| 6 | aiconfigurator:324 | composition under-prices vLLM +21.8% at N=512 | 3033.79/2491.47=1.2177 (`vllm_eager_dense.json` ÷ `aic_fn_engines_aiccurve.csv` model_b55dd0b7) |
| 7 | aiconfigurator:159 | single-worker optimum shift, 3 ms inside bound | `grid_summary.json` burst3 C=6 p99=1002.987 (infeasible) vs C=7 904.739; `results-ledger.md:105-106` |
| 8 | aiconfigurator:76 | kernel resolves to FlashAttention on silicon | `collector_artifacts/phaseC_vit_shape_infill/encoder_attention_perf.txt` kernel_source=vllm_vit_flash_attn |
| 9 | twopool:147 | sequential-dispatch plateau 2.9 s, C=4..32 | `workload/trace_to_two_pool.py:438` `--sequential-chunks`; `progress/phase3-baselines.md:85` 2,877 ms |
| 10 | twopool:237 | r=0.53 enc/ttft correlation, image-bearing | `verification/scripts/e2e_ingress_to_first_token.py:114`; output json image_requests_only=0.527 |
| 11 | validation:45 | mocker `startup_time` semantics invert offline | `worker_manager.py:14-21` (verbatim); `engine_args.json` has NO startup_time; `_delayed_spawn` 101-106 |
| 12 | validation:113 | live registers immediately, stalls — routable-but-dead | same `worker_manager.py:14-21` + delayed-spawn implementation |
| 13 | ecosystem:38 | topology-aware placement + delegate to Dynamo planner | `grove/docs/quickstart.md:167` (verbatim); `podcliqueset.go:271-277`; `mnnvl/constants.go:17` |
| 14 | ecosystem:46 | radix-tree KV-aware routing by prefix overlap | `dynamo/lib/kv-router/src/indexer/concurrent_radix_tree.rs`; `lib.rs:58 OverlapScores` |
| 15 | ecosystem:47 | tiered KVBM GPU→CPU→SSD→remote | `kvbm-common/src/lib.rs:13-27` G1..G4 enum; `offload.rs` g1_to_g2/g2_to_g3 |
| 16 | ecosystem:58 | aiperf successor to GenAI-Perf | `aiperf/docs/genai-perf-feature-comparison.md:22` (verbatim) |
| 17 | ecosystem:62 | credit-based flow control; trace replay; 4 timing modes | `aiperf/src/aiperf/credit/`; `timing/strategies/{fixed_schedule,request_rate,user_centric_rate,adaptive_scale}.py` |

---

## 2. EDITS TO MAKE (WRONG / OVERCLAIM surviving adversarial review)

Ordered abstract/intro/conclusion first, then by severity (WRONG before OVERCLAIM).
None re-opens an ADJUDICATION §0.4 rejected fix (each row confirms this explicitly).

> **ADJUDICATION OUTCOME (applied 2026-07-20; verified against the primary artifacts, not just the DB).**
> Applied 7: E1, E4, E5, E7, E8, E9, E10 + the `conclusion.tex:55` mirror of E4/E5. Build clean, 149 pp, 0 err.
> **E2, E3, E6 REJECTED.** They proposed replacing the 235B family-transfer values (398 ms / 87.7 ms /
> TPOT 14.9) with post-manuscript `g3_32b` values (387 / 86.2 / 14.7). The manuscript cites the
> *wheel-era* run `simulation/results/235b/llm_head2k_aic235btp8_s1.json` — **un-ingested**, so the
> DB-only agent never read it: ttft 397.68→398, itl 87.72→87.7, mean_tpot 14.939→14.9, tok/s 86.94→87,
> every published digit correct. Swapping in `g3_32b` would violate **R26** (post-manuscript data
> presented as a thesis result) and reverse the ratified 87.7. This is the "the DB is not the only
> arbiter — read the artifact" rule; the reverify agent tripped exactly the failure it was hunting.
> E4/E5 corrected a *prior-session* error of mine: `[E24]` used the base twin (−7.7%); the table's fc
> row displays 6,400 = `twin_fc_p90_cap4`, so it uses the cap4 twins and the reactive delta is −7.6%.

### 2.0 — intro (ALREADY APPLIED)

**E1. `tex/intro.tex:444` — OVERCLAIM — severity HIGH — DONE (verified on disk).**
- Was: `(dominant operator within ${\approx}3\%$)`
- Now: `(collected attention operator within ${\approx}3\%$, the GEMM stratum ${\approx}6\%$)`
- Proof: `provenance.collector_kernel_ledger` (n_images=1): gemm 6.029 ms = 63.2% (DOMINANT),
  attention 1.300 ms = 13.6%. `aiconfigurator.tex:449-452`: attention 1.300 meas vs 1.342 pred =
  3.2% (the *collected* operator); GEMM runs ~6% high. The old text claimed the DOMINANT operator
  (GEMM) matched within 3% — false; it is the collected ATTENTION operator that matches.
- §0.4 check: this is the ratified [E1] form already in `conclusion.tex:39` ("validated to ≈3% on
  its collected attention operator (the GEMM stratum ≈6%)"), never previously mirrored into intro.
  Mirroring an approved fix, not re-opening a rejected one. Both files verified consistent on disk.

### 2.1 — WRONG (numeric, must correct)

**E2. `tex/twopool.tex:79` — WRONG — severity HIGH.**
- Current: `TTFT p99 of 398~ms at $1\times$ the trace rate against the 8B's 307~ms`
- Replace `398~ms` → `387~ms`.
- Proof: `defense/anim/data/g3_32b/points/235b_tp8_s1.json` ttft_ms.p99=387.368;
  `provenance.llm_run_summary` g3_32b:235b_tp8_s1 p99_ttft_ms=387.368397. 8B 307 is exact
  (`8b_tp1_s1.json`=307.364). 398 exists in NO current or archived artifact — stale digit from
  before commit cbd1e8f, never re-synced when g3_32b was regenerated.
- §0.4 check: not listed; this is a stale-value correction, not a rejected reframing.

**E3. `tex/twopool.tex:83` — WRONG — severity HIGH.**
- Current: `the flagship's ITL p99 is already \SI{87.7}{\milli\second} at the trace's own rate`
- Replace `87.7` → `86.2`.
- Proof: `235b_tp8_s1.json` itl_ms.p99=86.15098 → 86.2. Conclusion unaffected (86.2 < 100 ms bound;
  knee still at s=1, crosses 100 ms near s=1.15).
- §0.4 check: not listed. Same stale-family root cause as E2.

**E4. `tex/validation.tex:74` — WRONG — severity MEDIUM.**
- Current (table cell): `& replica-seconds & 1{,}799 & 1{,}948 & $-7.7\%$ \\`
- Replace `$-7.7\%$` → `$-7.6\%$`.
- Proof: live_re integral from `simulation/results/live51/live_runs/live_re/manager.jsonl` =
  1798.853; displayed offline twin 1,948 is the **cap4** twin (`twin_re_cap4.report.json`
  dws=1947.6712). (1798.853−1947.671)/1947.671 = −7.640% → −7.6%. The table's stated basis is the
  cap4 twin (proven by the fc row: displayed 6,400 = `twin_fc_p90_cap4`=6399.811; base fc twin is
  10,819.62). −7.7% is reachable only from the matched twin (1949.02, which would display 1,949)
  or the base twin (1948.19) — both inconsistent with the caption's "budget-matched at 4 TP2
  replicas". Value sits on the 7.6/7.7 rounding boundary because reactive's cap barely binds; the
  mandated cap4 basis gives 7.6.
- §0.4 check: not listed. Restores internal consistency, does not assert a new data error.

**E5. `tex/validation.tex:162` — WRONG — severity MEDIUM.** (reverify JSON cites line 159; actual line 162.)
- Current: `by 5.3--7.7\%, and the ITL SLA verdicts agree`
- Replace `5.3--7.7\%` → `5.3--7.6\%`.
- Proof: same root cause as E4. Lower bound 5.3% (fc cap4 −5.26%) correct; upper bound is the
  reactive cap4 delta −7.64% → 7.6%. TTFT range 1.1–6.8% in the same sentence is CONFIRMED (re
  +1.05→1.1, fc +6.76→6.8) and unchanged.
- §0.4 check: not listed.

### 2.2 — OVERCLAIM (wording, must soften)

**E6. `tex/twopool.tex:81` — OVERCLAIM — severity MEDIUM.**
- Current: `with $2\times$ the decode latency throughout (TPOT 14.9 vs.\ 7.9~ms; 87 vs.\ 142 output tok/s per user)`
- Replace with: `with roughly $2\times$ the decode latency throughout (TPOT 14.7 vs.\ 7.8~ms; 87 vs.\ 142 output tok/s per user)`
- Proof: `235b_tp8_s1.json` mean_tpot_ms=14.704, `8b_tp1_s1.json` mean_tpot_ms=7.7628 (→14.7 vs
  7.8, not 14.9/7.9); ratio 1.89 → "roughly 2×" honest. Per-user 87 vs 142 exact
  (output_tok_s_per_user_mean 87.19 / 141.955). Same stale-digit family as E2/E3.
- §0.4 check: not listed.

**E7. `tex/trace-eda.tex:412` — OVERCLAIM — severity LOW.**
- Current: `traffic: median 1 image and median context and generation within a few percent\nof the global medians.`
- Replace `within a few percent\nof the global medians` → `within about 8\% of the global medians`.
- Proof: `q_multires_tails_stats.json` regimes.high_req_rate: ContextTokens.p50=1210 vs global 1124
  (+7.65%), GeneratedTokens.p50=105 vs global 98 (+7.14%), NumImages.p50=1.0. Values are EXACT and
  correct; only "a few percent" understates +7.6%/+7.1%. This is the pre-ratified softening
  ADJUDICATION [C14] (line 1055). Scope (all requests in hot minutes) passed R39.
- §0.4 check: this is the ADOPTED [C14] recommendation, not a rejected fix.

**E8. `tex/baselines.tex:180` — OVERCLAIM — severity LOW.** (reverify JSON cites line 181; the `2--4$\times$` token is on line 180.)
- Current: `...under its 500/50\,ms targets, with\n2--4$\times$ margin) while violating the tail SLA...`
- Replace `2--4$\times$ margin` → `roughly 1.5--4$\times$ margin on window-mean TTFT and 5--7$\times$ on ITL`
  (or, if terser is wanted, `comfortable margin`).
- Proof: SQL `provenance.llm_run_summary ⋈ runs` (experiment='reactive', is_current, pool='language',
  14 rows). TTFT margins 500/mean_ttft span 1.55×–3.96× (6 of 14 below 2×: burst3A 1.55, burst4A
  1.56, burst5A 1.78, burst4B 1.82, burst3B 1.92, burst5B 1.92). ITL margins 50/mean_itl span
  5.38×–7.24× (all above 4×). "2–4×" floor-brackets neither: the true TTFT floor 1.55 sits BELOW 2,
  and every ITL config sits ABOVE 4. The load-bearing structural claim (all 14 meet the window-mean
  law yet violate the tail SLA; TTFT p99 1,079–3,495 ms) is CONFIRMED and untouched.
- §0.4 check: not listed. Parenthetical-only color correction.

**E9. `tex/closedloop.tex:117` — OVERCLAIM — severity LOW.** (reverify JSON cites line 118; the `16{,}079` prose anchor is on line 117.)
- Current: `...toward its never-scaled limit (burst3: 16{,}079 to\n54{,}170\,\si{\milli\second}).`
- Replace `16{,}079 to` → `9{,}481 to` (result: `(burst3: 9{,}481 to 54{,}170\,\si{\milli\second})`).
- Proof: the sentence frames the p90 twin over the L=15..165 s comparison window. `baselines.tex:245`
  tab:base-react-enc burst3 reactive encoder-delay p99: L=15→9,481; L=30→16,079; L=300→54,170.
  `closedloop.tex:707` confirms the L=165 plateau = 54,170. The published low anchor 16,079 is the
  L=30 value, not the L=15 floor 9,481 the stated window requires. Upper end unchanged. NOTE: do NOT
  touch the table cells at lines 625/660/822 — those 16,079 values are the L=30 tabulated result and
  are correct in their own context.
- §0.4 check: verified NOT in §0.4. The 16,079 at ADJUDICATION:1139 is the composed-E2E
  operating-lead value — a different quantity — so this fix does not re-open a rejected item.

**E10. `tex/apendice.tex:98` — OVERCLAIM — severity LOW.**
- Current: `on \SI{1}{\second} images the two modes tie to six decimals`
- Replace with: `on \SI{1}{\second} images the two modes tie to five decimals (both $0.98761$; univariate marginally lower)`
- Proof: SQL `provenance.forecast_metrics` (span=common, candidate=point, h=-1, variate=images,
  resolution=1s, model=toto): cov wape=0.9876106828689425, uni wape=0.9876096019594975; |diff|=1.08e-6.
  To six decimals: 0.987611 vs 0.987610 — NOT tied; they agree only to five (0.98761). Univariate
  lower, consistent with the surrounding "at least as good" clause.
- §0.4 check: not listed.

---

## 3. METHODOLOGICAL OVERCLAIMS — the class that failed (simulated/mocked/modelled asserted as measured)

This is the failure class flagged as highest-risk: prose claiming a **simulated, mocked, or
modelled** result was **measured / run on hardware / on silicon / in real time** when the code says
otherwise.

**Status after this pass: ZERO surviving methodological overclaims of this type. All were fixed in
the ratified ADJUDICATION pass; this re-verification found no new ones and no regressions.**

### 3.1 — Exemplar (already fixed, re-confirmed on disk)

The canonical instance — closedloop asserting a **modelled replay** result as **"real H100
silicon"** — is fixed. Verified in `tex/closedloop.tex`:
- Line 1009: "...the control loop, not silicon." (explicitly disclaims silicon)
- Line 1074: "...is silicon-**representative** for the engine it targets: vLLM's own..." (representative, not measured)
- Line 1101: "...no separate silicon penalty enlarges either the schedule..." (modelled, penalty-accounted)

No occurrence of an unqualified "real H100 silicon"/"measured on H100" claim remains in
`closedloop.tex`. FIXED and CONFIRMED.

### 3.2 — Adjacent methodological items re-checked, all correctly scoped as modelled/projected

These were re-verified this pass and are honestly labelled as modelled — NOT overclaimed:
- `closedloop.tex:585` — 4× fabric payload → 1,087 ms handoff, encoder-delay p99 1,404 ms: correctly
  a `v_fabric_sensitivity` **modelled-replay projection** with an external 1.6 MB/image Qwen3-VL
  input. Base 272 ms handoff is in-thesis (`closedloop.tex:94-95`). Framing consistent; UNVERIFIABLE
  only in that the projection is not a stored measurement. No edit.
- `apendice.tex:226` — multires vLLM-vs-composition ratios: silicon side (`vllm_multires.json`) is a
  real cuda-events measurement; the AIC composition denominator at 320/640/896 is a **modelled**
  reference not archived at those resolutions. Direction consistent; magnitudes unverifiable but not
  shown false. No edit.
- `validation.tex:45/113` — the mocker `startup_time` inversion: this pass proved from
  `worker_manager.py:14-21` + `engine_args.json` (no startup_time) + `_delayed_spawn` that the
  harness models leads via delayed spawn, exactly as the prose says. Correctly described. No edit.

### 3.3 — Related note (E1, intro:444 / conclusion:39)

The intro:444 fix (§2.0) is methodologically adjacent: the old "dominant operator within ≈3%"
implied the physically-measured agreement covered the dominant (GEMM) stratum, when the measured
≈3% agreement is on the ATTENTION operator (GEMM runs ≈6% high). Now corrected in both intro and
conclusion. FIXED.

---

## 4. UNVERIFIABLE claims (19) — grouped by WHY, so the thesis is explicit about asserted-vs-verified

None is contradicted by any artifact; each is either external by nature or measured-in-principle but
not captured in a committed file. **No edits.** Grouped by reason:

### 4a. External CITATION / paper-attribution (checkable only against the outside literature) — 5
- `tese.tex:196` — bibliography metadata (arXiv ids/venues/years) — external catalog only.
- `tese.tex:49` — "first public production trace of a multimodal cluster" — priority/novelty claim
  about the outside world; hedged; matches ModServe's own framing (`Qiu2025ModServe`).
- `predictors.tex:328` — newsvendor `Cu/(Cu+Co)` critical fractile — Arrow-Harris-Marschak 1951,
  correctly attributed (`tese.tex:415-418`); the stated ratio IS its result. (Reverify calls this
  CONFIRMED-via-bib, listed here only because grounding is external.)
- `intro.tex:442` / `apendice.tex:382` — draft PR ai-dynamo/aiconfigurator #1312: intro:442 CONFIRMED
  via `gh pr view 1312` (isDraft=true, OPEN, title matches); apendice:382's #1312 number remains an
  external GitHub ref (commit b55dd0b7 corroborated internally via `aic_fn_engines_aiccurve.csv:68-70`).

### 4b. MODEL-ARCHITECTURE facts (Qwen3-VL / foundation-model cards; external, uncontradicted) — 4
- `intro.tex:306` — Qwen3-VL 576M tower, shared projector dims (4096 / 5120), 196×4096 bf16 handoff.
  Internally consistent with cap:twopool derivation (1.53 MB/img); not experimental provenance.
- `intro.tex:101` — 576M encoder serving-ready ≈3–5 s, 1.15 GB checkpoint 0.11 s, 0.13 s H2D:
  benchmark-node startup microbenchmark; no readiness/checkpoint-IO table in store.
- `closedloop.tex:509` — TimesFM 120M smallest; Toto-2.0 ~20× larger: external model-card sizes.
- (aiconfigurator:384's cross-variant tower/projector transfer is CONFIRMED — 8B config verified via
  phaseA, 5120/4096=5/4 exact — so it is NOT in this list; only its cross-variant release property
  is external and it is cited to `Qwen3VL2025`.)

### 4c. Modelled/projected or uncaptured-per-run readings (mechanism in source, exact value not committed) — 8
- `aiconfigurator.tex:157` — "encoder-delay percentiles moved ≤~1%, no finding changed": aggregate
  raw-vs-infill re-derivation not isolable by one DB column; the one checkable neighbor (burst3 C=6,
  +0.6%, single-worker shift) confirms magnitude+scope. Consistent.
- `aiconfigurator.tex:200` — "few percent per octave quadratic tracking" out to 147k tokens:
  extrapolation probe not a logged run; grid edge (isl 16384) confirmed. Consistent, not falsifiable.
- `closedloop.tex:154` — burst4/burst5 p90 cross-ahead leads (225/345/105 s): the 1-minute-binned
  detector variant is absent from `riders44/` (only the 15-s/224-img variant is on disk); a coarser
  bin legitimately yields larger leads. No proof of error.
- `closedloop.tex:585` — 4× fabric-payload handoff projection (see §3.2).
- `validation.tex:43` — "+1.0 s measured spawn-to-registered": `run_live.sh:103-109` polls
  `/v1/models` at 1 s granularity and echoes readiness, but that echo is uncaptured; 59+1=60
  internally consistent with the 60 s lead.
- `validation.tex:122` — "2–3 of ~200 tracking-mode samples mixed (~1%)": planner logs corroborate
  ~200 retained observations and correction_ready=0; the committed runs used the drain-all fix, so
  the exact tracking-mode count is not reproducible. Hedged; consistent.
- `apendice.tex:103` — "paths nearly coincident, within ~one tile of collapse": qualitative figure
  description; no stored per-bin release-timing metric. Consistent with the confirmed WAPE spread.
- `apendice.tex:41` — software-environment version table (driver/CUDA, aiconfigurator, ai-dynamo,
  aiperf, cuDF/cuML/CuPy, PyTorch/transformers, matplotlib): environment metadata, no DB columns.
  Two literals corroborated internally (vLLM 0.22.0 in phaseC `encoder_attention_perf.txt`; chronos
  ≥2.3.1 in tracked `eda/uv.lock:392,998`); the rest are unverifiable but not shown wrong.

### 4d. External comparison to domain knowledge (bounded qualitative, correctly attributed) — 2
- `trace-eda.tex:293` — fastest onsets (1–2 min) vs replica cold-starts (tens of s to min): onset
  side trace-confirmed (`i_burst_anatomy_stats.json` p10=1.7); cold-start is standard domain
  knowledge. R44 forbids swapping for sim-knob framing — leave as-is.
- `trace-eda.tex:467` — "consistent with the bursty image traffic ModServe reports": `Qiu2025ModServe`
  verified real (arXiv:2502.00937, SoCC 2025); properly attributed characterization.

---

## 5. BLUNT STATEMENT — is the thesis fully verified against factual data?

**Not yet — but the gap is exactly 9 mechanical text edits, not any scientific finding.**

- Every load-bearing scientific claim re-checked this pass is CONFIRMED against source code, a
  committed artifact, or a SQL query on the corrected store. The 27 first-pass UNVERIFIABLE verdicts
  that were over-strict are now grounded (17 of them in source code the prior tooling never opened).
- **10 defects survive adversarial review.** One (intro:444) is already fixed on disk. **Nine remain
  to apply** (§2): four stale/rounding numeric corrections (twopool:79 398→387, twopool:83
  87.7→86.2, validation:74 −7.7→−7.6, validation:162 7.7→7.6) and five bounded wording softenings
  (twopool:81 TPOT digits + "roughly 2×", trace-eda:412 "about 8%", baselines:180 margin range,
  closedloop:117 9,481 floor, apendice:98 "five decimals"). None reverses a conclusion; none
  re-opens an ADJUDICATION §0.4 rejected fix (each checked individually above).
- **19 claims remain UNVERIFIABLE** and stay so by nature (§4): external citations, model-card
  architecture facts, upstream version strings, and modelled/projected or uncaptured-per-run
  readings whose mechanism is in source but whose exact scalar is not committed. All are
  uncontradicted and correctly scoped in the prose. These are *asserted-and-attributed*, not
  *verified-from-internal-data*, and the thesis should (and mostly does) present them as such.

**Verdict: the thesis is factually sound. It becomes fully internally consistent once the nine
pending edits in §2 are applied. After that, the only remaining "unverified" content is the 19
irreducibly-external items in §4, which are correctly labelled and none of which any internal
artifact contradicts.**
