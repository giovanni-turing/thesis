# Thesis shortening and evidence-preservation audit

Date: 2026-07-20  
Authoritative source: the current `tex/*.tex` files and their current artifacts, not an older PDF or prior review  
Scope: analysis only; no thesis source was modified

## Executive decision

The thesis can be shortened substantially without weakening its scientific case. The main problem is not lack of focus inside individual experiments; it is repeated narration of the same thesis claim, result, and qualification across the Abstract, Introduction, Related Work, chapter openings, chapter summaries, the long closed-loop ledger, and the Conclusions.

The current PDF has 137 pages. Chapters 1--10 occupy about 96 numbered main-matter pages; `detex` gives roughly 28,000 main-chapter words (raw source-token counting is about 29,100). A defensible target is:

- **main narrative:** approximately 19,500--21,000 words and about 68--74 pages;
- **conservative complete document:** approximately 121--125 pages if every full ledger and diagnostic is moved intact to the appendix;
- **recommended complete document:** approximately 115--121 pages if redundant full ledgers are replaced by compact appendix tables while machine-readable artifacts remain canonical;
- **gross main-text reduction:** approximately 7,000--8,500 words and 22--28 pages;
- **net whole-thesis reduction:** approximately 4,000--5,200 words in the conservative move-everything case, or roughly 6,000--8,000 words in the compact-evidence case.

This target preserves evidence completeness under a strict rule: every important claim retains one canonical quantitative result, its causal comparator, its limiting qualification, and a reproducible artifact pointer. Evidence completeness does **not** require the same result to be explained in four chapters or every cell of a ledger to remain in the main narrative.

The highest-value action is to reduce Chapter 8 from 20 pages to roughly 10--12 pages, followed by reducing the 10-page Introduction to about 6 pages. The next strongest reductions are in Related Work, Trace EDA, the overlapping AIC validation narratives, and the Two-Pool limitations section.

## Corrections required before shortening

These issues were independently checked by the primary review and at least one second-pass reviewer. They should be normalized before prose is compressed; otherwise local qualifications will be lost and the shortened headline will become broader than the evidence.

### 1. Direct contradiction: burst2 and burst6 have no forecast evaluation

`tex/closedloop.tex:43-50` says burst2/6 are in the 1.4-day context-only prefix and are “graded only by forecast-free policies.” `tex/closedloop.tex:874-877` says they are never graded by a forecast policy. However, `tex/closedloop.tex:542-547` says the reactive controller fails them “while the forecast arms hold 588 ms,” citing a baseline table that contains only reactive results.

Adjudication: delete the forecast-arm clause. The shortest complete statement is:

> At \(L=300\) s, reactive control also fails burst2 and burst6; no archived rolling-origin forecast covers those episodes.

Related “every window” claims in `tex/intro.tex:396-403` and `tex/conclusion.tex:48-52` must become “every forecast-covered/in-span window.”

### 2. “Every burst episode” actually means four forecast-covered bursts

`tex/closedloop.tex:294-298` says “every burst episode” and then reports four. The trace contains 18 detected episodes, six selected major bursts, and four forecast-covered bursts (`tex/trace-eda.tex:232-245`, `tex/closedloop.tex:43-50`).

Canonical wording:

> Across the four forecast-covered burst episodes, the p90 language policy passes and the reactive planner fails under the tested end-to-end replays.

### 3. “Most forecastable” conflates persistence with absolute accuracy

`tex/related.tex:284-286` and `:303` call the image signal the “most forecastable.” Yet `tex/trace-eda.tex:290-292` says its per-bin accuracy is the lowest of the four signals, and `tex/predictors.tex:113-122` confirms the image series has the largest WAPE. What is supported is that image demand is the most persistent and loses little accuracy across the required horizon (`tex/predictors.tex:178-183`), not that it has the lowest point error.

Canonical wording:

> Image demand is the most persistent and retains usable predictive structure across provisioning horizons, despite being the hardest signal to predict per bin.

This preserves the important inversion without contradicting the accuracy table.

### 4. The validation chapter has two SLA metrics, not three

`tex/validation.tex:154` says live and offline SLA verdicts are identical on “all three metrics.” Table `tab:val-anchor` contains two SLA metrics, TTFT and ITL, plus replica-seconds, which is an accounting/control-path metric (`tex/validation.tex:52-77`).

Canonical wording:

> Live and offline runs put TTFT and ITL on the same sides of their SLA bounds; TTFT and provisioned replica-time agree within single-digit percent, while forecast ITL differs by 1.8 ms.

