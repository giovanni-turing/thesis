# Thesis restructure & shortening plan v3 — the structural edit

Date: 2026-07-26. Successor to `thesis_shortening_report_v2.md` (2026-07-20), which
concluded: "The correct next move is a structural edit, not another pass of local
sentence trimming." Author approved this plan 2026-07-26.

Targets: **55–65 numbered main-text pages, 80–95 total PDF pages** (from 96 main / 135
total). Achieved by relocation and restructure, not evidence deletion.

## 0. Novelty-claims policy (author directive, 2026-07-26)

Claim ONE novelty: **the complete operational chain** — encoder-specific signal →
provisioning-horizon probabilistic forecast → replica schedule → episode-level
SLA/resource evaluation. Present it as one result with supporting artifacts, not five
headline novelties. `related.tex` "No ingredient is claimed as novel here" is the
anchor sentence — keep it.

Do NOT claim novelty for: modality disaggregation / independently scalable pools;
recognizing image volume as the encoder load signal; predictive or cold-start-aware
autoscaling generally; upper-quantile headroom or the forecast–reactive hybrid; TSFM
forecasting itself; a production-deployed serving system; "first to quantify
decoupling" (ModServe's prior analysis makes that risky).

Limitation that must stay explicit: forecast and reactive p99 TIE on four of five
composed windows; the measured latency advantage resides in burst3. Claim a
demonstrated failure mode and trade-off, not universal forecast superiority.

Contribution tiers: primary = the chain above; enabling/secondary = AIC calibration,
the simulator, language-pool conversion, provenance infrastructure.

## 1. Research-question restructure (the core move)

Current RQ3 ("Can the system be simulated defensibly enough?") is a methodological
soundness question, not a research question. Remove it as an RQ; present AIC
calibration, simulator fidelity, and the live anchor as **methodology supporting all
RQs**. New RQ set:

- **RQ1 — Demand adequacy:** How strongly does request rate misrepresent
  vision-encoder demand, and what forecastable structure remains? (Evidence: trace
  EDA.)
- **RQ2 — Operational forecastability:** Can encoder demand be forecast with usable
  uncertainty at replica-startup horizons? (Evidence: predictors chapter.)
- **RQ3 — Control payoff** (absorbs old RQ4): Does forecast-driven vision
  provisioning improve the episode-level tail-SLA/resource trade-off over matched
  reactive and static controls? (Evidence: baselines + closed loop. Answer framing:
  demonstrated failure mode + trade-off — fc/reactive p99 tie on 4/5 composed
  windows, the latency edge lives in burst3 — never universal superiority.)

Consequences:
- The RQ list in the introduction states **questions only** — no answers, no result
  previews.
- Language-pool conversion becomes a **secondary result** inside the RQ3 chapter —
  demoted, not erased: keep exactly one abstract clause for it. This is synergistic
  with the 2026-07-26 adversarial-review remediation (the language results carry
  post-hoc / zero-startup labels; secondary status is where the corrected evidence
  puts them).
- Removing validation-as-RQ also disarms the defense-qa attack line "your live
  anchor is attached to everything except the contribution" — methodology claims
  less than an RQ does.

## 2. Chapter mapping and page budgets

| New | From (current) | Pages now → target |
|---|---|---|
| 1 Introdução (RQs, contributions, map) | ch1 | 10 → 6 |
| 2 Related Work | ch2 | 8 → 5 |
| 3 Methodology & Platform (trace, AIC cost model, two-pool simulator + fidelity, live anchor) | ch5 + ch6 + ch9 | 26 → 13 |
| 4 RQ1: Demand adequacy (EDA) | ch3 | 12 → 9 |
| 5 RQ2: Forecastability | ch4 | 10 → 7 |
| 6 RQ3: Control payoff (baselines merged in; language conversion as secondary section) | ch7 + ch8 | 26 → 16 |
| 7 Conclusões | ch10 | 4 → 3 |
| A Reproduction manifest (thin pointer table) | app A | 39 → 3–4 |

Main text ≈ 59 pp; with front matter (short captions → lists ~10 pp → ~3 pp) and thin
appendix, total ≈ 80–85 pp.

## 3. Overflow structure — supplementary artifacts

Everything displaced moves to a **supplementary material archive** (repo, pinned
commit hash; electronic appendix per USP norms), indexed from the thin Appendix A:

- S1 complete results ledger (`progress/results-ledger.md`, frozen copy)
- S2 complete forecasting grid (all models × signals × horizons × quantiles)
- S3 full provenance manifest + `SCHEMA_GUIDE.md` + schema migrations
- S4 kernel-collection history (phaseB–E collector artifacts)
- S5 audit trail: adversarial reviews + `verification/adversarial_review_resolution.md`

The in-thesis Appendix A keeps: one pointer row per figure/table (script + artifact +
run_id), the reproduction quickstart, and the supplementary index. This preserves the
adversarial review's Finding-4 requirement (the mapping must exist in the document)
while the depth lives in S3.

## 4. Editorial rules

- **One canonical presentation per headline and per limitation** — state once (in the
  RQ3 chapter for economics; in methodology for fidelity caveats), reference
  elsewhere. No nested restatements.
- Chapter summaries → one-paragraph transitions.
- Short list captions: `\caption[short]{long}` everywhere.
- Blank pages: per institutional template (decided in Phase 4, not ad hoc).
- Draft note (D1) removed **only** in Phase 4 with template application.

