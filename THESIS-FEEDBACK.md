# Advisor Review (v2) — `tex/tese.tex` and included chapters

> ## Resolution log — 2026-07-08 pass (all items adjudicated)
>
> Every numbered item was checked against the current tree and artifacts;
> fixes verified by rebuild (92 pp, zero undefined refs) and by re-running
> the underlying simulations where the item demanded data. Statuses:
> **DONE** (fixed & verified) · **DONE-BY-DATA** (new run performed) ·
> **SCHEDULED** (belongs to the baselines/closed-loop/validation chapters,
> which are in preparation from completed experiments) · **DEFERRED**
> (deliberately postponed, reason given) · **REJECTED** (checked; not a
> defect).
>
> | Item | Status | Resolution |
> |---|---|---|
> | B1 abstract/resumo | **DONE** | Abstract + Portuguese resumo written into `tese.tex` front matter |
> | B2 title/metadata | **DONE** | Real working title; institutional class/committee page deferred to template adoption (noted in source) |
> | B3 thesis statement | **DONE** | Final clause written from delivered closed-loop results (no placeholder) |
> | B4 contribution absent | **DONE/SCHEDULED** | RQ4 + Contribution 5 now state the delivered results with numbers; chapters in preparation, marked as such |
> | B5 placeholders | **DONE** | 8 of 9 resolved with content; 1 remains by design (validation anchors — Phase 5.1) |
> | B6 lists | **DONE** | LoF, LoT, List of Abbreviations (19 entries) added |
> | H1 missing LLM/AIC burst row | **DONE-BY-DATA** | Ran it: TP1×2 FAILS at s=1 (TTFT p99 1,868 ms vs poly 910); TP2×2 passes (748 ms). Table row added; inversion reframed as "both fail at naive topology, differently — shape-fixable prefill floor vs capacity-only queueing"; at the SLA-shaped (TP2) config the original contrast holds verbatim. Reviewer's 9%-margin warning was exactly right |
> | H2 ≥16× overclaim | **DONE-BY-DATA** | Swept s=3: poly knee→3 (ITL 94.3), calibrated knee stays 2 (s=3 fails, ITL 109.5). All "≥16×" claims replaced with "an order of magnitude" (provable >10× calibrated) |
> | H3 token-accounting contradiction | **DONE (disclosure)** | Full directional-bias paragraph in Ch.6 limitations: 196-vs-66 same-tensor conflict, ~3× frames prefill undercount, both biases named, TP1 floor robust / TP2 margin convention-dependent. Both-conventions run scheduled with closed-loop regen |
> | H4 vision-calm steady window; single-window knees | **DONE (cite + caveat)** | Limitations now state head2k is vision-lean (2.9 vs ~14 img/req) and cite the grid's multi-window re-derivation (all 6 bursts + 24-h steady; C* 6–16 vs 2) |
> | H5 3% scope; production forward unmeasured | **DONE** | "≈3% (strictly 3.2%)"; intro/RQ3/contributions re-scoped to attention-only + conservative band; "sits between" → "expected to sit between… scheduled validation work" |
> | H6 fidelity asymmetry | **DONE** | Explicit paragraph in Ch.6 limitations (sensitivity ≠ accuracy; h100 data not re-validatable here; + 16k-token extrapolation share 3.1%) |
> | E1 persistence gradient/estimators | **DONE** | Hurst=spectral identity disclosed (H=(1+β)/2, "one estimator, two views"); "three independent estimators agree" deleted here and in intro; four-signal monotone gradient dropped for the images-vs-requests contrast; gen anomaly explained via arrival-stamping |
> | E2 decode quarantine | **DONE** | † marker in persistence table; caveat at intro first use, RQ1, and summary ("offered work") |
> | E3 FM win sizing | **DONE** | 2–9% relative at 1-min stated; WAPE≥100% no-skill floor explained; "one-third" reframed; per-forecast cost (≈65–90 ms) + deployment-footprint asymmetry added |
> | E4.1 common-span asymmetry | **DONE (disclosure)** | Protocol now states 20% vs 98.7% coverage + burst over-representation + within-column-only reading; full realignment deferred to a rerun |
> | E4.2 baseline context budget | **DONE (disclosure)** | Limitation added (full-history + seasonal-naive would narrow margins); rerun deferred |
> | E4.3 "tuned" false | **DONE** | "fixed-parameter classical baselines" everywhere |
> | E4.4 no ARIMA | **DONE (bridge)** | Limitation notes ARIMA runs where it matters: Dynamo's own ARIMA predictor is a closed-loop baseline policy (14-run set + head-to-head exist) |
> | E4.5 significance | **DONE (disclosure)** | Bold winners flagged as ≤0.1-WAPE, "three-way tie" reading; bootstrap/DM deferred |
> | E5 burst-onset evaluation | **SCHEDULED** | The closed-loop lead-sweep (30–300 s, reactive vs forecast on the fastest-onset burst) is the operational form of this metric and exists; a Ch.4 detection-delay table from the archive is queued for the closed-loop chapter |
> | E6 band figure vs caption; p90 uncalibrated | **DONE-BY-DATA** | Empirical coverage computed over the archive (`predictors/results/metrics/quantile_coverage.json`): p90 = 0.88–0.90 at 1-min for every model/signal (nominal .90) — the p90 rule survives; p10 zero-tie distortion quantified (band 69% vs nominal 80%). Caption fixed to "piercing … as a calibrated p90 should (measured 11%)"; new §"Is the band calibrated?" |
> | E7 contamination | **DONE** | Limitation sentence + TimesFM-2.0-predates-release bound (≈2 WAPE points) |
> | E8 TimesFM ablation conflation; silhouette | **DONE-BY-DATA** | Sentence rewritten (univariate control ≠ request-rate-only policy); silhouette recomputed (k=4: 0.388 max over k∈{3..9}; 0.378/0.319 neighbors) and quoted |
> | C1 single trace | **DONE** | Mechanism-hypothesis paragraph (batch video tenants) + falsifiability statement added to Ch.3 limitations; generality already scoped per-chapter |
> | C2 foregone-conclusion risk | **DONE-BY-DESIGN** | Already satisfied by the delivered experiments: reactive baseline watches the same image signal (signal choice separated from forecast value); SLA × provisioned worker-seconds is the score; adversarial/regime cases in the fleet matrix |
> | C3 newsvendor framing | **DONE** | Critical-fractile paragraph + Arrow-Harris-Marschak citation in Ch.4; related-work sentence added |
> | C4 zero-shot lever | **DONE (disclosure)** | Fine-tune split named as the bounding experiment, deferred with the operational-simplicity argument |
> | C5 SLA grounding | **DONE** | Bounds tied to 2× Dynamo planner defaults + disaggregated-serving practice (cites); sensitivity already in limitations |
> | C6 count vs content | **DONE** | "request rate" wording fixed in Ch.2/positioning; "no new instrumentation" point added to intro |
> | X1 7.82/8.16 | **DONE** | Raw-slice/infilled-slice labels defined once and applied (validation table caption, smoke test, f(N) table reconciliation incl. 11.36/11.30 + 1.45/1.38) |
> | X2 summary counts | **DONE** | 7,760/34,710 with campaign+infill breakdown |
> | X3 knee-table column label | **DONE** | "TTFT / enc. delay p99"; caption states which rows report which |
> | X4 315 ms | **DONE** | 316.4 ms (= f(64)) |
> | X5 147 forwards | **DONE** | 148 (147×f(64)+f(1)), matching the converter |
> | X6 87 vs 101 | **DONE-BY-DATA** | Recomputed: 101 windows > p99 forming 87 runs → 18 merged episodes; both sentences rewritten; Jaccard sets defined (≥p99; 6 request-minutes tied at threshold) |
> | X7 3% → 3.2% | **DONE** | "≈3% (strictly 3.2%)" at source; "≈3%" at echoes |
> | X8 +24%/1.2×/1.24 | **DONE** | §5.5 duplicate removed entirely (trimmed to forward pointer); remaining uses = 1.24×/+24% |
> | X9 two frames definitions | **DONE** | Distinguishing sentence at first co-occurrence (threshold class vs archetype) |
> | X10 "indistinguishable" | **DONE** | "unremarkable in level (barely above its own p99 of 4.35); more decisively … disjoint (Jaccard 0.02)" |
> | X11 SLA/SLO | **DONE** | Both defined at first use in Ch.1; "evaluation SLA" fixed as the document's term of art |
> | X12 ≈2 s p99 | **DONE** | "≈2 s at roughly p98 (union bound); stage budgets are engineering heuristics" |
> | X13 episode vs window | **DONE** | Terminology note in Ch.6 (episode = Ch.3 object; scenario window = envelope); wording swept |
> | X14 tuned | **DONE** | = E4.3 |
> | W1 sentence length | **PARTIAL** | Worst offenders split (intro opener, results ¶, knee prose rewritten); global pass deferred to final copy-edit per the review's own ordering |
> | W2 editorializing | **DONE** | "real forecast capital", "essentially free", "honest reading", "and the headline:", "where load lives", "locates the exit", "plumbed" all replaced |
> | W3 captions argue | **DONE** | Onsets + seven-day captions descriptive; band caption corrected (E6) |
> | W4 redundancy | **PARTIAL** | §5.5-vs-Ch.6 duplication removed; intro restatement retained by design (one number per result), full tightening pass deferred |
> | R1 biblatex | **DEFERRED** | Manual entries repaired in place (below); migration postponed until the institutional template decision (which dictates the bib style) — both changes touch every entry once |
> | R2 venues/preprints | **DONE** | "(to appear)" on ICML'26/NSDI'26; arXiv-only entries already preprint-styled; Mooncake "(Best Paper)" dropped |
> | R3 author lists | **DEFERRED** | BurstGPT/Aegaeon/BlitzScale "et al." expansion needs web-verified lists — queued with the bib migration; entries carry arXiv IDs meanwhile |
> | R4 dataset citation | **DONE** | AzureLMM2025 rewritten as a dataset citation (repository, release context, access date, terms pointer) |
> | L1 book class | **DEFERRED** | Documented in source; abnTeX2/departmental template adoption is a single later switch |
> | L2 boxes | **DONE** | URL footnote fixed via `\url`; new worst overfull is 12 pt in one caption (pre-existing class); 0 undefined refs |
> | L3 keep headers | **KEPT** | Retained |
>
> Beyond the listed items, the pass added: architecture diagram (Fig. 1.1,
> TikZ), f(N) measured-vs-composed + kernel-ledger figure (Ch.5),
> three-model burst comparison figure (Ch.4), reproducibility appendix
> (environment + figure/table→script→artifact manifest), hyperref, and a
> cap-sensitivity run (32/64/128 → p99 5.16/5.01/6.74 s: burst verdict
> cap-insensitive). New runs are ledgered in `progress/results-ledger.md`.

