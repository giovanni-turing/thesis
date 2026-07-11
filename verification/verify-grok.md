# Fact-Check of the Grok Committee Review

Scope: verify every finding in `grok/report.md` + `grok/cross-check.md` (R1–R13,
S1–S15, cross-cutting, D1–D5) against ground truth — thesis `tex/*.tex`, code,
artifacts, papers. Verdicts recompute or read source; nothing outside
`verification/` modified. `*-assessment.md` files were not read.

IMPORTANT META-FINDING: the Grok reviews are timestamped 2026-07-10 16:54–16:57.
Several thesis `.tex` files were edited AFTER that (17:05). Git commit
`ba96acf "tex: fix false 'both ITL p99 sub-bound' claim (grok committee D1/R1)"`
shows the author already applied the top-ranked fix. So for R1/D1 the *finding was
valid at review time but is ALREADY FIXED in the current tex.* Each finding below
is judged against the CURRENT tex state.

---

### D1 / R1 — Reactive ITL "sub-bound / far under bound" is false
Target: `conclusion.tex:47-49`, `intro.tex:498-501` (current); table `validation.tex:64-72`
Verdict: CONFIRMED (underlying fact) — but ALREADY-FIXED in current tex
Severity: major (was); now resolved
Evidence:
- Live artifacts recomputed: `live_runs/live_re/profile_export_aiperf.json` →
  reactive ITL p99 = **150.74 ms** (live), `twin_re_cap4.report.json` p99_itl = **160.26 ms**
  (offline). Both exceed the 100 ms bound (predicate `validation.tex:56`). Forecast ITL:
  live 11.47 ms, twin 5.287 ms → sub-bound. Table `tab:val-anchor` (11.5/5.3, 150.7/160.3) is exact.
- Grok quoted `conclusion.tex:47` = "both ITL p99 also sub-bound" and `intro.tex:498-500` =
  "stay far under bound". CURRENT text reads: conclusion "forecast sub-bound, reactive **above
  bound in both**"; intro "sub-bound for the forecast policy … and **above** the 100 ms bound
  for the reactive policy, 150.7 versus 160.3 ms". The false wording is gone.
- Git: `ba96acf` explicitly credits "grok committee D1/R1".
If ALREADY-FIXED: the diagnosis was correct (reactive genuinely FAILS ITL); the specific
sentences Grok flagged no longer exist. No further action needed on this item.
Dup-hint: ITL sub-bound false; codex/opus likely flagged same, now fixed.

---

