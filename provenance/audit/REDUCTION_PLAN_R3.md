# Thesis Reduction Plan — Round 3 (analysis of the current text)

**Baseline analyzed:** working tree after commit `e9a515e` + the 14 deep-verify fixes.
137 pages, ~30,500 body words. Every chapter re-read in full for this plan
(2026-07-20); all line numbers refer to the current files.

**Goal:** shorter still, with the shining points *more* visible — zero loss of
evidence, findings, or honesty caveats. This plan lists **everything** judged
shortenable without leaving a gap, plus what must instead be highlighted.

**Honest headline before the detail:** rounds 1–2 already took the cheap 20%.
What remains is (a) ~2,000–2,300 words of residual redundancy that is genuinely
gap-free to remove (≈ 4–6 pages), and (b) three *structural* options worth ~2–4
more pages that each require a decision because they trade something. Beyond
that, further cuts would start deleting evidence.

---

## 0. The facts that must SHINE (not just survive)

These are the thesis. Every editing decision below serves making them easier to
find. Each has exactly one **owner** location where it is stated in full; every
other mention should be one clause.

| # | Fact | Owner (state in full, bold the verdict sentence) |
|---|------|--------------------------------------------------|
| S1 | Vision demand decouples from request rate: R²=0.12 vs 0.65, Jaccard 0.02 at the extremes, 16× peak-over-mean bursts invisible in the request signal | trace-eda §vision (l. 209–245) |
| S2 | The burstiest signal is the most persistent (H≈0.93, 69-min memory) → forecastable exactly at provisioning horizons; TSFMs win **20/20 cells zero-shot**, p90 edge calibrated 0.88–0.90 | trace-eda tab (l. 180–204) + predictors §point/§quantiles |
| S3 | Encoder cost model is **measured silicon** (RTX 5090, locked clocks, upstreamed PR #1312), attention within ≈3%, matches vLLM's own tower within **12.8%** across the serving regime | aiconfigurator §validation + apendice §engine-sensitivity |
| S4 | Saturation knees an order of magnitude apart; the largest burst breaks *both* pools differently — removable TP1 prefill floor vs **episodic encoder queueing at 29% utilization, invisible to every dashboard signal** | twopool §knees (l. 288–338) |
| S5 | Closed loop: p90 forecast holds the SLA **60/60 cells, lead-invariant 15–165 s**, beats the identically-informed reactive controller on the one-minute onset **at every lead**; mechanism = graduated standing headroom, not detection | closedloop §cl-matrix |
| S6 | The economics: **0.62× deployable static encoder worker-time at week scale** (0.59–0.62 across readiness models) — and, stated with equal prominence, *per burst window every autoscaling arm costs MORE than static*; language pool is compliance (2–6× dearer than reactive) at 0.96× break-even | closedloop §cl-aggregate + §cl-ledger-cost |
| S7 | The verdict pair reproduces on the **real Dynamo control plane** (mocked engines — validates the control loop, not silicon): PASS/FAIL identical, TTFT within 1.1–6.8% | validation tab:val-anchor |

**Highlighting moves (add ~0 words, big findability gain):**
- Each owner statement above already exists; make sure it is the *first or last
  sentence of its section* and bold — S1, S4, S5, S6 already are; S2's "20/20"
  verdict in predictors l. 140–141 is bold, good; S3's verdict sentence in
  aiconfigurator l. 307 ("The analytical model matched the empirical test") is
  bold, good.
- The five-number spine (0.12 / 20-of-20 / 12.8% / order-of-magnitude / 0.62×)
  appears once each in the abstract — after this round, verify it stays that way.

---

## 1. Global guardrails (unchanged from rounds 1–2 — never cut)

1. The 7 honesty caveats (offered-work decode stamp; RTX-5090-real vs
   H100-simulated vs mocked-engine-live; single 7-day trace / not fold-invariant;
   588 ms analytic single-stream floor; per-burst-costs-more; order-vs-readiness
   billing; 3-denominator cost accounting). De-dup only; a one-clause trace stays
   wherever a claim depends on one.
2. `tab:ap-manifest` + `tab:ap-env` (the offload target), all `\label`s that are
   referenced, all citations.
3. The closedloop ledger tables (`tab:cl-ledger-enc/llm/joint`,
   `tab:cl-aggregate`, `tab:cl-ewma`, `tab:cl-triad`) — adjudicated in round 2 as
   load-bearing per-metric evidence (tie-at-floor rows ARE finding S6's
   localization). Cutting them is a *decision item* (§4B), not a default.
4. The Resumo (USP-required). The rejected-fixes list (ADJUDICATION §0.4) — none
   of the values protected there may drift.
5. Before dropping any inline number: confirm it lives in the DB/appendix
   manifest, else add the pointer first.

---

## 2. Cross-chapter moves (do these once, they touch several files)

| ID | Move | Where | Est. saving |
|----|------|-------|-------------|
| G1 | **Chapter summaries re-enumerate their own numbers.** trace-eda §Summary (l. 389–403) restates R², CV², 6-min, H, Jaccard, 4%; predictors §Summary (l. 344–365) restates 2–9%, 8–32%, one-third, 0.88–0.90, 12-step; twopool §Summary and closedloop §Summary similar. Rule: a summary states finding-*shapes* + at most two numbers (the chapter's own headline). The reader who wants digits has just read them. | 4 files | ~200 w |
| G2 | **Figure captions that re-state adjacent body numbers.** `fig:eda-arrival` caption repeats Fano 1.8→938 (body l. 120–123); `fig:eda-decouple` caption repeats R²=0.12; `fig:eda-acf` caption repeats 0.64/69/9; `fig:cl-framework-diff` caption (~130 w) restates 3,495/2,164/651/1.1–6.8% all present in body text; `fig:app-engines` caption ~90 w. Rule: one anchor number per caption, mechanism in one clause; the caption points, the body states. | 5 captions | ~150 w |
| G3 | **Intro restates owned statistics in full.** Intro §gap quotes trace-eda's full battery (R², CV² pair, Jaccard, 370 img/s, 16×, Fano pair, Hurst pair, 5.0 s @ 29%). Keep R²=0.12, the 5.0 s@29% invisible-failure, and Hurst 0.93 (they carry the argument); compress the rest to shapes ("an order of magnitude burstier, extremes disjoint, overdispersed at every window"). | intro | ~90 w |
| G4 | **"Dashboard-masking" is explained ~5×** (intro-gap, baselines summary l. 236–239, cl-aggregate l. 434–443, cl-ledger-llm l. 643–648, EWMA para l. 174–177). Owner: cl-aggregate. Others → name + pointer ("the masking of §cl-aggregate"). | 3 files | ~70 w |

---

## 3. Per-chapter inventory

Format: **role → spotlight → cut list (all of it) → verdict**. Savings are
conservative estimates.

### 3.1 `closedloop.tex` — 7,337 w → target ~6,800 (−500)

Still 24% of the body. The tables are locked; all remaining fat is prose that
re-narrates them.

**Spotlight:** S5 + S6. The single most important sentence in the thesis is
l. 395–397 ("meets the tail SLA over the aggregate *and* inside every in-span
episode at 0.62×") — already bold. Second is the division-of-labour sentence
l. 658–659 ("encoder = savings; language = compliance") — already bold. Keep both
exactly where they are.

Cuts, in descending value:
1. **Mechanism paragraph alarm statistics** (l. 135–153): "crosses on 70–102
   bins per day … against ≤1 for point and p50" + "55 minutes to 4 hours late or
   never" are supporting detection stats; the load-bearing claim is
   *graduated-headroom-not-detection* + zero calm-day false alarms. Keep those
   two, move the counts to the manifest. (−60 w)
2. **EWMA paragraph re-narrates its table** (l. 167–189): the cell-by-cell
   verdict walk ("clear the burst-masked week aggregate but fail b3/b5 … the one
   calibration that clears every episode costs 1.09×, frontier
   1.32/1.09/0.94/0.83") duplicates `tab:cl-ewma` + its caption. Keep the bind
   statement ("coverage-vs-cost bind: cheap calibrations fail the fast onset;
   the one that passes over-provisions"), the 1.09× anchor, and the band-*shape*
   conclusion; drop the frontier enumeration (it also appears at l. 419–432).
   (−80 w)
3. **ρ-frontier stated 3×**: l. 148–150 (mechanism, "0.48–0.89×"), l. 419–432
   (aggregate, full frontier 0.89→0.40 + clean band), l. 149/427 overlap. Owner:
   §cl-aggregate paragraph. The mechanism-paragraph mention → "(the
   per-episode-clean band, §below)". (−40 w)
4. **Reactive-appears-to-pass paragraph** (l. 434–443) vs ledger-llm masking
   paragraph (l. 643–648): same point (aggregate masks burst3), both with the
   sub-half-percent explanation. Owner: l. 434–443 (it introduces the
   aggregate-and-per-episode grading rule). Ledger version → one clause +
   pointer. (−45 w)
5. **Ledger commentary re-quoting table cells** (l. 529–554): "the reactive p99
   of 16,079 is 15× over" (in table, bolded); burst2/6 4,282/4,606 re-quoted
   from `tab:base-react-enc` (l. 544–547) — keep the *existence* of the two
   extra separations, drop the re-quoted values ("adds two more separations at
   long lead, Table tab:base-react-enc"). (−50 w)
6. **Volume-of-evidence subsection** (l. 807–834, ~230 w): compress to ~120 w —
   one sentence for 2,060 runs / 44 checks / 20 arms / exact-path join; one for
   749,601×2 + 1M×2 replay scale + manifest pointer; keep the live-anchor
   sentence and the scale-is-not-independence caveat verbatim (honesty). (−110 w)
7. **p50-contrast mechanism told twice** (l. 319–329 week-scale + l. 94–100
   matrix item 1): both explain median-sizes-to-mean. Owner: matrix item. The
   week-scale paragraph keeps the numbers (828 ms / 319.9 GPU-h / 38%) and the
   burstiness-gap sentence, drops the re-explanation. (−40 w)
8. **Summary** (l. 923–945): currently restates lead range, both readiness
   models, mechanism, conversion, 0.62×. Chapter summary keeps 0.62× + the
   per-pool mechanism clauses; drops the readiness-model span (stated twice
   above) and the lead enumeration. (−45 w)
9. Assorted single-clause hedges: "stated once and completely" (l. 723), "the
   scope note said" (l. 834), "as the table's caption says" variants. (−30 w)

**Do NOT cut:** the scope/arm-definition paragraph (l. 454–469 — it is the
no-cherry-picking guarantee); the three-denominator bullets (l. 749–782); the
two honesty cost points (l. 784–792); the controller-cost paragraph (l. 794–805,
it pre-empts the obvious objection); anything in §Limitations (l. 836–921 — every
sentence there survived adjudication, including the just-restored
expanding-context definition).

### 3.2 `intro.tex` — 3,382 w → target ~2,900 (−480)

**Spotlight:** the thesis-statement quote (l. 168–181) and the RQ4 verdict. The
quote is the one block a committee member re-reads; it is good and must not be
touched.

Cuts:
1. **Contribution 5 is a 230-word results-preview** (l. 386–410): it pre-runs
   closedloop with 6–8 workers, ρ=15, 15–165 s, 588 ms, 734 ms, 0.62×, EWMA
   1.09×, belief-to-knee, zero false alarms. A contribution item needs the
   *claim* + one or two numbers: keep "holds every window at every lead at
   0.62× the deployable static fleet; the identically informed reactive
   controller loses the fastest onset at every lead; a calibrated-EWMA control
   shows the band shape, not accuracy, is load-bearing." Drop the rest (all
   stated in closedloop). (−120 w)
2. **RQ answers duplicate Contributions** (l. 185–223 vs 329–410): round 1
   reduced this but each RQ still carries its mechanism sentence. Keep RQ
   text = question + one-clause answer + chapter pointer; the mechanism lives in
   the contribution item (or vice versa — pick per RQ, currently both carry it
   for RQ1 and RQ4). (−130 w)
3. **§Scope duplicates the owning chapters' limitation sections** (l. 415–458):
   every item (decode stamp, 448² uniform, 12.8%, single-stream handoff,
   TP2 convention, zero-shot, live anchor) is stated in full in its owner
   chapter. Intro scope should be the *inventory*, one clause each + pointer;
   currently several items carry their full derivation ("the sign of the bias
   over the population the controller actually samples spans zero…" — that is
   trace-eda's sentence). (−150 w)
4. G3 (gap-section statistics battery → shapes). (−90 w)
5. The cold-start footnote (l. 86–92) survived round 1 in compressed form —
   fine — but the body sentence it hangs on already says "tens of seconds to
   minutes"; the footnote's last clause ("so the closed-loop evaluation sweeps
   per-pool lead ranges…") repeats §approach. Trim the clause. (−25 w)

**Do NOT cut:** the two-paragraph opening (l. 10–43) — it is the best-written
spread in the manuscript; the thesis quote; fig:intro-arch and its caption
(orients everything); the organization section (7 lines, cheap).

### 3.3 `twopool.tex` — 3,363 w → target ~3,080 (−280)

**Spotlight:** S4. The knee table + the invisible-failure sentence (l. 315–323)
are the mechanical heart of the thesis. Also the honest
convention-dependence paragraph (l. 379–393) — a committee will respect it;
leave intact.

Cuts:
1. **Engine-sensitivity restated** (l. 169–175, end of handoff paragraph): the
   1.4–1.6×-is-execution-stack + 12.8% pair is aiconfigurator's owned headline,
   already compressed there to one statement + appendix pointer. Here → one
   clause ("the cost model matches vLLM's own tower within 12.8%,
   App. engine-sensitivity"). (−50 w)
2. **Union-bound / ≈1.3 s reconstruction** (l. 199–211): closedloop's measured
   join (l. 719–721) now supersedes this estimate and says so. Keep two
   sentences (the ≈2 s budget statement + "a modelled reconstruction puts
   composed p99 at ≈1.3 s, confirmed by the measured join of
   Table cl-ledger-joint"); drop the correlated-tails mechanism sentence
   (restated at the join). (−70 w)
3. **Batching paragraph** (l. 111–144, ~250 w): keep the law, the chunk-parallel
   policy + its *simulator-assumption* honesty, and the sequential-alternative
   counterfactual number (2.9 s plateau). Trimmable: the "(1,64),(2,32),(64,1)"
   triple example → one pair; the "(a ~3.2 ms fixed per-forward overhead)"
   parenthetical (manifest); "Under low load the policy changes nothing …
   identical to three decimals" → half. (−60 w)
4. **Resolution-repricing wall** (l. 395–423): every scope limit stays (672²
   fabric-margin, 24-h both-fabrics miss, never-quote-without-window), but the
   paragraph re-derives the "why" twice ("because the schedule is driven by
   image count and is blind to size" appears as both mechanism and consequence).
   One derivation. (−60 w)
5. G1 summary trim (l. 435–450). (−40 w)

### 3.4 `related.tex` — 2,416 w → target ~2,190 (−225)

**Spotlight:** the Positioning section + table — this is what examiners read
first. Its three narrow precedence claims are exactly right; do not touch their
scope.

Cuts:
1. **Pre-LLM ML-serving genealogy** (l. 100–116): Swayam, MArk, Clockwork,
   INFaaS, AlpaServe, InferLine each get a clause; only InferLine (per-stage
   pipeline sizing) is a real comparator. Compress the other five to one
   sentence + citation block; keep InferLine's two sentences and Autopilot.
   (−90 w)
2. **"Two gaps" paragraph vs Positioning** (l. 163–172 vs 279–317): gap 1
   (single-stream signals) is restated in Positioning's claim 1; gap 2 (no TSFM
   evaluation) in claim 2. Keep the Two-gaps paragraph as the *section-local*
   one-liner version (it already is fairly short); trim its second halves
   ("…reproduces the missizing this thesis quantifies" and "…which remove the
   per-signal modeling burden" carry the argument — keep those, drop the
   set-up clauses). (−50 w)
3. **Positioning claim 1 re-quotes R²=0.123/0.654** (l. 300–302): trace-eda owns
   the pair; here "nearly decoupled from request rate (R²=0.12 vs 0.65 for
   decode; Chapter trace-eda)" is fine — it is already one clause. Leave.
   Instead trim the *last-column* explanation (l. 321–327), which the table
   caption (l. 331–340) repeats verbatim-ish: state once in the caption, one
   pointer in text. (−60 w)
4. TSFM catalogue (l. 215–228): each model one clause — already tight; optional
   −25 w by merging Moirai/Lag-Llama/Time-MoE into one "…and others" clause
   (they are never used again). (−25 w)

### 3.5 `predictors.tex` — 2,756 w → target ~2,560 (−200)

**Spotlight:** S2's verdict sentence (l. 140–141, bold, 20/20) and the
calibration finding (l. 262–270) — the p90-coverage 0.88–0.90 is what the whole
closed loop stands on. Both already prominent.

Cuts:
1. **Baseline configuration details** (l. 69–78): α=0.3 / β=0.1 / γ=0.1 /
   seasonal-period mechanics → "conventionally configured (parameters in the
   manifest)"; keep the fixed-parameter honesty (it recurs in Limitations,
   owner there). (−45 w)
2. **Dynamo-shipped-predictor paragraph** (l. 164–176) closes with "…which the
   closed loop turns into a mechanical result" — and closedloop's model-choice
   item states the same with the same ARIMA/Kalman/Prophet list. Ownership:
   predictors owns the *accuracy* statement (keep the frontier sentence), the
   closed-loop consequence → one clause. (−35 w)
3. **Finding 4 MAE anchor** (l. 185–192): keep "≈1,302 images (21.7 img/s
   against a common-span mean of ≈41)" — it calibrates absolute error — but the
   parenthetical span-over-representation cross-ref appears 3× in the chapter
   (l. 55–58, 190–191, implicit at 130); twice is enough. (−20 w)
4. **Protocol stride mechanics** (l. 37–49): the origin-tiling description is
   load-bearing (it defines "as a scaler would consume"); the context-budget
   sentence ("120 forecast tokens (one point plus nine quantiles over the
   horizon)") is manifest detail. (−25 w)
5. G1 summary trim (l. 344–365): the summary is currently a full second
   statement of all four findings. Halve. (−75 w)

### 3.6 `aiconfigurator.tex` — 2,507 w → target ~2,380 (−130)

**Spotlight:** S3. The strata taxonomy (l. 135–156) is genuinely good pedagogy
and the foundation of the "lookup-table-of-measurements" claim — keep whole.

Cuts:
1. **Out-of-envelope paragraph** (l. 83–90): compress to two clauses (giant tail
   memory-infeasible → excluded at the hardware envelope; spurious OOMs
   requeued). (−45 w)
2. **Two-pool composition section** (l. 331–356): the 50-request smoke test gets
   a full paragraph; one sentence carries it ("a 50-request smoke workload
   produces a complete AIPerf-style report end to end"). Keep the h100_sxm
   16384-token extrapolation caveat verbatim (owned here, quoted by twopool).
   (−45 w)
3. **Infill paragraph** (l. 103–118): keep both dataset states + the ≈1%
   re-derivation result (honesty); trim the justification tail ("which is why
   grid-exact silicon at the query shapes was worth collecting"). (−20 w)
4. Summary (l. 358–375) restates both findings + 3% + 12.8% + 17% — it is the
   chapter's headline set, but "every remaining difference enumerated and
   bounded" + the two-findings restatement can lose ~20 w. (−20 w)

### 3.7 `trace-eda.tex` — 2,537 w → target ~2,400 (−140)

**Spotlight:** S1 + the persistence table. The closing sentence of §multires
("provisioning the vision pool from the request signal misses precisely the
moments that matter", l. 352–353) is the chapter's best line — keep.

Cuts:
1. G2 caption dedup: `fig:eda-arrival` (Fano numbers), `fig:eda-decouple`
   (R² + two-orders), `fig:eda-acf` (0.64/69/9 restated). Keep each caption's
   *reading instruction*, drop the number echo. (−70 w)
2. **Hill-estimator sentence** (l. 63–66): "indicative only" tail-index aside →
   halve ("generated tokens are the heaviest-tailed (Hill, indicative), so
   decode capacity is quantile-driven"). (−25 w)
3. **Archetype prose vs table** (l. 74–84): "The fit is cuML k-means with k=4
   (silhouette-selected over k∈{3,…,9}, a near-tie…)" — keep near-tie honesty,
   drop the k-range parenthetical (manifest). The frames-class overlap sentence
   (l. 79–82) is load-bearing (two definitions coexist) — keep. (−20 w)
4. G1 summary trim (l. 389–403). (−25 w)

### 3.8 `apendice.tex` — 1,769 w → target ~1,690 (−80)

Manifest + env untouchable. Cuts:
1. `fig:app-engines` caption (l. 141–151, ~90 w): the sweep-count/CI details
   (69 batch sizes, CI < 0.06 ms, 13 sizes) → keep "dense sweep, tight CIs";
   the band/cap reading stays. (−30 w)
2. **Upstream-contributions paragraph** (l. 191–207): keep both contributions
   fully (they are the returned-value record) but the grid-edge numerology
   (m=32768 / 784N / 401408 / batch 512) can drop to "the GEMM and attention
   grids stopped well short of ViT shapes; ViT-shape rows were collected and
   returned". The exact numbers are in the PR. (−40 w)
3. §Supplementary figure captions (l. 67–91): `fig:pred-heatmap` caption
   editorializes ("precisely wrong for bursty, mean-reverting rates") — that
   is the one caption whose explanation exists nowhere else; keep it. No cut.

### 3.9 `baselines.tex` — 1,621 w → target ~1,580 (−40)

Already tight; the billing paragraph, TP-layout finding, and burst3-defeats-
reactive result are all owners. Only polish:
1. l. 96–101: the stage-conditional C* caveat sentence is long; one clause
   shorter. (−20 w)
2. l. 229–239 summary: "(RQ1's missizing, priced)" style is good; the full-trace
   sentence re-quotes 677/2,905/588/0.687× from the closedloop ledger table —
   keep 0.687× + verdict, drop the three re-quoted latencies. (−20 w)

### 3.10 `validation.tex` — 1,142 w → target ~1,120 (−20)

Done. Only the budget-units finding (l. 133–141) can lose its last clause
("…and remains a reportable upstream defect" duplicates "equalizes the caps").
(−20 w) **Everything else stays** — this chapter is the model of what the others
should read like.

### 3.11 `conclusion.tex` — 923 w → target ~890 (−35)

Done. One cut: the closed-negative-result parenthetical (l. 106–110, the
structural language-pool predictor) is predictors' §covariates finding restated
with its mechanism; one clause suffices ("a structural prefill decomposition was
tested and closed — it buys nothing at onsets; Chapter predictors"). (−35 w)

### 3.12 `tese.tex` abstract + Resumo — ~700 w → target ~640 (−60)

Both were trimmed in round 1 and are now good. Remaining:
1. The "(tested under a held cursor, not a second anticipation experiment)"
   caveat appears in both abstracts in full parenthetical form. It is a
   body-level honesty distinction; in the abstract "a tail-aware *conversion* of
   the same forecast" already carries it. Keep the clause in the body
   (closedloop owns it), drop the parenthetical from both abstracts. (−30 w EN +
   −30 w PT)
2. Keep: "the week-scale economics are simulated" closing sentence (honesty),
   both keyword blocks, 0.62×/0.96× as the only two ratios.

---

## 4. Structural options — need a decision, each trades something

**A. Draft-status note** (`tese.tex` l. 124–139, ~120 w + 1 page): already
marked "REMOVE for the defense/submission version". Removing it now saves a page
immediately; keeping it is correct while the advisor-review framing still
applies. *Recommend: remove at defense build, not now.*

**B. Per-burst ledger tables → burst3 + aggregate only** (closedloop §ledger):
the known big lever, ~1.5–2 pages. Adjudicated against in round 2 because the
burst1/4/5 tie-at-floor rows *are* finding S6's "the improvement is localized"
evidence, and the user's own directive ("every relevant metric per pool")
mandates them. *Recommend: keep. Revisit only if a hard page limit appears.*

**C. `fig:cl-framework-diff`** (closedloop l. 331–350): a 3-panel summary figure
whose panels (a) and (b) visualize numbers fully stated in prose and tables;
panel (c) is a pointer to validation. ~0.7 page + 130-w caption. It is,
however, the one *figure* a reader can cite for the whole argument
(accuracy-parity → verdict-category → live-anchor). *Recommend: keep the figure,
cut the caption per G2 (−80 w). Drop the figure only under a page limit.*

**D. `apendice_ecosystem.tex` — NOT IN THE BUILD.** Verified: `tese.tex`
includes only `apendice`; the PDF contains no ecosystem section. Its 808 words
cost zero pages today. Decide one of:
   - (i) leave as-is (a drafted, unused file — costs nothing, slightly
     misleading in word counts);
   - (ii) wire it in (`\input` at the end of apendice.tex) at ~1.5 pages if the
     committee should see the stack overview;
   - (iii) delete/archive the file.
   *Recommend (i) now, decide (ii) vs (iii) with the advisor.* Round-1/2 edits
   to this file changed nothing visible — worth knowing.

**E. TikZ architecture figure** (intro l. 260–306): earns its page — keep.

---

## 5. Totals

| Chapter | Now | Cut | Target |
|---|---:|---:|---:|
| closedloop | 7,337 | −500 | 6,840 |
| intro | 3,382 | −480 | 2,900 |
| twopool | 3,363 | −280 | 3,080 |
| related | 2,416 | −225 | 2,190 |
| predictors | 2,756 | −200 | 2,560 |
| trace-eda | 2,537 | −140 | 2,400 |
| aiconfigurator | 2,507 | −130 | 2,380 |
| apendice | 1,769 | −80 | 1,690 |
| baselines | 1,621 | −40 | 1,580 |
| conclusion | 923 | −35 | 890 |
| validation | 1,142 | −20 | 1,120 |
| abstract+Resumo | 700 | −60 | 640 |
| (ecosystem — not in build) | (808) | 0 | — |
| **Total** | **~30,450** | **−2,190** | **~28,260 (−7.2%)** |

Pages: **137 → ≈ 131–133** from §3 alone; **≈ 128–130** if options A + C-figure
are taken at defense time. Beyond that, only §4B moves the needle, at real
evidentiary cost.

## 6. Execution & verification protocol (same as rounds 1–2)

1. Apply per chapter with exact-match edits; closedloop tables remain
   byte-locked.
2. After the pass: rebuild (`latexmk`), assert 0 errors / 0 undefined refs;
   cross-file `\label`/`\ref` orphan scan = 0; `./provenance/verify_all.sh`
   must return DELIVERY-READY (30 checks incl. rejected-fix and
   methodological-overclaim patterns).
3. Deep-verify lenses (forensic-diff vs the pre-round commit, hostile
   seam-reader, honesty-adversary, number-consistency vs DB, table↔prose,
   acronym/ref) — the round-2 harness is archived at
   `provenance/audit/deep_verify.js` and re-runnable as-is.
4. Adjudication rule unchanged: an under-cut is acceptable; a lost finding,
   caveat, or protected value is not.