The budget statement also needs clarification: the table says “budget-matched at 4 TP2 replicas” (`tex/validation.tex:54-59`), while `tex/validation.tex:133-140` describes `max_gpu_budget=8` as clamping to eight replicas. The shortened text must state the **applied replica cap in each path** and distinguish GPU-budget units from replica units.

### 5. The TP1×4 generalization exceeds the displayed table

`tex/baselines.tex:103-110` says TP1×4 fails every burst and TP2×2 passes every burst, with a 1.55--1.74× tail reduction. Table `tab:base-tp` displays burst1--5 only (`tex/baselines.tex:125-145`). Artifact evidence supports the same verdict for burst6, but adding it changes the upper reduction to about 1.81×.

Adjudication: for the shortest thesis, say “all five tabulated burst windows” and keep 1.55--1.74×. The alternative is to add burst6 and update the range to 1.55--1.81×.

### 6. The 0.96× language result needs model and denominator scope

The Abstract and Conclusion present 0.96× as a general language-fleet result (`tex/tese.tex:66-67`, `tex/conclusion.tex:68-69`). The body shows that it is the **Chronos p90** schedule: 518.6 H100 GPU-hours versus a TP2×2 static fleet time-scaled to the same 5.60-day span, 537.4 GPU-hours (`tex/closedloop.tex:300-316`). Toto and TimesFM preserve the 651 ms pass verdict but cost 625 and 641 GPU-hours. Request-count scaling changes the reference to 503.7 GPU-hours and the ratio to 1.03× (`tex/closedloop.tex:773-781`).

Canonical wording:

> On the 5.60-day span, the Chronos-p90 language schedule passes near break-even: 0.96× a time-matched static TP2×2 reference; alternate foundation models preserve the SLA verdict at higher cost.

In a compact limitation or cost sentence, retain that request-matched normalization gives 1.03×. This is why the correct interpretation is “near break-even,” not “language-pool saving.”

### 7. The 0.62× headline needs span, unit, and denominator every time it is promoted

The canonical experiment covers 5.60 forecast-covered days, 749,601 requests, and four in-span burst episodes (`tex/closedloop.tex:352-359`). It provisions 2.41 M encoder worker-seconds versus 3.87 M for the same-span static \(C=8\) fleet (`tex/closedloop.tex:363-384`). It is a week-scale saving, not a burst-window saving (`tex/closedloop.tex:750-765`), and the full seven-day trace has no forecast comparator (`tex/closedloop.tex:766-772`). “GPU-time” is derived under one encoder worker per RTX 5090; it is not measured energy and is never summed with H100 hours (`tex/closedloop.tex:784-792`).

Canonical wording:

> Over the 5.60-day forecast-covered span, Chronos-p90 provisions 2.41 M RTX-5090 worker-seconds—0.62× the same-span deployable static \(C=8\) fleet’s 3.87 Mworker-s—while passing the aggregate and every in-span episode.

The detailed result should retain issue-time actuation, warm readiness, and the 0.59--0.62× strict-re-warm range (`tex/closedloop.tex:395-410`).

### 8. Physical validation is forward-compute validation, not a live encoder service

The Abstract says the encoder cost was “physically validated” (`tex/tese.tex:55-57`). The exact boundary is an eager vLLM standalone vision-tower forward on synthetic GPU-resident inputs with randomly initialized weights; it excludes preprocessing, host-to-device transfer, scheduling, prefill, and a live serving worker (`tex/apendice.tex:170-186`). The week result is a replay repriced with measured \(f(N)\), not a week executed on silicon.

Canonical wording:

> The encoder cost model is matched against standalone vLLM vision-tower forwards on RTX 5090 silicon; the week economics remain simulated, and a full live encoder-worker validation remains future work.

Keep the separate live boundary: the Dynamo anchor exercises the real control plane with mocked engines, one burst, two policies, and one live run per policy (`tex/validation.tex:27-47`, `:79-101`, `:143-161`).

### 9. The Conclusion’s “none reverses direction” is too broad

`tex/conclusion.tex:91-94` says none of the limitations reverses the direction of the results. But the language cost ratio changes from 0.96× to 1.03× under request-count normalization, and daily encoder folds range 0.47--1.10× with one 1,262 ms SLA miss (`tex/closedloop.tex:773-781`, `:898-921`).

Canonical wording:

> These limitations do not invalidate the stated 5.60-day aggregate, but fold-level feasibility and cost direction vary; no directional generalization is claimed beyond the tested span, model, and denominator.

### 10. Simulation output should not be called “measured behavior”

`tex/twopool.tex:437-440` says the simulator reproduces the motivating claim “as measured behavior.” The result is simulated behavior under calibrated timing. The encoder timing has a physical forward-compute anchor; the H100 timing is AIC-calibrated and not independently measured on H100 (`tex/twopool.tex:365-377`).