Reviewed: `tese.tex`, `intro.tex`, `related.tex`, `trace-eda.tex`, `predictors.tex`,
`aiconfigurator.tex`, `twopool.tex`, the build log, and the rendered headline figures
(`sim_knees.png`, `pred_forecast_band.png`). Build state: clean — 57 citations / 57 bib
entries, no undefined references, all 13 figures resolve; only minor under/overfull boxes.

**About this revision.** Every claim in this review was re-verified against the sources
(file:line given throughout; arithmetic recomputed; two figures inspected pixel-level).
Five v1 items did not survive verification and were dropped or corrected — they are listed
in §11 for transparency. Roughly eighteen new, verified issues were added, including two
that materially affect the thesis's headline result (H1, H2).

Severity: **[Blocker]** must be fixed before submission · **[Major]** materially weakens a
claim or the argument · **[Minor]** polish. Issues are numbered (B/H/E/C/X/W/R/L) so you
can track them.

---

## 1. Overall assessment

The thesis is well-conceived and genuinely original. The central argument — *in
modality-disaggregated multimodal serving, no single load signal sizes every pool; the
vision signal is simultaneously the least visible to conventional autoscaling and the most
forecastable; therefore provision each pool predictively on its own signal* — is crisp and
defended at three independent levels (statistical decoupling, forecastability, simulated
saturation). The reproducibility discipline (versioned scripts, archived artifacts, an
upstream PR, corrections recorded rather than absorbed) is exemplary. Related work is
current, broad, and honestly positioned; "none of the ingredients is novel — the finding
is" (`related.tex:297-303`) is exactly the right register. The internal numeric
consistency is, with the specific exceptions catalogued in §6, very good — most
headline numbers cross-check exactly across chapters, which is rare in a draft.