### D2 / R2 — Abstract "live Dynamo" adjacency over-extends the live anchor
Target: `tese.tex:57-61`; scope `validation.tex:133-146`
Verdict: PARTIAL (rhetorical overreach, not a false number)
Severity: moderate
Evidence:
- Abstract chains cost ratios then "both verdicts reproduce on the live Dynamo runtime" in one
  sentence (`tese.tex:59-61`). The live anchor is scoped in `validation.tex:133-140` to: one
  window (burst3), language pool only ("the encoder pool's controller exists only in
  simulation"), two policies, mocked engines. So the encoder economics (0.27–0.31×) are
  simulation-only; the abstract's adjacency invites reading the live result as pricing transfer.
- BUT "both verdicts reproduce" is literally true (forecast PASS, reactive FAIL, verified live +
  twin). It over-scopes by placement, not by asserting a false fact. Conclusion (`:44-49`) and
  intro (`:494-503`) and Scope (`intro.tex:494`) already bind it to "language pool / mocked
  engines / fastest-onset burst".
If PARTIAL: the number is honest; only the abstract lacks the pool/window/mock qualifier the body
carries. A defensible finding, but weaker than "major" — the body scoping is thorough.
Dup-hint: abstract live scope; cross-model overlap likely.

---

### D3 / R8 — "Order-of-magnitude knees" without censoring qualifier
Target: `tese.tex:53-54`; body `twopool.tex:250,276-281`, `tab:sim-knees`
Verdict: PARTIAL / CONFIRMED-as-worded (body already discloses; abstract does not)
Severity: minor
Evidence:
- `tab:sim-knees` marks the vision steady-window knee "**≥ s=32 (cens.)**" — never crossed within
  the swept range. `twopool.tex:277-281`: "vision pool is uncrossed at 32× … the demonstrated
  separation is a factor **>10** … a lower bound". So the thesis body explicitly states the knee
  is censored and the separation is a *lower bound*.
- The abstract (`tese.tex:53-54`) and conclusion (`:16-17`) say "an order of magnitude apart"
  without the "≥ / lower bound / locked 2×2" qualifier. Grok's point is a wording gap in front
  matter only; the numbers are not contradicted.
Dup-hint: censored vision knee lower-bound.

---

### D4 — Abstract dual-pool failure equality vs token-accounting caveat
Target: `tese.tex:54-56`; intro `:489-491`; `twopool.tex:380-402`
Verdict: PARTIAL
Severity: minor
Evidence:
- `twopool.tex:398-400`: "the burst-window language verdict is convention-dependent while the
  vision verdict is not"; intro `:489-491` says the burst language pass "is also
  token-accounting-convention-dependent … the TP1 prefill floor and the vision-pool verdict are
  not." So the asymmetry is stated in intro + twopool.
- Abstract `:54-56` labels the two failures as "a shape-fixable prefill floor; episodic encoder
  queueing at 29% mean utilization" — it *does* distinguish them (one shape-fixable) but omits the
  token-convention fragility of the language TP2 margin. Minor front-matter softening, not a
  contradiction.
Dup-hint: token-convention language TP2 fragility.

---

### D5 / R7 (part) — "Five bodies" vs six review sections in related.tex
Target: `related.tex:9-11`; also `intro.tex:508`
Verdict: CONFIRMED (self-contradiction / undercount)
Severity: minor (hygiene)
Evidence:
- `related.tex:9-11` opens "**Five bodies** of work border this thesis:" and names exactly five
  (LLM serving, multimodal serving, autoscalers, workload characterization, time-series
  forecasting). `intro.tex:508` echoes "the **five literatures** it borders".
- `grep '\section{'` yields SIX review-body sections + Positioning:
  Serving LLMs (`:18`), Serving multimodal (`:49`), Autoscaling (`:99`), Workload characterization
  (`:186`), Time-series forecasting (`:219`), **Simulators and performance models (`:258`)**,
  Positioning (`:282`). The "Simulators" body is a full section (Vidur, LLMServingSim, Dynamo
  mocker, aiconfigurator) plus a positioning-table column ("Calibrated simulation"), but is
  excluded from the "five" count. Genuine undercount.
Dup-hint: five vs six bodies; codex/opus likely caught.

---

### R2/C3 / R3 — Fabric/handoff is a boundary condition of the headline payoff
Target: `intro.tex:475-481` (Scope); `closedloop.tex:385-398`; conclusion `:81-83`
Verdict: CONFIRMED (finding valid); PARTIALLY pre-addressed
Severity: moderate
Evidence:
- The 588 ms floor + 0.27–0.31× assume embedding-only handoff or ≥100 Gbps: `closedloop.tex:388-396`
  quantifies the 4× DeepStack payload on 25 Gbps raising p99 handoff 272→1087 ms (encoder-delay p99
  1404 ms — SLA violation from transfer alone, "every policy violates … including static C=16, p99
  1311 ms"). Verified as an internal sensitivity claim; artifact `aggregate44_rho/static_C16_ds4`
  p99 = 1311.3 ms confirms the ds4 (4×) static-C16 number exactly.
- Grok's ask: surface this next to the *first* sale of the ratio (abstract/RQ4), not only in
  Scope/limits. Current state: it IS in `intro.tex` Scope (`:475-481`), `closedloop` limits, and
  conclusion bounds (`:81-83`) — but the abstract and RQ4 headline sentences omit it. So the
  finding is a placement/emphasis fix, and the substance is already documented and numerically
  self-consistent.
Dup-hint: 25Gbps DeepStack breaks all policies.

---

### R4 / C4 — Single-trace universality vs thesis-statement wording
Target: `intro.tex:196-208`; `conclusion.tex:85-89`; `trace-eda.tex:461-474`
Verdict: CONFIRMED (valid scoping critique); largely pre-addressed
Severity: moderate
Evidence:
- Thesis statement (`intro.tex:197-208`) is worded universally ("In a modality-disaggregated
  multimodal serving system, no single load signal can size every pool…"). Evidence is one 7-day
  Azure trace with by-construction 50/50 split (`trace-eda.tex:26,455`, `predictors.tex:402-404`,
  `closedloop.tex:419-422`).
- The thesis already scopes this heavily: `trace-eda.tex:461-474` ("Everything in this chapter
  describes *this* trace … the generality argument runs through mechanism, not sampling … The
  claim is falsifiable"), and conclusion bounds `:79-89`. Grok's specific extra ask — soften "each
  leans conservative" (`conclusion.tex:88`) because external validity is a *limit* not a
  measurement-conservatism — is a fair, narrow wording point. Verdict: valid, mostly addressed;
  the "leans conservative" phrase is the residual over-strong clause.
Dup-hint: single-trace universal statement.

---

### R5 / C5 — "TSFMs beat every baseline on every signal / all twenty cells" on a soft suite
Target: `predictors.tex:151-152,167-199,384-390`; `tese.tex:49-50`; `conclusion.tex:26-33`
Verdict: CONFIRMED (all sub-facts true) — but thesis ALREADY qualifies heavily
Severity: moderate
Evidence (recomputed from `predictors/results/metrics/`):
- Table 1 (`tab:pred-wape`) reproduced EXACTLY from `metrics_overall.parquet` (all 40 cells match,
  e.g. 1-min images: Chronos-cov 52.9 / EWMA 54.2 / naive 67.8 / HW 69.4). "Beat every baseline in
  all twenty cells" holds, but the margin over EWMA is 2–9% at 1-min (thesis states this at `:153`).
- HW **worse than naive** confirmed (1-min img 69.4 > 67.8; 1-s img 217.0 > 156.9). Thesis flags
  HW "never sees two full diurnal cycles" (`:387-388`).
- ARIMA near-tie confirmed from `results_dynamo/comparison_table.csv`: 1-min ARIMA 0.5213 vs
  fm_best (Toto) 0.5153 (h=1); 15-s ARIMA 0.6675 vs 0.6374; Kalman 0.8111, Prophet 0.7328, naive
  0.7638 — every number in `predictors.tex:189-193` is exact. Foundation h1 0.515 confirmed
  (`metrics_h1.parquet` Toto uni 0.5153).
- Baselines are fixed-parameter + context-capped: thesis states this explicitly (`:76-79,384-390`)
  and admits "a full-history seasonal baseline and per-series tuning would narrow the margins".
- Bold "best" wins ≤0.1 WAPE without significance test: thesis admits it (`:173-175`, "below
  plausible sampling variability, with no significance test attached … an honest reading is a
  three-way tie").
If PARTIAL: every factual sub-claim of R5 is TRUE, but the thesis already contains nearly all the
qualifications Grok demands. The residual is that the abstract (`:49-50`) still leads "beat
classical baselines on every signal" without the soft-suite caveat, and ARIMA is not on the main
accuracy grid (present only in the reactive baseline). A presentation fix, not a science defect.
Dup-hint: soft baselines carry abstract; ARIMA near-tie.

---

### R6 / C6 — (a) EDA window post-selection; (b) 151-duplicate REPORT↔thesis mismatch
Target: `trace-eda.tex:26-29,269-271`; `analysis/trace_eda/REPORT.md:24`; `workload/trace_to_two_pool.py`
Verdict: CONFIRMED (both sub-findings)
Severity: minor (hygiene) / moderate (disclosure)
Evidence:
- (b) DUPLICATES — direct contradiction confirmed and RESOLVED in the thesis's favor:
  `trace-eda.tex:26-28` = 151 duplicate rows are "**retained** … analyses process ties in file
  order." `REPORT.md:24` = 151 duplicate rows "**dropped by the converter**." I checked the actual
  converter `workload/trace_to_two_pool.py`: it has NO dedup/drop code (grep for
  duplicat/drop_dup/dedup = nothing); `analysis/trace_eda/a_quality.py:26` only *counts* them
  (`n - len(df.drop_duplicates())`), does not drop. So the converter RETAINS → thesis is correct,
  **REPORT.md is stale/wrong**. `a_quality_stats.json` confirms duplicate_full_rows=151, rows=1e6,
  text_only 50.0%, largest_gap 0.6488 min (≈39 s). Repo-hygiene fix: update REPORT.md.
- (a) WINDOW SELECTION — b1–b6 are the six largest bursts chosen with full-week knowledge:
  `trace-eda.tex:265-271` ("The image-rate signal exceeds its p99 … 18 burst episodes. The six
  largest, plus the calmest day, form the evaluation windows"). The selection basis (largest
  bursts) IS disclosed; forecast leakage is separately controlled by the 1.4-day context split
  (`closedloop.tex:46-61`). Grok's ask (state that windows are top-envelope post-selections and its
  non-circularity implication) is a transparency add; the underlying facts are disclosed.
Dup-hint: REPORT.md dropped-vs-retained; window post-selection.

---

### R9 — Baselines: oracle-vs-deployable static, ρ=15 derivation, 101-grid domain
Target: `baselines.tex:54-61,105-107,192`; `closedloop.tex:369-373`
Verdict: PARTIAL (findings valid; several already addressed)
Severity: moderate
Evidence:
- Oracle per-window C* vs deployable static: `tab:base-grid` gives per-window C* (2→16); the
  ratios use the single "**deployable static**" C=16 + TP2×2 (`:105-107`), which is named and
  distinguished from per-window optima. The distinction Grok wants IS made ("deployable static").
- 101-point grid: `baselines.tex:59` states "101 evaluated points, all archived" but does not list
  the C/TP/N ranges or the lex cost order in the text — Grok's "domain undocumented in text" is
  fair (the count is given, the domain is not).
- ρ=15 derivation: `closedloop.tex:369-371` explicitly says ρ "is a swept control knob (four
  settings), **not a first-principles derivation**". So the thesis does not claim ρ=15 is derived;
  it is swept {10,15,20,25} with all reported. Grok's "derive or justify ρ=15" is partly moot —
  the thesis frames it as an operating point, not a derivation.
Dup-hint: deployable-static denominator; ρ swept not derived.

---

### R10 — AIC: co-headline 1.4–1.6× e2e model-vs-silicon with ~3% attention
Target: `aiconfigurator.tex:242-248,266-307`; `intro.tex:241-247`
Verdict: CONFIRMED (numbers) — framing-balance ask is a judgment call
Severity: moderate
Evidence:
- `tab:aic-fn` verified internally consistent: measured/composed ratios 1.38,1.37,1.36,1.50,1.58,1.62
  across N=1..64; whole-tower anchor mean 1.47 (band 1.32–1.62). The ~3% attention agreement
  (`:417`, strictly 3.2%) is a *single-operator* claim; the e2e f(N) gap is 1.4–1.6×. These are
  different objects, as cross-check §5 notes.
- The chapter does surface the 1.4–1.6× prominently (`:253-322`, "Both discrepancies move in the
  conservative direction … realized encoder capacity is, if anything, lower than simulated") and
  the abstract calls the model "validated physically" while intro RQ3 (`:241-244`) gives the
  1.4–1.6× band. So both numbers are present; Grok's ask is to weight them equally at the headline
  (the summary leads with "≈3%"). Presentation preference; no number is wrong. The closedloop
  silicon-replay pointer Grok wants IS present: `closedloop.tex:408-418` replays the winning
  schedule under measured f(N) → p99 784 vs 588 ms, ratio preserved.
Dup-hint: 3% attention vs 1.4-1.6x e2e headline balance.

---

### R11 — Closed loop is feedforward; "physics floor 588" vs static 565
Target: `closedloop.tex:22-44,74-79`, `tab:cl-aggregate`
Verdict: PARTIAL / CONFIRMED (framing) + minor floor-rhetoric point
Severity: minor–moderate
Evidence:
- "Closed loop": the controller reads archived rolling-origin forecasts and issues schedules L
  early with hysteresis (`:26-44`) — it is forecast-scheduled/feedforward with no residual
  feedback. `closedloop.tex:365-366` admits "honest with respect to information, but offline."
  Grok's "rename to forecast-scheduled" is a framing point; the design is disclosed.
- Floor rhetoric: `tab:cl-aggregate` (verified against artifacts) shows static C=16 p99 = **565 ms**
  while the forecast p90 "zero-queueing service floor" = **588 ms** (=f(64) 316.4 + handoff 272 =
  588.4, arithmetic checks). Static 565 < 588 because 16 always-on workers form smaller batches
  than the full 64-image forward the 588 floor assumes. The table caption explains the 588 rows
  "coincide at the zero-queueing service floor"; the sub-floor static value is real, so calling
  588 "the floor" is regime-specific (peak full-batch) rhetoric, as cross-check §1 flags. Minor
  conceptual wording, not an error.
Dup-hint: feedforward not closed-loop; 588 floor vs 565 static.

---

### R12 — Validation: n=1 "run noise"; fpm_observation_mode conditionality
Target: `validation.tex:64-72,92,116-120`
Verdict: CONFIRMED
Severity: moderate
Evidence:
- Single live run + single offline twin per policy (artifacts: exactly one
  `live_runs/live_fc`, one `live_re`, one twin each). The prose uses "within run noise" as a verdict
  (`:92,143`) without defining live-path variance; closedloop's ≈4% offline p99 noise is not
  re-established live. Grok's "demote to single-trajectory descriptive" is fair.
- Systematic same-sign replica-second bias confirmed from artifacts: fc live 6063 vs twin 6400
  (−5.27%), re live 1799 vs twin 1948 (−7.65%) — both negative, consistent with the tick-stall /
  spawn-delay harness effects the chapter itself lists (`:121-130`), i.e. a bias not zero-mean
  noise.
- fpm_observation_mode: `validation.tex:110-120` states the fix "drains every published pass …
  with it, the live planner is ready at its first tick" — i.e. the PASS path is partly post-fix.
  The chapter does not report the default-mode (unfixed) outcome. Grok's ask to condition the
  table on the mode is valid.
Dup-hint: n=1 run-noise; fpm post-fix agreement.

---

### R13 — Trace-eda claim hygiene (persistence→forecastability, Hill, dual-view H, 1-s "erases")
Target: `trace-eda.tex:64-67,184-186,314-337,359-401`
Verdict: PARTIAL (mostly pre-addressed by the current tex)
Severity: minor
Evidence:
- Dual-view Hurst: `trace-eda.tex:184-186` and `tab:eda-persistence` caption already state "the
  Hurst column is *derived* from the spectral slope (H=(1+β)/2): one estimator viewed two ways,
  **not two corroborating measurements**." Grok's exact demotion is already in the text.
- Hill without GOF: `:64` already says "indicative values, **no formal goodness-of-fit claim**".
  Already hedged.
- Persistence⇒forecastability: `:334-337` (ACF fig caption) says the envelope "is forecastable …
  **though its per-bin accuracy is the lowest of the four signals**", and `:323-325` frames LRD as
  "a risk, not a theorem, which Chapter 4 tests empirically." The smuggling Grok alleges is
  hedged, and predictors chapter does the empirical test.
- 1-s "erases": `fig:eda-multires` caption `:401` says a coarse monitor "does not merely blur the
  vision surges, it **erases** them" — strong wording, but the table backs it (images retain 3.9%
  of the 1-s peak at 60 s). Provisioner-relevance caveat could be added; minor.
Dup-hint: Hurst dual-view already hedged; Hill no-GOF already stated.

---

### CROSS-CUT — Unit label GPU-time vs worker-time (cross-check §1; S11)
Target: `tese.tex:59,77`; `intro.tex:45,262,454`; `conclusion.tex:65,77`; `closedloop.tex:317,439`
Verdict: CONFIRMED (label drift, incl. intra-file)
Severity: nit
Evidence:
- Abstract `:59` "static encoder fleet's **GPU-time**"; resumo `:97` "tempo de **GPU**".
- Body primary source uses "**worker-time**": `closedloop.tex:317,439`, conclusion `:65`
  ("provisioned worker-time"), intro `:262,454`.
- BUT the same files also say GPU-time elsewhere: conclusion `:77` "best static encoder fleet's
  **GPU-time**"; intro `:45` "provisioned **GPU-time**". So the drift is even within intro and
  within conclusion. Numerically harmless (1 encoder worker = 1 RTX 5090 GPU;
  `baselines.tex:18-19` defines the encoder metric as "worker-seconds … never summed across
  classes") but the label is inconsistent. Pick one.
Dup-hint: GPU-time vs worker-time label.

---

### CROSS-CUT — R² 0.12 vs 0.123 rounding (cross-check §1; S11)
Target: `tese.tex:46,81`; `intro.tex:141`; `trace-eda.tex:241,257,482`; `conclusion.tex:15`
Verdict: CONFIRMED (harmless rounding inconsistency)
Severity: nit
Evidence: `d_signals_stats.json` constant_fraction_fit r2 = **0.12253911**. Rounds to 0.12 (2 sf,
used in abstract `:46`, fig caption `:257`, conclusion `:15`, resumo `:81`) or 0.123 (3 sf, used in
intro `:141`, trace-eda body `:241`, related `:179`, trace-eda summary `:482`). Same number, two
precisions. Pick one policy.
Dup-hint: 0.12 vs 0.123 sig figs.

---

### CROSS-CUT — Validation table `tab:val-anchor` numbers (cross-check §1)
Target: `validation.tex:64-72`
Verdict: CONFIRMED (every cell exact)
Severity: n/a (accuracy check — passes)
Evidence (recomputed from `simulation/results/live51/`):
- Forecast: live TTFT p99 695.16→695; ITL 11.47→11.5; twin TTFT 651.14→651; ITL 5.287→5.3;
  twin decode_worker_seconds 6399.81→6400; ΔTTFT +6.76%→"+6.8%"; Δrep −5.27%→"−5.3%". ✓
- Reactive: live TTFT 3531.45→3531; ITL 150.74→150.7; twin TTFT 3494.73→3495; ITL 160.26→160.3;
  twin rep-s 1947.67→1948; ΔTTFT +1.03%→"+1.0%"; Δrep −7.65%→"−7.6%". ✓
- Offline twins 651/3495 also match `closedloop.tex:206,214` burst3 numbers.
Dup-hint: live table exact; clean agreement.

---

### CROSS-CUT — Week-scale aggregate `tab:cl-aggregate` + frontier + the "993.8 ms TimesFM loose end"
Target: `closedloop.tex:296-348`
Verdict: CONFIRMED (table + frontier exact); the "993.8 ms TimesFM loose end" is NOT on the frontier
Severity: n/a (accuracy check — passes)
Evidence (recomputed from `simulation/results/aggregate44/` and `aggregate44_rho/`, static=7.739 Mws):
- `tab:cl-aggregate` reproduced exactly: static C16 565.2/7.74M/1.00×; static C2 2952.8/0.97M/0.125×;
  fc p90 L30 588.4/2.376M/0.307×; fc p90 L300 588.4/2.116M/0.273×; fc p50 L30 3047.4/0.963M/0.124×;
  react L30 588.4/2.611M/0.337×; react L300 904.7/1.672M/0.216×. All match to the digit.
- Frontier: ρ10 588.4/0.438×; ρ25 899.3/0.179× ("0.44× … down to 0.18× at ρ=25 (899 ms)" exact);
  only ρ∈{10,15} per-episode-clean (0.44–0.31×) matches. The "loose end of that frontier" the text
  names (`:338-344`) is the aggregate-only ρ=25 tail (Chronos), correctly caveated.
- TimesFM week cells: fc_p90_L30_timesfm 588.4/0.297×; fc_p90_L300_timesfm **664.5**/0.263×. So
  TimesFM range 0.26–0.30×, max p99 **664.5 ms** — exactly the chapter's "TimesFM at 0.26–0.30×
  … 300-second-lead admits mild queueing, p99 664 ms, still passing" (`:322-324`).
- The value **993.829 ms** appears ONLY in `results_44.jsonl` (the per-window 560-cell matrix), for
  two **p50** cells (burst1/chronos/L300 and burst4/timesfm/L15) — a policy that fails regardless
  and is not part of the week frontier. There is NO 993.8 ms p90 TimesFM point on the frontier; the
  frontier's TimesFM worst case is 664.5 ms and passes. So a "993.8 ms TimesFM frontier loose end"
  is unsubstantiated — DENIED as a frontier concern. (It does not appear anywhere in `grok/` either.)
Dup-hint: frontier internally consistent; 993.8 is p50 per-window, not frontier.

---

### CROSS-CUT — Jaccard 0.02 / 5 shared minutes
Target: `trace-eda.tex:414-419,483`; `tese.tex:47`
Verdict: CONFIRMED
Severity: n/a
Evidence: `q_multires_tails_stats.json` jaccard = **0.024752** → 0.02. Consistent with 5 shared /
(106+101−5)=202 = 0.02475. Text "only 5 are shared (Jaccard 0.02)" exact. Pearson img_vs_req 0.3546
(→0.36) and gen_vs_req 0.8121 (→0.81) confirm decode-carried/vision-decoupled directional claim.
Dup-hint: Jaccard 0.02 clean.

---

### S11 — Unify R² sig figs and unit labels
Verdict: CONFIRMED (see the two CROSS-CUT items above) — Severity: nit. Both are real, harmless,
one-line fixes.

### S1–S10, S12–S15 (non-blocking suggestions)
Verdict: NOT INDIVIDUALLY DISPROVABLE — these are enhancement suggestions (free-intercept R²,
second LRD estimator, window-sensitivity, CRPS/pinball, thrashing counts, composed e2e SLA,
fixed-headroom reactive ablation, HPA prose, TRT-LLM/NIXL fence, contributions restatement,
chunk-parallel sensitivity, SOL clamp, Limitations heading, multi-percentile live CDFs). Each is a
reasonable "could add," none identifies an error. Spot-checks: S12 (parallel vs sequential
encoder dispatch) — the sensitivity Grok wants already exists (`twopool.tex:142-151`, sequential
floor 2.9 s from 4–32 workers). S14 (Limitations heading) — valid; conclusion has only a paragraph,
not a `\section{Limitations}`. S5 (thrashing) — genuinely absent; the controller has 3-min
hysteresis but no scale-churn counts reported.
Dup-hint: suggestions are additive, non-blocking.

---

## SUMMARY

Counts (13 required R + 5 D + cross-cuts checked):
- CONFIRMED (fact holds): D1/R1 (already-fixed), D5/R7-count, R3, R4, R5, R6(a+b), R10, R12,
  unit-label drift, R²-rounding, validation table (exact), week aggregate + frontier (exact),
  Jaccard, S11, S14/S5 (as gaps). 
- PARTIAL (valid but over-stated / already pre-addressed / rhetorical): D2/R2, D3/R8, D4, R9,
  R11, R13.
- DENIED / unsubstantiated: the "993.8 ms TimesFM frontier loose end" — 993.8 ms is a p50
  per-window matrix cell, not on the week frontier; the frontier's TimesFM max is 664.5 ms and
  passes.
- ALREADY-FIXED in current tex: R1/D1 (the headline finding) — committed as `ba96acf` crediting
  "grok committee D1/R1".

No fabricated numbers found. Every quantitative claim I recomputed (validation table, week-scale
aggregate + ρ frontier, predictors Table 1, Dynamo predictor WAPEs, Jaccard, R², f(64)+handoff=588)
matched its artifact to the digit. Grok's value is claim-hygiene/scoping, exactly as its own
verdict states; it surfaced no data-integrity problem.

Top 5 CONFIRMED (by exam risk):
1. R1/D1 reactive ITL fails the 100 ms bound (150.7/160.3) — the "sub-bound for both" wording was
   false; ALREADY FIXED in current intro/conclusion (git ba96acf).
2. D5/R7 "five bodies" undercounts the six review sections (Simulators body omitted).
3. R6(b) REPORT.md says duplicates "dropped by converter"; thesis says "retained"; converter code
   has no dedup → thesis correct, REPORT.md stale. Real doc contradiction.
4. Unit-label drift GPU-time vs worker-time (even intra-intro and intra-conclusion) and R² 0.12 vs
   0.123 — harmless but real inconsistencies.
5. R12 validation n=1 with systematic same-sign replica-second bias (−5.3%/−7.6%) presented as
   "within run noise"; fpm_observation_mode makes the PASS path partly post-fix (default-mode
   outcome unreported).