Use “in simulation under calibrated timing.”

### 11. The manifest omits the canonical language-week experiment

The 0.96× result is ledgered and stored under `simulation/results/llm_week/` (`progress/results-ledger.md:284-289`, `:368-374`), but `tex/apendice.tex:209-338` does not explicitly map the `llm_week` experiment. Add one compact manifest row in a future edit. This is a small addition that makes a shorter body better evidenced.

## Evidence spine that must survive

The following is the minimum complete proof chain. Secondary metrics can move, but none of these links should disappear.

| RQ | Claim to retain | Canonical evidence to retain | Qualification that must remain |
|---|---|---|---|
| RQ1: signal sufficiency | Request rate poorly carries vision demand; per-pool saturation differs | \(R^2=0.123\) vs 0.654 (`trace-eda.tex:209-219`); CV²/persistence table (`:164-204`); extreme Jaccard 0.02 (`:340-353`); saturation table `tab:sim-knees` (`twopool.tex:232-266`) | One seven-day trace; generated tokens are arrival-stamped offered work; steady-knee topology and SLA are specific |
| RQ2: forecastability | Zero-shot TSFMs retain a modest uniform edge and usable lead; p90 supplies calibrated headroom | Rolling-origin/common-span protocol (`predictors.tex:31-58`); Table `tab:pred-wape` (`:103-125`); horizon result (`:178-183`); p90 coverage 0.88--0.90 at one-minute cadence (`:258-270`) | Fixed-parameter classical baselines; one-minute common span is only 33.4 hours and burst-heavy; image has the worst absolute per-bin error; lower band edge is not calibrated |
| RQ3: platform validity | Encoder timing is silicon-anchored, timing-model sensitivity is quantified, and live control decisions reproduce offline verdicts | Matched vLLM \(N\le64\) bound (`aiconfigurator.tex:226-239`, `apendice.tex:141-189`); Table `tab:sim-poly-aic`; Table `tab:val-anchor` | Standalone forward only; H100 timing not independently measured; real control plane uses mocked engines; one live run per policy |
| RQ4: baseline fairness | Static and reactive comparators are strong and share mechanics | Static table `tab:base-grid`; reactive language result (`baselines.tex:150-171`); reactive encoder table `tab:base-react-enc` | Costs are pool-specific and never summed; order-time and readiness-time billing differ |
| RQ4: encoder mechanism | P90 passes the 60-cell issue-time factorial; p50 and same-signal reactive fail where the claim depends on anticipation/headroom | `closedloop.tex:68-165`; compact EWMA/reactive-headroom synthesis; Table `tab:cl-aggregate` | Five forecast-covered windows; issued leads 15--165 s; p90 standing headroom, not clean detection; warm vs strict re-warm |
| RQ4: language mechanism | The same held signal passes only with a tail-aware belief-to-knee conversion | Table `tab:cl-triad` and `closedloop.tex:225-278` | Held cursor, not a second anticipation experiment; 0.96× is Chronos/time-matched and near break-even |
| RQ4: economics and end-to-end result | Encoder 0.62× over 5.60 days; forecast buys encoder savings and language compliance | Table `tab:cl-aggregate`; compact request-linked aggregate/burst3 end-to-end comparison from `closedloop.tex:661-729`; cost-denominator synthesis from `:731-805` | Per-burst autoscaling costs more than static; aggregate masking requires episode grading; compose by request identity before p99; daily-fold adverse result stays visible |

Two compact main-text tables should be created during a future edit because the current manuscript relies on prose for results that are too important to leave assertion-only:

1. an **encoder factorial summary** for `tex/closedloop.tex:68-133`, reporting p90/p50 pass counts by readiness model and the clean \(\rho\) range instead of reproducing 60 cells;
2. a **language-week summary** for `tex/closedloop.tex:300-316`, reporting Chronos/Toto/TimesFM p90, p50, reactive, and the time-matched static reference. This table should be mapped to `simulation/results/llm_week/` in the appendix manifest.

These additions can replace more prose than they add and make the shortened RQ4 chain stronger.

## Recommended shorter structure

### Front matter

- Abstract: 180--210 words.
- Resumo: a semantic mirror of the Abstract, not a longer second version.
- Remove the draft-status note (`tex/tese.tex:124-139`) from the defense/submission build; the source already labels it for removal.
- Keep institutional contents and lists until the required template is known.
- Remove abbreviations that are unused after editing; currently HPA and LRD appear only in the list, while OSL remains used.

### Introduction: target 6 pages instead of 10

The Introduction should contain exactly six elements:

1. one paragraph defining modality-disaggregated pools and the provisioning problem;
2. one compact thesis statement;
3. one paragraph with the three decisive trace facts;
4. four research **questions**, without their answers;
5. the architecture figure plus one methodology paragraph;
6. five concise contributions and one limitations table.

Delete the chapter-by-chapter roadmap or reduce it to one sentence. The table of contents already performs that function.

### Related Work: target 5 pages instead of 8

Organize by the question “which signal is watched, and how is it converted into capacity?” Replace paper catalogs with taxonomies and retain the positioning table. The table plus three narrow “to our knowledge” claims can replace most of the repeated thesis inversion in `tex/related.tex:279-327`.

### Trace EDA: target 7--8 pages instead of 12

Keep the trace definition, square-grid/nonconstant-token facts, the persistence table, the seven-day signal figure, the decoupling figure, onset statistic, resolution result, extreme Jaccard, and limitations. Move or remove exploratory clustering and redundant figures whose exact statistics remain inline and artifact-backed.

### Predictors: target 7 pages instead of 10

Keep the causal rolling-origin protocol, common-span bias, WAPE table, horizon result, p90 calibration, operational forecast figure, and limitations. Move model registry details, negative structural decomposition, and full covariate table to supplementary evidence. Keep the exact \(\pm0.4\%\) covariate bound in the body.

### AIC and Two-Pool chapters: target 14--15 pages combined instead of 22

Keep them as separate chapters if the committee values a clear calibration/platform boundary, but remove their duplicated architecture transition. AIC should present one measured/interpolated/modeled table and one unified matched-engine validation section. Two-Pool should retain the calibrated-vs-polynomial table, saturation-knee table, and queue-mechanism figure, with a compact limitations matrix.

### Baselines: target 4--5 pages instead of 6

Keep the static grid, reactive language result, and reactive encoder table. Move the full iso-cost TP table if its conclusion is retained exactly in prose.

### Closed Loop: target 10--12 pages instead of 20

Retain the controller, temporal split, decisive encoder ablations, held-cursor language conversion, aggregate table, a compact joint result, cost denominators, and limitations. Move the full encoder/language/joint ledgers to the appendix, but leave their adverse and interpretive findings in the main narrative.

### Validation: target 2--3 pages instead of 4

Keep the anchor table and exact scope. Move live-stack engineering diagnostics to a supplementary subsection, retaining one body sentence that names the four discovered divergences.

### Conclusion: target 2--3 pages instead of 4

Answer each RQ once, delete “The thesis statement, revisited,” state the bounded limitations precisely, and present three short future-work items.

## Chapter-by-chapter action plan

### `tex/tese.tex`: Abstract, Resumo, and draft note

- **Rewrite `44-70` and `80-116`:** keep trace scope, decoupling/burst/persistence, zero-shot result, separate encoder/language mechanisms, 0.62×/near-break-even outcomes, and validation boundaries. Remove draft-PR workflow detail and the full saturation diagnosis.
- **Delete `124-139` in the submission version:** it is project status, not thesis evidence.
- **Do not delete `141-149` without checking institutional rules.**

Expected reduction: 250--350 words plus any front-matter pagination benefit.

### `tex/intro.tex`

- **Merge `10-25` with `48-77`:** define prefill/decode/vision once. Keep TTFT/ITL/SLA terminology once and move the systems catalog to Related Work.
- **Keep `27-43` as the single thesis preview; delete the separate block quotation `166-181`.**
- **Compress `79-98`:** retain the two reactive assumptions and cold-start problem; move the long pool-specific lead footnote to the closed-loop protocol.
- **Reduce `103-161` to trace identity, signal mapping, three decisive statistics, six-minute onset, and the forecasting inversion.** The complete evidence stays in Trace EDA.
- **Rewrite `183-223` as four questions only.** Current entries answer themselves and duplicate Contributions/Conclusions.
- **Keep `231-239`, compress `241-258`, and let Figure `fig:intro-arch` replace surrounding architecture prose.** Shorten its caption.
- **Compress `329-410` from about 680 words to 350--400.** Keep novelty, design, and one quantitative outcome per contribution; delete secondary side findings.
- **Convert `415-458` into a compact limitations table.** Preserve every boundary: one trace, arrival-stamped decode, uniform image size, standalone forward validation, handoff/fabric, open loop, model/TP scope, and mocked-engine replay.
- **Delete or reduce `460-474` to one sentence.**

Expected reduction: 1,300--1,500 words.

### `tex/related.tex`