Three systemic problems dominate everything else:

1. **The thesis does not yet contain its own thesis.** The position statement has a
   `[Placeholder]` where its operative clause belongs (`intro.tex:190-193`); RQ4 — the
   closed-loop payoff, the actual contribution — is deferred (`intro.tex:230-238`); four
   of five contributions are platform, not result. See B3–B4.
2. **The headline simulation claim is under-evidenced on its most important half.** The
   burst-window "inversion" — the language pool *still meets* the SLA while the vision pool
   violates — is supported only by the timing model the same chapter deprecates for exactly
   this purpose, with a 9% margin against a documented +24% timing effect (H1); and the
   "≥16×" knee separation is an over-claim given the octave-spaced sweep grid (H2).
3. **Single-dataset dependence.** One seven-day trace, one cluster, a by-construction
   50/50 modality split. Acknowledged, but it must temper the language of generality
   everywhere, not only in limitations (C1).

None of these is fatal. H1/H2 are fixable with one additional run and one rewording; the
missing chapters are scheduled work. But all three must be treated as the critical path.

---

## 2. Blockers: completeness and front matter

- **B1. No abstract.** None exists. Mandatory. If the institution is Brazilian (the
  `tese`/`figuras`/`mestrado` naming suggests it), you also need a Portuguese *resumo* and
  palavras-chave, and likely an ABNT-compliant class (see L1).
- **B2. Placeholder metadata.** Title is "Thesis Draft Chapters --- Workspace Preview
  Build" (`tese.tex:19`); `\date{\today}`; no title page, committee page, institution,
  program, or advisor.
- **B3. The thesis statement is incomplete.** `intro.tex:190-193` ends in
  `[Placeholder: final clause pending the closed-loop evaluation]`. Even in draft, write
  the claim you intend to prove; a reader cannot judge an argument whose conclusion is a
  placeholder.
- **B4. The contribution proper is absent.** RQ4 (`intro.tex:230-238`), Contribution 5
  (`intro.tex:360-368`), the baselines chapter, the closed loop, validation, and
  conclusions are all deferred. Chapters 3–6 are setup. Until the closed loop lands, frame
  them explicitly as platform — and treat that chapter as the critical path.
- **B5. Placeholders in prose.** Seven `[Placeholder: ...]` markers across `intro.tex` and
  `related.tex`. Track them centrally; none may survive the final build.
- **B6. Missing lists.** No list of figures/tables and no acronym/symbol list, in a
  document dense with TTFT, TPOT, SLA/SLO, KV, ViT, TSFM, AIC, WAPE, MAE, CV², ACF, ITL,
  TP, LRD, FIFO. At least the acronym list is near-mandatory (see also X11 on SLA vs SLO).

---

## 3. The headline result (Chapters 5–6): issues that touch it directly

### H1. [Major — top priority] The burst-window inversion rests on the timing model the chapter itself disqualifies
`tab:sim-knees` contains **no `LLM / AIC & burst` row** — only `LLM / poly & burst`
(`twopool.tex:213`), and the figure legend confirms no such run exists (`sim_knees.png`:
`head2k·poly`, `head2k·aic`, `burst1·poly`). Yet the chapter's central sentence — "the
language pool, fed the very same requests, **still meets the full SLA** at that rate"
(`twopool.tex:250-252`), repeated in the intro (`intro.tex:47-49`, `:355-357`) — is a
burst-window claim about tail latency. Section 6.2 states plainly that "burst behavior —
precisely what autoscaling experiments measure — is visible **only under calibrated
timing**, so all headline runs use AIC timing" (`twopool.tex:60-63`). The one headline run
that most needed calibrated timing is the one run without it.

The margin makes this urgent, not pedantic: poly burst TTFT p99 = **910 ms**, i.e. 9%
under the 1,000 ms bound (visually *on* the SLA line in `sim_knees.png`), while the
documented poly→AIC p99 inflation on the steady window is **+24%** (307 vs 248,
`tab:sim-poly-aic`). If even half that inflation transfers to the burst window, the
language pool crosses the bound at s=1 and the clean "opposite order" inversion collapses
into "both pools violate in the burst."

**Fix:** run the burst window under AIC timing (one run; the pipeline exists). If the
language pool holds, the headline is secured; if it crosses marginally, reframe from
"language still meets the full SLA" to the defensible contrast that survives either way —
vision exceeds its bound by 5× (5,013 ms) at 29% utilization while language sits at/near
its bound. The per-pool-signals thesis survives; the current wording may not.

### H2. [Major] "Saturation knees ≥16× apart" is an over-claim given the sweep grid
The sweep is octave-spaced (knees at s=1, 2; the named successor of 2 is 4,
`twopool.tex:245`; vision censored at 32; the figure shows doubling points, with s=8
apparently skipped in the language panel). "Knee" is defined as the *largest swept s
meeting every bound* (`twopool.tex:198`). Therefore the language pool's true knee lies in
**[2, 4)** and the vision pool's at **≥32**: the provable separation bound is
**>32/4 = 8×**, not ≥16×. "≥16×" (`intro.tex:46-47`, `twopool.tex:238`, `:313`) is the
ratio of last-passing swept points, which equals the true-knee ratio only if the language
knee is exactly 2.

**Fix (either):** (a) sweep s=3 (and s=2.5 if needed) for the language pool — if it fails
at 3, the bound becomes >32/3 ≈ 10.7×, and the exact wording can follow the data; or
(b) reword to the statement the data already supports: "the vision pool sustains 16× the
trace scaling that the language pool sustains." Also reconcile the mixed phrasing "offered
loads … apart" (`intro.tex:47`) — the pools' loads are in different units (req/s vs
img/s); what is 16× apart is the trace-scaling factor.

### H3. [Major] Per-request token accounting is internally contradictory — and both biases point toward the headline
Three conventions coexist for the *same* request:
1. **Encoder work:** every image costed as a full 448² forward (784 patches)
   (`twopool.tex:160-164`).
2. **Handoff:** 196 post-merge tokens/image shipped across the seam
   (`twopool.tex:151-155`).