## 5. Preservation contract (non-negotiable)

Every agent in the restructure campaign carries
`verification/adversarial_review_resolution.md` (34 items) as a checklist: **every
corrected claim must survive the move verbatim in meaning** — post-hoc labels,
plateau-not-floor, zero-startup baseline label, matched-origin ARIMA framing, onset
6.5 min, dispatch-cap vs frames-class, census wording, etc. Compression must never
reintroduce a retracted claim. The "Claims that survived" list (review §survived) must
also not be weakened.

## 6. Guard maintenance

Dedup to canonical presentations will trip sites-count guards in
`provenance/verify_all.sh` (e.g. the 0.965× floor, re-set to ≥2 on 2026-07-26). Each
dedup that reduces a guarded count gets an **adjudicated guard update with a dated
comment** — never a blind loosening, never left red. The artifact-read derived-value
gates (0.62/0.76/0.82) are count-independent and must stay green throughout.

## 7. Phases

- **Phase 0** (in flight): 34-finding remediation campaign lands; resolution doc +
  regression sweep reviewed.
- **Phase 1:** commit the corrected full-length manuscript as the rollback baseline.
- **Phase 2:** restructure campaign — skeleton first (chapter order, RQ rewrite,
  methodology merge, baselines merge), then per-chapter compression agents, appendix
  relocation, short-caption pass. File-partitioned agents; no two agents share a file.
- **Phase 3:** verification wave on the shortened build — full gates with adjudicated
  guard re-floors + fresh adversarial pass against the preservation contract.
- **Phase 4:** institutional template (ABNT/IME front matter, biblatex), draft-note
  removal, blank-page policy, Lists check, **defense-deck sync** (renumbering breaks
  deck references: defense-qa.tex, slides.tex, reveal deck).

## 8. Additional author directives (2026-07-26, second batch)

### 8.1 Mechanism vocabulary (mandatory, thesis-wide + deck)
- **burst4 = forecast anticipation** (genuine lead).
- **burst3 = better placement of standing probabilistic headroom** — NOT anticipation:
  the p90 band already held ~21 workers pre-spike; no usable lead (defense-qa ~1738
  already draws this distinction).
- **Week result = SLA/resource trade-off.**
- Prefer "forecast-informed capacity placement under startup delay" over
  "anticipatory scaling" everywhere.

### 8.2 The decisive baseline experiment (top experimental priority)
Under identical mechanics, single frozen protocol: (1) forecast policy; (2)
same-image-signal reactive; (3) reactive + calibrated minimum warm floor; (4)
deployable static fleet; (5) optional perfect-future oracle. Freeze all parameters on
the calibration split (burst2/burst6 era), evaluate ONCE on later data. Output:
worker-time vs worst-episode p99 (and failed-episode count) frontier plot. Question it
answers: does forecasting improve the achievable frontier, or was reactive merely
denied standing capacity? (Warm-floor gap acknowledged at defense-qa ~1756.)

### 8.3 Evaluation contract (freeze per RQ before Phase-2 prose)
For each RQ define: population + independent unit; primary endpoint; comparator;
success criterion; denominator and scope. Lives at the top of each RQ chapter.

### 8.4 Reusable systems rule (conclusion upgrade)
Mechanism diagram relating: startup lead vs burst-onset time; peak demand vs standing
capacity; aggregate↔encoder signal coupling; forecast uncertainty vs warm-capacity
cost. Distinguish regimes: forecasting helps / warm floor suffices / nothing responds
in time. General principle without pretending external validation.

### 8.5 Evidential units
Days/episodes are the units — not requests, rolling origins, or factorial cells.
"60/60 configurations" = parameter robustness, never sample size. Prefer day/burst
block intervals or leave-one-episode-out where feasible. Forecast evaluation
prioritizes downstream quantities (under-provision probability, burst-time quantile
coverage, worker-count regret) over WAPE rankings.

### 8.6 Cost language
We measure provisioned worker/GPU time — say "resource-time reduction". Never merge
RTX and H100 time into one economic number without the explicit conversion model
(gpus.io price snapshot); keep dollar framing as a labeled sensitivity, not headline.

### 8.7 Title (APPROVED 2026-07-26 — apply in Phase 2)
New title: "Forecast-Informed Vision-Pool Provisioning for Modality-Disaggregated
Multimodal Serving" — replaces "Predictive Per-Pool Provisioning" (overstates
symmetry). Apply in tese.tex (title page + PT translation, PDF metadata) during the
Phase-2 skeleton; propagate to defense deck, slides, defense-qa, and any running
headers in Phase 4's deck-sync pass.

### 8.8 Second-experiment queue (after 8.2)
1. Independent reproduction test: three headline results from a clean checkout +
   thin appendix only.
2. One burst replayed through REAL encoder workers (RTX 5090) — closes the
   "vision controller only simulated / live anchor uses mocked engines" gap.

## 9. Risks

- Merging chapters breaks `\label`/`\ref` graphs → Phase 3 gate: 0 undefined refs.
- PT/EN abstract divergence during rewrite → verifier checks both.
- Page-budget misses: budgets above are envelopes; evidence completeness wins over
  page count when they conflict (per v2's finding that compact evidence tables add
  text back).