- **Compress `22-78`:** group engine and multimodal systems by function; retain closest systems and representative citations rather than one sentence per system.
- **Compress `95-172`:** preserve default reactive infrastructure, InferLine/Autopilot, SageServe/WarmServe/Dynamo, HeteroScale/TokenScale, and the two actual gaps. Avoid “all” and “none” where custom signals or proactive heuristics exist.
- **Compress `177-205`:** one paragraph for traffic precedents, one for why the Azure multimodal trace changes the question.
- **Compress `210-250`:** retain the evaluated TSFM families and relevant cloud/observability precedents; group unevaluated model catalogs in one cited clause.
- **Trim `255-274`:** retain the simulator/AIC gap, not every simulator mechanism.
- **From `279-327`, delete the repeated inversion and retain only the three narrow precedence claims plus the real-cluster caveat.** Keep “to our knowledge.”
- **Keep `329-359` and shorten its caption; let the positioning table replace prose.**

Expected reduction: 900--1,050 words.

### `tex/trace-eda.tex`

- **Compress `8-41`:** keep dates, row count, fields, 50/50 construction, square grids, and nonconstant embedded vision tokens. Move duplicate-row/tie handling to the appendix.
- **Move or remove Figure `fig:eda-ctx-vs-img` (`43-54`) if the exact token relation remains in prose.**
- **Move exploratory clustering `72-113` to supplementary material.** In the main text retain only the frames-class dominance needed later.
- **Retain the measured Fano range in `118-127`; move Figure `fig:eda-arrival` if necessary.** Bound claims to the tested one-second--one-hour range.
- **Keep `fig:eda-sevenday`; move `fig:eda-windows` to Baselines/Closed Loop or the appendix.**
- **Keep the persistence table `180-204`, but halve the interpretation `164-178`.** Retain that Hurst is derived from spectral slope and that half-life/Hurst orderings differ.
- **Keep the decoupling result `209-230`; compress burst anatomy `232-258`.** Say frames-dominated episodes plus one outlier, not “one burst type.”
- **Merge `273-308` into the temporal section.** Keep the 69-vs-9-minute contrast and the limitation that only specified linear/rank relations were tested; move the ACF figure and negative-test details.
- **Keep the 3.9%-vs-37% resolution result and Jaccard 0.02; move detailed tail marginals and the multiresolution figure if needed.**
- **Delete the empty redirect section `355-362`.**
- **Keep and tighten limitations `366-387`; delete the repetitive summary `389-403`.**

Expected reduction: 800--1,000 words and several redundant figure pages.

### `tex/predictors.tex`

- **Compress `10-26` and merge protocol paragraphs `31-93`.** Retain causality, \(H=12\), common-span bias, univariate/covariate distinction, WAPE/MAE, and model cost. Move fixed baseline hyperparameters and context caps to the manifest.
- **Keep Table `tab:pred-wape`.** Merge `140-192` into two paragraphs and state the horizon result either in the figure caption or body, not both.
- **Move the Dynamo registry comparison `164-176` and structural additive negative result `208-221` to supplementary evidence, retaining one exact sentence for each.**
- **Move Table `tab:pred-cov` if the body keeps the exact \(\pm0.4\%\) conclusion.**
- **Reduce `242-256` to the median-point conclusion; keep p90 calibration `258-270`.**
- **State each forecast-band observation once across `275-312` and its caption.**
- **Keep all limitation categories `317-342`, compacted; replace summary `344-365` with three sentences.**

Expected reduction: 700--900 words.

### `tex/aiconfigurator.tex`

- **Compress `6-38`:** retain the missing consumer-GPU data, unusable fallback, and 5.9× SOL error; move exception names and the sibling-device probe to an artifact note.
- **Move most target-system detail `45-56`; compress collection details `63-90`.** Retain production-kernel selection, pinned vLLM, locked clocks, and the 17% clock effect.
- **Present raw and post-infill states `94-118` in one compact paragraph/table.** Preserve the labels: 7,679/34,326 is pre-infill and 7,760/34,710 is post-infill; otherwise the current numbers look contradictory.
- **Replace `125-165` with a three-row measured/interpolated/modeled table plus omitted-effects paragraph.**
- **Merge `167-253` and `255-329` into one matched-engine validation section.** Make the vLLM \(N\le64\), 12.8% result primary; keep HuggingFace 1.4--1.6× only as execution-stack attribution.
- **Move detailed HuggingFace figure/table and term-level profile to the existing engine-sensitivity appendix.** Keep a compact representative comparison and the Student-t protocol.
- **Delete the duplicate two-pool smoke architecture `331-346`; centralize the 3.1% H100 extrapolation caveat in Two-Pool limitations.**
- **Replace `358-375` with three sentences.**

Expected reduction: 850--1,050 words.