3. **Prefill length:** the trace's `ContextTokens` verbatim — which embeds the *traced*
   model's vision tokenization at ≈277→**66** tokens/image at scale
   (`trace-eda.tex:37-42`, fig. caption `:50-53`).

Items 2 and 3 describe the **same tensor** — the embeddings the encoder emits and the LM
consumes — yet the seam transfers 196 tokens/image of bytes while the LM's input grows by
~66/image. For the median top-1% frames request (529 images, ≈36,000 recorded context
tokens, `trace-eda.tex:349-352`), a Qwen3-VL-consistent input would be ≥529×196 ≈ 104k
tokens — the simulated prefill under-counts frames-class language-pool work by roughly
**3×** under the simulation's own encoder assumptions. And the trace's own evidence that
the production model spent only ~66 LM tokens/image at scale suggests the uniform-448²
full-compute assumption *overstates* frames-class encoder work. Note the alignment: the
first bias makes the language pool look better in bursts, the second makes the vision pool
look worse — **both push toward the burst-inversion headline** (and H1 already shows that
verdict has a 9% margin). The thesis prides itself on directional-bias accounting
(`aiconfigurator.tex:266-272`); this is the one place the accounting is missing, and it is
load-bearing. `trace-eda.tex:391-395` even states the counts are "not transferable to a
different model's tokenizer" — and the simulation then transfers them.

**Fix:** pick one consistent convention (e.g., prefill = text-token estimate + 196/image),
or run the burst window under both conventions and report the band. At minimum, add the
directional analysis to `twopool.tex` limitations.

### H4. [Major] The "steady" window is unusually vision-calm, and every knee is a single-window point estimate
The steady window is the trace's first 2,000 requests: 2.77 req/s but only 8.0 img/s =
2.9 img/req (`twopool.tex:190-191`) against a weekly average of 23.7/1.7 ≈ 14 img/req
(`tab:eda-percentiles`) — the window carries ~5× less vision work per request than the
trace at large. The censored vision knee ("≥s=32" = 256 img/s) is measured on this
image-lean sliver, which inflates the steady-traffic headroom contrast that feeds the
"≥16×" claim. Moreover every knee is one deterministic run over one window; TTFT p99 on
2,000 requests is decided by ~20 tail samples. The burst result, likewise, is one episode
(the largest) of the 18 identified.

**Fix:** repeat the sweeps over several windows (e.g., a median-image-intensity steady
window; 2–3 additional burst episodes) and report the knee range. This simultaneously
addresses the determinism/no-error-bars concern.

### H5. [Major] Validation scope: "within 3%" is the operator, not the number the simulator consumes
The 3% agreement covers the encoder-attention operator alone — and is strictly 3.2%
(1.342 vs 1.300 ms, `aiconfigurator.tex:333-335`; write "≈3%"). The quantity the
simulation consumes — the composed full-forward f(N) — sits **1.37–1.62× below**
end-to-end measurement across the batch axis (`tab:aic-fn`, `aiconfigurator.tex:225-230`)
and 1.14–1.45× at batch 1 (`tab:aic-validation`). The intro's framing ("validated against
physical measurement — the collected operator agrees within 3% — makes the encoder pool's
simulated timing defensible," `intro.tex:41-44`) invites the reader to attach the 3% to
the simulated timing. Two subsidiary points:
- The claim that "a production encoder sits between" the composed bound and the HF-eager
  measurement (`aiconfigurator.tex:255-257`) is **asserted, never measured** — no
  production-vLLM forward is ever timed, though the container and kernel are in hand. One
  measurement closes this.
- Your conservative-direction argument (optimistic encoder cost ⇒ real saturation earlier
  ⇒ burst claims robust; `aiconfigurator.tex:266-272`) is sound and should be stated
  *wherever* the 3% is quoted — it, not the 3%, is what actually defends the simulation.

### H6. [Major→Minor] Fidelity asymmetry between the pools — state it once, plainly
The encoder model is collected and physically validated on your silicon; the language
pool's AIC `h100_sxm` timing is trusted from the shipped database and Dynamo's engine, and
is not (and cannot be) re-validated in this work. RQ3's wording is actually careful
("physically validated silicon data" vs "a calibrated engine," `intro.tex:219-223`), and
the poly-vs-AIC comparison honestly quantifies *sensitivity* — but sensitivity is not
accuracy, and `twopool.tex` limitations never state the asymmetry. Credit where due: the
steady-window language knee is timing-robust (s=2 under both models, `tab:sim-knees`).
The burst window is where the asymmetry bites — which is H1.

---

## 4. The empirical chapters (3–4): issues in the evidence base

### E1. [Major] The "persistence gradient" and its "three independent estimators" are overstated
`trace-eda.tex:158-163` claims: more vision-driven ⇒ burstier ⇒ more persistent, with
"three independent estimators — Fano growth, autocorrelation half-life, and spectral
slope — agree[ing] on this ordering." Three verified defects:
1. **Hurst and spectral slope are the same estimator.** Every row of
   `tab:eda-persistence` satisfies H = (1+β)/2 *exactly* (0.66→0.83, 0.72→0.86, 0.74→0.87,
   0.51→0.76, 0.82→0.91, 0.86→0.93). The Hurst column is algebraically derived from the
   slope column; presenting them as corroborating is circular. (Also: no Hurst estimation
   method is ever named — say which estimator produced H, and if it is the spectral
   identity, drop one column or add an independent estimator, e.g. DFA or R/S.)
2. **Per-signal Fano is never shown.** Fano numbers appear only for the request counting
   process (1.8→938, `trace-eda.tex:119-121`); the table has no Fano column, so "Fano
   growth agrees on this ordering" is unsupported for the other three signals.
3. **The orderings disagree.** Generated-tokens/s has the *shortest* ACF half-life
   (5 min — below requests' 9) but the second-*highest* Hurst (0.91). The half-life
   ordering (gen < req < ctx < img) and the Hurst ordering (req < ctx < gen < img) are
   different orderings; "agree" is factually wrong on the table's own numbers.

The contrast that *does* hold cleanly — images vs requests dominate on CV², half-life, and
Hurst simultaneously — is all the thesis needs. Lead with it; drop or heavily qualify the
four-signal monotone-gradient claim; explain the generated-tokens anomaly (see E2).

### E2. [Major] Decode-signal statistics are arrival-stamped and should be quarantined
The decode series stamps each request's full generated-token volume at its *arrival*
minute (`trace-eda.tex:166-171`) — it measures the arrival of decode work, not decode
load. Its CV², half-life, Hurst, and forecastability are then reported alongside signals
that do execute near arrival, and folded into the gradient narrative and RQ1's "largely
yes for decode (R²=0.654)." Given generated tokens is also the heaviest-tailed marginal
(Hill ≈1.9, `trace-eda.tex:62-63`), the anomalous high-Hurst/short-half-life combination
of E1 is plausibly an artifact of this construction. Add the caveat at every point of use
(the intro currently repeats decode numbers without it), and consider marking decode rows
distinctly in the persistence table.

### E3. [Major] The foundation-model win must be honestly sized at the operational cadence
Verified from `tab:pred-wape` (1-min, best FM vs best baseline EWMA): images 52.9 vs 54.2
(−1.3 pts, 2.4% rel.), requests 33.4 vs 35.2, context 43.2 vs 44.7, generated 37.4 vs 41.2
— a **2–9% relative** improvement at the only cadence near the control loop's. The
dramatic "one-third lower WAPE" (`predictors.tex:150-153`, echoed as Contribution 2,
`intro.tex:325-327`) lives at 1-second bins, where:
- **WAPE ≥ 100% means no skill.** The always-zero forecast scores WAPE = 100% by
  definition; at 1 s the best model scores **98.8%** on images (naive 156.9, EWMA 146.1).
  The celebrated one-third reduction is a move from "much worse than predicting zero" to
  "par with predicting zero." These margins are between degrees of uselessness, in the
  regime the thesis itself calls a shot-noise floor (`predictors.tex:174-178`) and where a
  12-step horizon (12 s) is below cold-start time anyway.
Reframe: the FM contribution at provisioning cadence is a *modest* accuracy gain plus
robustness (zero per-signal tuning, mild horizon decay, one model for all signals). Then
let the closed loop determine whether 2–9% converts into SLA/GPU-hour value over EWMA —
and report the answer either way; "tuned-EWMA is competitive at 1-min" would itself be a
useful finding. Also fix the cost framing: the 1–80 min vs ~1 min figures
(`predictors.tex:80-83`) are benchmark wall-clock; the operational difference is "a GPU
plus a 120M–2.5B model service" vs "a few lines of arithmetic" — state it that way.

### E4. [Major] Evaluation-design defects in the forecasting benchmark
1. **The common span is not comparable across resolutions.** Origins ≥8076 at every
   resolution (`predictors.tex:50-53`) means the 1-min columns evaluate only the final
   2,004 minutes — **33.4 h, 20% of the week, containing the largest burst** (admitted at
   `predictors.tex:179-181`) — while the 1-s columns cover 98.7% of the week. Column-to-
   column comparisons across the grid are therefore apples-to-oranges, and the 1-min model
   ranking is entangled with one episode. Fix: fix one absolute evaluation window (e.g.,
   the last 24–33 h) across *all* resolutions, or report per-day breakdowns.
2. **Baselines are handicapped by an FM-motivated context budget.** Giving classical
   methods TimesFM's 1,928-bin budget (`predictors.tex:48-49`) caps Holt–Winters
   seasonality at 1 h (32 h of context < two 24-h cycles) — so no baseline can see the
   diurnal structure Chapter 3 foregrounds (`trace-eda.tex:126-130`). Operationally,
   classical baselines would use *all* history at negligible cost. Give them full history,
   and add a seasonal-naive (t−24 h) baseline.
3. **"Tuned classical baselines" is false.** The summary claims the FMs beat "tuned
   classical baselines" (`predictors.tex:288-289`), but the protocol fixes textbook
   constants (α=0.3; HW 0.3/0.1/0.1, "configured conventionally,"
   `predictors.tex:63-67`). Untuned. Either tune them (per-series α by validation — which
   would likely *narrow* the FM margin; be prepared for that) or delete "tuned."
4. **No ARIMA/Prophet**, although the thesis names them as the incumbent predictors in
   production autoscalers, including Dynamo's own predictive loop (`related.tex:159-161`,
   `:228-231`). Your competitor-of-record's forecaster is absent from the comparison. Add
   ARIMA at minimum.