### `tex/twopool.tex`

- **Reduce `10-30` to setup plus three findings; compress architecture `35-52`.**
- **Move the callback timing leak `65-69` and detailed 235B family transfer `71-83` to supplementary material.**
- **Keep Table `tab:sim-poly-aic`.**
- **Compress batching/handoff `111-175`.** Retain \(f(1)\), \(f(64)\), measured saturation near \(N=6\)--8, 64-image cap, chunk-parallel assumption, 1.6/6.4 MB payloads, and “bandwidth lower bound, not tail estimate.”
- **Halve protocol `182-230`; keep SLA populations, isolated pools, topology, and selected windows.**
- **Keep Table `tab:sim-knees` and Figure `fig:sim-burst-queue`; remove repeated verdicts from captions/body.**
- **Merge `288-338` into two result paragraphs: steady knee separation, then burst mechanisms.**
- **Replace limitations `351-433` with a five-part matrix:** SLA/topology; encoder-vs-H100 timing fidelity; token convention; uniform image size/handoff; isolated open-loop simulation and omitted ingress. Move detailed resolution/cap sensitivities to supplementary material.
- **Replace summary `435-450` with two sentences and use “in simulation under calibrated timing.”**

Expected reduction: 1,000--1,200 words.

### `tex/baselines.tex`

- **Merge accounting `21-37` into one compact paragraph.** Preserve order-time versus readiness-time billing and no cross-hardware summation.
- **Halve protocol `42-62`.** Keep window identities, context-only burst2/6, lead ranges, and hysteresis.
- **Integrate `95-123` into the static-table interpretation.** Preserve stage-conditional qualification, deployable \(C=8\), TP2 necessity, and 4×/2× calm overprovisioning.
- **Move Table `tab:base-tp` if the body retains one exact iso-cost sentence, narrowed to the five displayed windows.**
- **Compress reactive language `150-171` to the 14/14 mean-law pass but tail-SLA fail, plus the 10% spend/no-tail-gain ablation.**
- **Compress `207-218`; replace summary `220-241` with a two-sentence transition.**

Expected reduction: 350--500 words.

### `tex/closedloop.tex`

This is the central chapter; shorten by canonicalization, not by removing adverse results.

- **Reduce `11-20` to two sentences.**
- **Compress, do not delete, controller/split/factorial `25-133`.** The issue-time causal design, five-window scope, 15--165 s bound, p50 failure, p90 60/60, readiness models, model tie, and \(\rho\) frontier are indispensable but repeatedly stated.
- **Keep the mechanism `135-165` in about half its length.** Preserve graduated standing headroom, burst3 not being cleanly anticipated, and reactive-with-headroom failure.
- **Move full EWMA Table `cl-ewma` (`167-220`) but retain exact body evidence:** cheap calibrations fail burst3/burst5; the all-pass EWMA costs 1.09× static; foundation p90 passes at 0.62×.
- **Keep Table `cl-triad` and compress `225-278`.** Preserve held cursor, belief-to-tail-knee derivation, and mean-conversion failure.
- **Merge `280-329` into one burst paragraph and one week paragraph.** Say four forecast-covered bursts. Retain Chronos/time-matched scope for 0.96×.
- **Remove Figure `cl-framework-diff` (`331-350`):** all three panels duplicate evidence elsewhere.
- **Keep Table `cl-aggregate`; halve `395-443`.** Preserve issue time, readiness, model robustness, clean \(\rho\) band, and aggregate masking.
- **Move the full encoder and language ledgers `445-660` to the appendix, but retain a compact evidence synthesis:** four of five composed encoder windows tie at the service floor; the p99 advantage is burst3; readiness billing can reverse apparent cost; forecast buys language compliance, not thrift, and costs 2--6× more than the failing reactive policy; token-pooled ITL differs from validation TPOT.
- **Move the full joint ledger table `661-710`, but keep a compact aggregate/burst3 comparison and the method:** join on request identity, then take p99; do not sum marginal p99s. Retain forecast ≈1,240 ms, reactive 1,696 ms aggregate and 21,868 ms burst3.
- **Keep denominator analysis `731-792` in a compact body subsection.** It must say 0.62× is 5.60-day vs static \(C=8\), per-burst autoscaling is more expensive than static, full-trace reactive has no forecast comparator, 0.96× becomes 1.03× under request scaling, and pool costs are never summed.
- **Reduce controller-cost `794-805` to one sentence; move run-volume `807-835` to provenance.**
- **Compress limitations `836-921`, retaining every category and the adverse daily-fold range/failure.**
- **Replace summary `923-945` with at most three sentences.**