5. **No significance testing.** Bold winners in `tab:pred-wape` are decided by ≤0.1 WAPE
   (requests 1-min: 33.4 / 33.4 / 33.5). With 167 origins at 1-min, bootstrap CIs or a
   Diebold–Mariano test are cheap; without them, the inter-FM ranking claims (Toto-2 "takes
   15 of 20 cells," `predictors.tex:155-160`) are noise-level. You half-say this
   (`:161-162`) — make it quantitative.

### E5. [Major] No burst-onset (event-based) evaluation — the missing link to the closed loop
The entire motivation is catching burst *onsets* (median 6 min, fastest 1 min,
`trace-eda.tex:238-244`), yet Chapter 4 never measures forecast behavior at onsets:
everything is time-averaged WAPE/MAE plus one qualitative figure. Averages are dominated
by calm bins and plateau-riding; they cannot say whether the forecast raises capacity
*before* the ramp. Add an event-based metric over the 18 episodes: detection delay (first
tile whose forecast/p90 crosses an episode threshold) vs onset, hit/miss within cold-start
budget, and false-alarm rate. This is the single most valuable addition to Chapter 4 —
it is what the closed-loop chapter will actually consume, and it is computable from the
archived 19.2M-value forecast set today.

### E6. [Major] The p90-headroom rule is proposed on an uncalibrated band — and the showcase figure contradicts its own caption
The chapter proposes "provision at p90 during regime uncertainty" (`predictors.tex:251-252`)
while the limitations admit quantile calibration/coverage was never assessed
(`predictors.tex:278-281`). Worse, the figure contradicts the text: the caption says bins
"spike to 370 images/s **inside the band**" (`predictors.tex:265-266`) and the body says
the band "covers **nearly all** observed excursions" (`:250-251`), but in
`pred_forecast_band.png` the p10–p90 band tops out at ≈200–250 img/s while observed spikes
reach 320–370 — visibly *piercing* the band (as a p90 should ~10% of the time!). Fix the
caption; compute empirical coverage per signal/resolution from the archived quantiles (an
afternoon of work); and let the closed loop *derive* its headroom quantile rather than
hand-pick p90 — see C3.

### E7. [Minor] Pretraining-contamination caveat for "zero-shot"
Chronos-2 (arXiv 2510) and Toto-2 (2605) postdate the trace's 2025 public release. If any
pretraining corpus ingested series derived from the released trace, "zero-shot" is
compromised. Verbatim ingestion of your derived per-bin series is unlikely, but the
check (model cards / training cutoffs) costs one sentence and is now standard TSFM-
benchmark hygiene. State it in `predictors.tex` limitations.

### E8. [Minor] Two smaller Chapter-4 defects
- The claim that TimesFM's covariate-blindness "is precisely the request-rate-only
  ablation conventional autoscalers embody" (`predictors.tex:62-64`) conflates two
  different things: univariate-per-signal forecasting still watches *each pool's own
  signal*; a conventional autoscaler watches *only the request rate*. Delete or rewrite.
- k=4 "by silhouette" (`trace-eda.tex:74-76`, used by Chapter 4's narrative) reports no
  silhouette values or stability; add them, since the 3.4%-archetype figure is quoted
  downstream.

---

## 5. Cross-cutting scientific concerns

- **C1. [Major] Single trace, by-construction split.** All quantitative claims derive from
  one seven-day trace of one cluster whose 50/50 modality split is constructed
  (`trace-eda.tex:387-395`). Temper generality language throughout ("multimodal serving
  workloads exhibit…" → "this trace exhibits…"), and add a paragraph *hypothesizing the
  mechanism* of the decoupling (a few tenants running batch video jobs?) — a mechanism
  argument is the only available bridge from one trace to a class of workloads, and
  ModServe's own burstiness observations can support it.
- **C2. [Major] Foregone-conclusion risk in the closed loop.** By Chapter 6 the deck is
  stacked: the vision signal is decoupled, forecastable, and invisibly saturating. A
  reactive baseline fed the *request rate* is designed to lose. For the result to carry
  weight: (a) give the reactive baseline the *right* signal (image rate) so signal-choice
  and forecast-value are separated — your planned ablation, but it must be the headline
  comparison, not a sensitivity; (b) include scenarios where forecasting can lose (the
  mixed-composition outlier episode, `trace-eda.tex:226-228`; regime changes; injected
  forecast error); (c) score everything as SLA compliance × GPU-hours so Chapter 4's WAPE
  finally converts to value.
- **C3. [Minor, high-leverage] Frame headroom sizing as a newsvendor problem.** The
  quantile-headroom decision is exactly a critical-fractile choice: the optimal quantile
  follows from the ratio of under-provision cost (SLA penalty during cold-start lead time)
  to over-provision cost (GPU-hours). This connects Chapter 4's bands, the cold-start
  parameter, and the closed loop's objective in one line of theory, replaces the arbitrary
  p90, and situates the thesis in a literature (staffing/newsvendor under lead times) the
  related-work chapter currently misses.
- **C4. [Minor] Zero-shot-only is an unpulled lever.** You have 7 days; fine-tune on days
  1–3, test on 4–7, even for one model, to bound the upside — or argue concretely
  (operational simplicity) why zero-shot is the right deployment posture. The current
  "conservative reading" (`intro.tex:389-390`) is an assertion the reader cannot size.
- **C5. [Minor] Ground the evaluation SLA.** TTFT p99 <1 s / ITL p99 <100 ms / encoder p99
  <1 s (`twopool.tex:177-184`) are asserted. Cite an external SLO reference or show knee
  positions under a small SLA grid (you already show one alternative at
  `twopool.tex:286-290` — one more row makes it a sensitivity analysis).
- **C6. [Minor] "Invisible in the request stream" conflates count with content.** The
  image rate is perfectly computable from the request stream's *content* — every request
  carries `NumImages` at admission; it is invisible only in the request *count/rate*
  (`related.tex:99`, `:288`; `trace-eda.tex:152`). This matters practically (no exotic
  instrumentation is needed to watch the right signal — a point *for* your proposal).
  Standardize on "request rate"/"aggregate arrival count" when that is what is meant.

---

## 6. Verified numerical and internal inconsistencies

| # | Defect | Locations | Fix |
|---|--------|-----------|-----|
| X1 | Encoder unit cost quoted as 7.82 ms (pre-infill) and 8.16 ms (post-infill) with no reconciling sentence at point of use; Ch.5's validation and smoke test use the former, Ch.6's runs the latter. Companion mismatch: measured 11.360 vs 11.30, ratio 1.45 vs 1.38 between `tab:aic-validation` and `tab:aic-fn`. | `aiconfigurator.tex:319,346,368` vs `:225`; `twopool.tex:122` | One canonical sentence: "pre-infill 7.82 (validation baseline) → post-infill 8.16 (all Ch.6 runs)"; label tables pre/post-infill. |
| X2 | Chapter summary reports the **pre-infill** dataset (7,679 / 34,326) after the body established the final counts (7,760 / 34,710). | `aiconfigurator.tex:400-401` vs `:128` | Summary should state final counts (or "7,679 + 465 infill"). |
| X3 | `tab:sim-knees` last column labeled "TTFT p99" but vision rows report *encoder-delay* p99; the caption does **not** clarify. | `twopool.tex:209` vs `:214-215` | Relabel "TTFT / encoder-delay p99" or split the column. |
| X4 | Max per-forward cost stated as "at most 315 ms" vs the chapter's own f(64) = 316.4 ms. | `twopool.tex:256` vs `:123` | Unify (316.4, or explain). |
| X5 | Largest request: 9,409 images at a 64-image cap is **148** forwards (64×147=9,408), text says 147. | `twopool.tex:145` | Verify against the script; fix the off-by-one. |
| X6 | Hot-image minutes: "exceeds its 99th percentile in **87** windows" vs "**101** hot-image minutes" for nominally the same top-1% set (1% of 10,080 ≈ 101). | `trace-eda.tex:219` vs `:355` | Define each set once (threshold vs rank? strict vs ≥?) and reconcile. |
| X7 | "Agreement within 3%" is strictly 3.2% (1.342 vs 1.300). | `aiconfigurator.tex:333-335` et al. | Write "≈3%" or "within 3.3%". |
| X8 | TTFT-tail inflation stated as "+24%", "≈1.2×", and 1.24 (307/248) in three places. | `intro.tex:228,353`; `aiconfigurator.tex:390-391`; `tab:sim-poly-aic` | Unify at 1.24×/+24%. |
| X9 | Two near-identical "frames/video" groupings used interchangeably: k>10 class (2.7% req / 81.2% vol) vs k-means archetype (3.4% / 85.7%). | `intro.tex:116-118`; `trace-eda.tex:78,97,223-224` | One sentence distinguishing them at first co-occurrence. |
| X10 | Burst-peak request rate 4.48 req/s is *above* the request signal's own p99 (4.35) yet called "indistinguishable from routine traffic." | `intro.tex:135-137` vs `tab:eda-percentiles` | Soften ("unremarkable in level"; the rigorous statement is the Jaccard-0.02 disjointness). |
| X11 | SLA vs SLO: `SLO` is defined and used only in Ch.2 (`related.tex:19-20`); `SLA` is used 21× (intro, Ch.6) and never defined. | throughout | Define both once; use SLO for the latency objectives unless a contractual agreement is meant. |
| X12 | Composed "≈2 s p99 to first token" from two 1-s p99 budgets: the sum of two p99 thresholds is a union-bound **p98**-style guarantee, not p99. | `twopool.tex:181-184` | Say "≈2 s at p98 by union bound" or argue the correlation structure. |
| X13 | "Episode" means two different objects: Ch.3's contiguous >p99 minutes (18 episodes totaling 87 min) vs Ch.6's 8.3-h burst *window*. | `trace-eda.tex:218-219` vs `twopool.tex:189-191` | Introduce "burst window (envelope around episode E1)" terminology. |
| X14 | "Tuned classical baselines" contradicts the protocol's "configured conventionally" fixed constants. | `predictors.tex:289` vs `:63-67` | Delete "tuned" (or actually tune them). |

---

## 7. Chapter-by-chapter notes

**Ch.1 Introduction.** Excellent architecture (context → gap → statement → RQs → approach
→ contributions → scope), but it restates nearly every quantitative result in the thesis
in very long sentences (`intro.tex:44-49`, `:160-163`), duplicating the chapters and the
summaries. State each result once with its number. Blocking items: B2–B5.

**Ch.2 Related Work.** The strongest chapter — current, comprehensive, honestly
positioned. Two fixes: the positioning table names "HeteroScale" (`related.tex:331`) while
the text never introduces that name (`:167-169` describes `Li2025TamingChaos` without it);
and decide a single convention for grey literature (the vLLM/LMSYS blog posts live in a
footnote, `related.tex:85-90`, everything else in the bibliography).

**Ch.3 Trace EDA.** Rich, mostly rigorous; the decoupling (R²=0.123 vs 0.654), burst
anatomy, and Jaccard-0.02 disjointness are compelling. Repair E1/E2, reconcile X6/X9/X10,
report silhouette values (E8). The multiresolution analysis (`trace-eda.tex:296-343`) is
excellent and under-sold — it is the quantitative case against averaged dashboards.

**Ch.4 Predictors.** Clean protocol and honest about the shot-noise floor and the
covariate null result (which is a genuinely nice negative finding echoing the decoupling).
The problems are design-level: E3–E8. Note the forecast-band figure honestly shows naive
riding the plateau nearly as well as the FMs — consistent with E3's message that the
FM edge at 1-min is modest and lives at regime *edges*, which is exactly what E5's
event-based metric would capture.

**Ch.5 AIConfigurator.** Careful, honest systems work: the clock-locking discovery
(~17%), the SOL-fallback finding (~5.9×), the term-by-term ledger, and the recorded infill
correction are all genuinely valuable — the two ecosystem findings deserve their
prominence. Fix H5, X1, X2, X7. Two structural notes: the chapter has **zero figures**
despite being the most number-dense (an f(N) measured-vs-composed curve and a stacked
kernel-ledger bar would carry §5.3–5.4 at a glance); and §5.5 duplicates Ch.6 content
(the calibrated-vs-polynomial deltas appear in both, `aiconfigurator.tex:388-393` vs
`twopool.tex:56-63` + table) — trim §5.5 to a forward pointer.

**Ch.6 Two-Pool Simulation.** The saturation-inversion result is the best single result in
the current draft — which is why H1–H4 matter so much: they are all repairs to *this*
chapter's headline. Also: the chunk-parallel dispatch policy is a strong modeling choice
(one request's chunks spread over all free workers, transfer not charged to the worker,
`twopool.tex:130-159`) that directly produces "capacity-controllable" tails; you retain
the sequential alternative behind a flag — report both curves once, in an appendix if need
be, so the policy's effect on the headline is quantified rather than asserted.

---

## 8. Presentation and writing

- **W1. [Major] Sentence length and density.** Many sentences run 4–6 typeset lines with
  stacked em-dash clauses (`intro.tex:44-49`, `:159-163`; `twopool.tex:130-149` is one
  ~20-line paragraph-sentence chain). Split; one claim per sentence; cap em-dash pairs.
- **W2. [Minor] Editorializing voice.** "real forecast capital" (`predictors.tex:141-142`),
  "essentially free" (`predictors.tex:169`), "the honest reading brackets reality"
  (`aiconfigurator.tex:255`), "and the headline:" (`intro.tex:353`). Keep the confidence,
  drop the blog idiom.
- **W3. [Minor] Captions argue beyond their figures.** Several captions carry thesis-level
  conclusions ("…which is what makes reactive scaling insufficient and forecasting
  necessary," `trace-eda.tex:253-255`; similar at `:151-153`, `:277-279`). Captions should
  describe; let the body argue. (And one caption is factually contradicted by its figure —
  E6.)
- **W4. [Minor] Redundancy.** The core narrative is restated in intro, RQs, contributions,
  positioning, and every chapter intro+summary; §5.5 vs Ch.6 duplicates results. One
  tightening pass.

---

## 9. Bibliography and citations

- **R1. [Major] Manual `thebibliography`.** 57 hand-formatted entries in the root file
  (`tese.tex:36-316`), self-described as a stopgap ("Minimal bibliography so the build
  resolves \cite without biber," `tese.tex:35`). Move to biblatex/BibTeX now — entries are
  already inconsistent (page numbers and volumes sporadic; no DOIs; venue styles vary).
- **R2. [Major] Verify venues/years; mark preprints.** Several entries pair an arXiv ID
  with a future or unverified venue (`WarmServe2025` → "ICML, 2026"; `Xiang2025ServeGen` →
  "NSDI, 2026"; `vLLMOmni2026`, `Yu2026HeteroServe`, `Cho2026LLMServingSim2` appear
  arXiv-only). Distinguish published / to-appear / preprint explicitly; key years also
  disagree with venue years (`Wang2024BurstGPT` → "KDD, 2025") — a symptom of hasty
  assembly that an examiner will probe.
- **R3. [Minor] Incomplete author lists** ("Y. Wang, et al.", `tese.tex:200`;
  `Xiang2025Aegaeon`, `Zhang2025BlitzScale`) — expand; "et al." in a thesis bibliography
  is poor form. Drop the promotional "(Best Paper)" from `Qin2025Mooncake`
  (`tese.tex:85`).
- **R4. [Minor] Dataset citation malformed.** `AzureLMM2025` uses the dataset filename as
  its title (`tese.tex:232-235`); cite as a dataset (publisher, name, repository, year,
  accessed/commit).

---

## 10. LaTeX / build hygiene

- **L1. [Minor] Generic `book` class** (`tese.tex:4`). If an institutional template
  (abnTeX2 or departmental class) is required, switch *before* writing the remaining
  chapters — it supplies the front matter of §2 and late migration is painful.
- **L2. [Minor] A handful of under/overfull boxes** (notably the URL footnote in
  `related.tex:85-90`). Clean before final; `\url{}` with a proper package will fix the
  footnote.
- **L3. [Good — keep.]** The per-file `%!TeX root` headers, provenance comments, and
  figure-generation notes are genuinely useful; retain them through the final build.

---

## 11. Changes from v1 of this review (verification log)

Dropped or corrected after re-verification — these were not legitimate as stated:

1. *Hyphenation inconsistency* ("cold start" vs "cold-start", "request rate" vs
   "request-rate") — **dropped**: the cited variants are grammatically correct
   (noun vs compound modifier). Replaced by the verified SLA/SLO defect (X11).
2. *`\graphicspath` fragility* — **dropped** as trivial/non-issue.
3. *"The caption \[of `tab:sim-knees`\] clarifies the metric"* — **corrected**: the caption
   does **not** clarify; the mislabel is worse than v1 stated (X3).
4. *"The chapter title says 'for provisioning'"* (Ch.4) — **corrected**: that phrase is a
   related-work section title, not the chapter title; replaced with the accurate version
   of the point (autoscaler-framed questions scored by generic metrics → E3/E5).
5. *"RQ3 reads as if both pools are validated"* — **softened**: RQ3's wording is careful;
   the real issue is the missing statement in Ch.6's limitations plus the burst-verdict
   timing gap (H6, H1).
6. *"60–80× the compute"* — **reframed**: those are benchmark wall-clock figures, not
   per-decision costs; the fair statement is deployment-footprint asymmetry (E3).

Major additions in v2, all source-verified: H1 (missing calibrated burst run — confirmed
in both table and figure legend), H2 (octave grid → ">8×" is the provable bound), H3
(196-vs-66 same-tensor contradiction + aligned-bias analysis), H4 (image-lean steady
window; single-window knees), E4.1 (common-span coverage asymmetry 20% vs 98.7%), E4.3
("tuned" is false), E3 (WAPE≥100% no-skill floor), E5 (no onset-event evaluation), E6
(band figure contradicts caption; uncalibrated p90 rule), E7 (contamination caveat), C3
(newsvendor framing), C6 (count-vs-content), X4–X6, X10–X14.

---

## 12. Prioritized checklist

**Blockers (before any submission):**
1. Abstract/resumo + keywords; real title page and front matter (B1, B2, B6, L1).
2. Complete the thesis statement (`intro.tex:190`) and resolve all placeholders (B3, B5).
3. Deliver the closed-loop + conclusion chapters; until then, label Chapters 3–6 as
   platform (B4).

**Protect the headline result (highest technical priority):**
4. Run the burst window under AIC timing; restate the inversion accordingly (H1).
5. Refine or reword "≥16×" to match the sweep grid's resolution (H2).
6. Reconcile per-request token accounting (196 vs 66 vs 448² conventions) and add the
   directional-bias analysis (H3).
7. Re-run knees on additional windows/episodes; report ranges (H4).
8. Re-scope the "3%" claim; measure one production-vLLM forward or flag the assumption
   (H5); state the pool-fidelity asymmetry in Ch.6 limitations (H6).

**Strengthen the evidence base:**
9. Repair the persistence-gradient/estimator claims; quarantine decode statistics (E1, E2).
10. Fix the forecasting evaluation: aligned evaluation window across resolutions;
    full-history + seasonal + ARIMA baselines; delete "tuned"; add CIs/DM tests
    (E4, X14).
11. Add the burst-onset detection-delay evaluation (E5) and empirical quantile coverage;
    fix the band figure caption (E6).
12. Size the FM-vs-EWMA claim honestly at 1-min; flag the WAPE-100% floor at 1 s (E3).

**Closed-loop design (before running it):**
13. Reactive baseline on the *right* signal; adversarial episodes; SLA×GPU-hours as the
    headline metric (C2); derive headroom quantile via the newsvendor fractile (C3).

**Polish:**
14. Fix X1–X13; bibliography to biblatex with verified venues (R1–R4); prose pass
    (W1–W4); Ch.5 figures; contamination sentence (E7); SLA grounding (C5).

---

### Closing note
The re-review reinforced v1's overall verdict: the scholarship, honesty, and
reproducibility here are well above bar, and the numeric spine is largely sound — most
cross-chapter numbers check out exactly. The two most consequential findings of this pass
(H1, H2) are not signs of sloppiness; they are the two places where the draft's rhetoric
ran one step ahead of the runs that exist. Both are fixable within days: one calibrated
burst run, one finer sweep or one reworded sentence. Do those before anything else — the
thesis's single most quotable sentence ("the pools saturate ≥16× apart and in opposite
order inside the burst") currently rests on them.