Expected main-text reduction: 3,000--3,400 words. Expected net document reduction after appendix moves: approximately 1,800--2,300 words plus several pages of duplicated tables/figure prose.

### `tex/validation.tex`

- **Halve setup `11-47`, preserving stack, hardest window, two policies, mocked timing, delayed spawn, and offline twins.**
- **Keep Table `tab:val-anchor`; reduce `79-101` to one result paragraph.** Retain single-live-run scope.
- **Move byte-identical tick/capacity detail and diagnostic list `103-141` to supplementary material.** Keep one body sentence naming startup semantics, calm-load sampling, cadence stall, and cap-unit divergence.
- **Tighten `143-161` with the corrected two-SLA-metric wording and explicit applied cap.**

Expected main-text reduction: 350--450 words.

### `tex/conclusion.tex`

- **Compress RQ1/RQ2 `15-31` by one-third.**
- **Keep RQ3 `33-46` but say standalone vision-tower forward and real control plane with mocked engines.**
- **Keep RQ4 `48-71` with forecast-covered scope and exact 0.62×/0.96× qualifications.**
- **Delete `73-80`, “The thesis statement, revisited.”** It immediately repeats the RQ answers.
- **Rewrite `82-94` using the bounded statement above; remove “none reverses direction.”**
- **Delete the completed negative experiment in Future Work `106-110`; it belongs only in Predictors. Present the remaining three extensions as compact bullets.**

Expected reduction: 200--300 words.

### `tex/apendice.tex`

- **Keep the manifest `209-338`: it is the evidence-completeness mechanism. Add an explicit `llm_week` row.**
- **Compress environment prose `48-62`, long interpretive captions `70-89`, engine introduction `97-110`, and repeated engine interpretation `154-168`.**
- **Keep physical scope/repricing `170-189` nearly intact.**
- **Compress upstream-contribution detail `191-207`; delete the workspace-layout paragraph `340-348`.**
- **Absorb the full closed-loop ledgers, EWMA details, and live engineering diagnostics only if they remain useful to examiners.** If they merely duplicate archived machine-readable artifacts, retain compact tables rather than all prose.

Expected direct reduction before moved material: 200--300 words.

## Canonical claim wording for reuse

The following wording should be reused, with shorter variants in the Abstract, instead of independently paraphrasing the same claim in every chapter.

### Trace and forecasting

> In one seven-day Azure multimodal trace, image demand is poorly carried by request rate (\(R^2=0.123\)), markedly burstier (CV² 3.83 vs 0.32), and nearly disjoint at the extremes (Jaccard 0.02). It is also the most persistent signal and retains usable predictive structure across provisioning horizons, despite having the largest per-bin error.

### Platform boundary

> Encoder cost is anchored by standalone vLLM vision-tower forwards on RTX 5090; language timing is AIC-calibrated H100 simulation; the live anchor validates Dynamo’s real control plane with mocked engines, not GPU execution.

### Encoder result

> Across five forecast-covered windows and issued leads of 15--165 s, Chronos-p90 at \(\rho=15\) meets the encoder SLA under warm and strict-re-warm models, including burst3 where same-signal reactive control fails at every lead. Over the 5.60-day covered span it provisions 0.62× the same-span static \(C=8\) worker-time; this is a week-scale, not per-burst, saving.

### Language result

> The language experiment tests tail-aware conversion of a held forecast cursor, not a second anticipation loop. Mean conversion fails; the belief-to-tail-knee conversion passes all four forecast-covered bursts. Chronos costs 0.96× a time-matched static TP2×2 fleet over 5.60 days, but 1.03× under request-matched normalization; alternate TSFMs preserve the pass verdict at higher cost.

### Validation boundary

> On burst3, one live run per policy through Dynamo’s real control plane with mocked engines reproduces the offline pass/fail directions for TTFT and ITL; it validates the control path, not silicon or the encoder pool.

## Adjudication of proposed cuts

### Accepted

- Delete repeated thesis statements, mini-conclusions, and empty redirect sections.
- Replace paper catalogs with taxonomies while preserving closest-work citations and novelty hedges.
- Move exploratory EDA and secondary forecasting ablations to supplementary evidence.
- Merge the two overlapping AIC validation narratives and make matched vLLM evidence primary.
- Move detailed closed-loop ledgers and live engineering diagnostics while retaining their adverse conclusions in the main text.
- Delete Figure `cl-framework-diff`; its three panels repeat existing results.
- Retain one primary table/figure per claim and remove duplicated body/caption interpretation.

### Accepted with modification

- **Move the EWMA table:** only if the body retains the exact 1.09× all-pass EWMA and burst3/burst5 failure evidence.
- **Move the joint ledger:** only if the body retains request-identity composition and aggregate/burst3 end-to-end results.
- **Move the encoder/language ledgers:** only if the body retains the service-floor tie, burst3-only encoder p99 separation, language compliance-not-thrift result, billing distinction, and ITL/TPOT distinction.
- **Move limitations:** only detailed sensitivity cells may move. The main text must retain all limitation categories and adverse daily-fold evidence.
- **Remove figures:** only where the exact statistic, population, method, citation, and artifact remain.

### Rejected

- Removing the held-cursor qualification or describing the language result as anticipation.
- Calling 0.96× model-independent or an unqualified saving.
- Calling 0.62× energy savings, full-week-seven-day savings, or per-burst savings.
- Removing per-episode grading; the aggregate masks burst3.
- Removing warm versus strict re-warm accounting.
- Merging token-pooled ITL with per-request TPOT.
- Calling the live anchor a live GPU/encoder validation.
- Calling the matched-engine forward test full serving-path validation.
- Removing the 100 Gbps/embedding-only handoff requirement.
- Removing the adverse daily-fold result because it weakens the headline.
- Removing the common-span sampling bias, fixed-baseline qualification, or one-minute p90 calibration scope.
- Describing AIC’s exact graph-cost batching law as a physically exact serving law.
- Deleting primary result tables while keeping only rhetorical summaries.
- Removing the artifact manifest.
- Cutting institutional front-matter components before checking submission rules.

## Recommended editing order

1. **Correct the eleven scope/consistency issues above.** Establish canonical wording before deleting duplicates.
2. **Lock the evidence spine.** Mark the tables, figures, qualifiers, and artifact rows that cannot move or disappear.
3. **Shorten the Abstract and Resumo together.** Verify semantic parity sentence by sentence.
4. **Rewrite the Introduction around one thesis statement and question-only RQs.**
5. **Compress Related Work and Trace EDA.** Remove catalogs/exploratory material before touching core evidence.
6. **Merge overlapping methods/validation narration.** Preserve measured-versus-inferred boundaries.
7. **Rebuild Chapter 8 around the controller, causal ablations, one aggregate table, one compact joint result, denominators, and limitations.**
8. **Move supplementary ledgers/diagnostics and update the manifest, including `llm_week`.**
9. **Shorten Conclusions last.** It should synthesize the already-canonical claims, not introduce new wording.

## Verification checklist after a future shortening edit

- Abstract and Resumo contain the same claims, scope, denominators, and validation boundaries.
- Every “all/every” statement names its population: five forecast-covered windows, four in-span bursts, or five tabulated TP windows.
- 0.62× always carries 5.60-day span, static \(C=8\) denominator, provisioned worker-time, and issue-time/readiness scope where space permits.
- 0.96× always carries Chronos, time-matched TP2×2 denominator, and near-break-even interpretation; 1.03× request normalization remains visible.
- “Most persistent” is never rewritten as lowest-error or “most forecastable.”
- Encoder measurement, H100 simulation, and mocked-engine live control are never collapsed into “end-to-end physical validation.”
- P90 calibration is limited to one-minute cadence; the common-span bias and fixed-baseline qualification remain.
- Held cursor and tail-aware conversion remain wherever the language result is summarized.
- Aggregate and per-episode verdicts remain separate.
- End-to-end p99 is calculated after request-identity joining, never by summing marginal p99s.
- Warm/readiness and order-time billing remain distinguishable; RTX-5090 and H100 costs are never summed.
- Token-pooled ITL and per-request TPOT remain distinguishable.
- The 100 Gbps/embedding-only handoff requirement, open-loop demand, one-trace scope, and adverse daily-fold result remain.
- Every retained quantitative claim has a body table/figure or an explicit manifest artifact.
- The `llm_week` experiment is added to the manuscript manifest.
- LaTeX builds with zero undefined references; all moved figure/table labels and cross-references resolve.
- The final word/page reduction is measured on the built artifact, not estimated from source lines.

## Final assessment

The thesis is scientifically richer than its central argument requires. Its strongest version is shorter because the evidence is already unusually complete: the manuscript can let a few canonical tables, explicit limitations, and the reproduction manifest carry weight currently borne by repeated prose.

The appropriate goal is not to make the work look uniformly positive. The shorter thesis must preserve the difficult facts: image demand is the hardest per-bin series; the language 0.96× is denominator- and model-specific; encoder autoscaling costs more than static inside individual burst windows; one daily fold fails; the live anchor uses mocked engines; and burst2/6 lack forecast coverage. Preserving those facts while eliminating repetition will make the 0.62× result and the per-pool mechanism more credible, not less.
