# Thesis Review: Improvement Points

**Date:** 2026-07-08
**Scope:** `tex/tese.tex` + 6 chapter files (`intro`, `related`, `trace-eda`, `predictors`, `aiconfigurator`, `twopool`)

> **Adjudicated 2026-07-08 (same day):** every item checked and marked
> below — `[x]` done (with note), `[~]` partial/scheduled with reason,
> `[R]` rejected after checking (judgment stated). Cross-references:
> the fuller per-item log lives at the top of THESIS-FEEDBACK.md; new
> runs are ledgered in progress/results-ledger.md.

---

## 1. Structural & Organizational

### 1.1 Missing Chapters (Critical)
- [~] **Baselines chapter** — SCHEDULED: experiments complete + ledgered (grid, close-out, reactive 14-run set); chapter drafting is the next writing block. Interim mitigation applied: intro/related now state the delivered results with numbers and label chapters "in preparation" (no placeholder text remains).
- [~] **Closed-loop chapter** — SCHEDULED: 4.3 delivered (C(t) matrix, lead sweep, LLM closed loop); RQ4 + Contribution 5 now carry the real results. Chapter drafting queued behind the 4.4 fleet aggregate (the headline number).
- [~] **Conclusion chapter** — queued with the above (needs the aggregate to conclude on).
- [~] **Validation chapter** — Phase 5.1 remains scheduled work; the one surviving `[Placeholder]` in intro marks exactly this.
- **Impact:** acknowledged; the "payoff" numbers are now *stated* in intro (statement, RQ4, contribution 5) from archived experiments, so the argument is no longer headless while the chapters are written.

### 1.2 Title Page
- [x] Real working title set: *Predictive Per-Pool Provisioning for Modality-Disaggregated Multimodal Model Serving* (institutional template/PT title page deferred, noted in source).

### 1.3 Front Matter
- [x] Abstract written (~290 words) + Portuguese resumo.
- [~] List of abbreviations added (19 entries). Acknowledgments/dedication deliberately left for the author.
- [x] `\listoffigures` + `\listoftables` added (with `\frontmatter`/`\mainmatter` page numbering).

### 1.4 Chapter Ordering & Flow
- [x] Bridge exists: Ch.4 summary ends by handing forecasts to the autoscaling experiments; Ch.5 now closes §5.5 with an explicit forward pointer instead of duplicated results.
- [R] `\part{}` headers — rejected for now: part-numbering churn is better taken together with the institutional template switch.

### 1.5 Appendix Material
- [~] A reproducibility appendix was added (environment + artifact manifest — the higher-value appendix). Moving Table 3.5/kernel ledger out of the chapters was **rejected**: both are load-bearing cross-reference targets (Table 3.5 anchors six quoted percentiles; the ledger carries the attribution claim), and the new f(N)+ledger figure already summarizes the latter visually.

---

## 2. Writing & Prose

### 2.1 Strengths (Preserve)
- The prose is exceptionally precise and dense with information. Every paragraph carries quantitative claims.
- Cross-referencing between chapters is thorough and deliberate.
- The "provisioning gap" narrative arc (Ch1→Ch3→Ch6) is compelling.

### 2.2 Density & Readability
- [~] **Intro density** — the 17-line opener was split; §1.2 subsections **rejected** (three paragraphs would fragment into stubs); the summary figure was **done** (Fig. 1.1, TikZ architecture diagram with the four signals).
- [~] **Long sentences** — worst offenders split (intro opener, results ¶, Ch.6 knee prose rewritten); a global pass is deferred to final copy-edit, after the factual layer (per report.md's own rewrite order).

### 2.3 Placeholder Hygiene
- [x] 8 of 9 markers resolved with content from archived experiments; the one survivor (validation anchors) is intentional and tracked in the roadmap.
- [x] Thesis-statement placeholder resolved first, as demanded — the operative clause now states the closed-loop claim outright.

### 2.4 Consistency
- [x] *aiconfigurator* italicized at first use per chapter, "AIC" thereafter (spot-checked all three chapters that use it).
- [x] Naming defined once in Ch.6: "the mocker (marketed as DynoSim)"; `dynamo.replay` reserved for the CLI entry point.
- [R] CV² — checked: consistently `CV$^2$` throughout; no defect found.
- [R] "frames class"/"frames-class" — rejected (grammatical: noun vs compound modifier); THESIS-FEEDBACK v2 dropped this same item on the same grounds.

---

## 3. Technical Content

### 3.1 Introduction (Ch1)
- [x] **Architecture diagram** — done (Fig. 1.1: trace → vision pool → seam → language pool, forecaster on top, four signals labeled).
- [x] **Contribution 5** — resolved the other way: kept as a contribution and filled with the delivered results (588 ms vs ≥38 s lead sweep, 0.1× static worker-seconds, 14/14 mean-law diagnostic), labeled "chapters in preparation".
- [~] Validation anchors — remains the one intentional placeholder (Phase 5.1).

### 3.2 Related Work (Ch2)
- [x] LLMServingSim 2.0 added to the positioning table (shared row with Vidur) + pointer sentence in §2.6.
- [x] Zero-shot rationale made explicit in §2.5 ("a per-pool system multiplies the signals to forecast; pretrained models remove the per-signal fitting burden").
- [x] Kubernetes-native autoscalers (HPA, KEDA, Knative KPA) named, characterized, and cited at the top of §2.3.

### 3.3 Trace EDA (Ch3)
- [x] Vision-/text-borne rows explained in the table caption (modality split of the context series; spectral-only; exists to show persistence is vision-inherited).
- [x] §3.6 operational implication — already present ("understates the encoder pool's surges by roughly 25×"); caption also states it. Marked done on verification.
- [x] Hill estimator + top-percentile threshold + no-GoF-claim sentence added.
- [x] `[htb]` → `[htbp]` across all chapter files.

### 3.4 Predictors (Ch4)
- [R] Promoting the covariate table to Ch1/Ch3 — rejected: it answers a forecasting question and is cross-referenced from the decoupling discussion; moving it would orphan §4.3.
- [x] Forecast latency/cost paragraph added (≈65–90 ms per 12-step forecast vs 15–60 s cadence; deployment-footprint asymmetry stated honestly).
- [R] Dedicated subsection for "band is headroom" — the conclusion closes its own titled section (§4.4) and now also heads the new calibration paragraph; a further subsection would duplicate headings.
- [x] Multi-model comparison figure added (all three TSFMs on the largest burst — near-coincident paths).

### 3.5 AIC / Vision Pool (Ch5)
- [x] Summary re-scoped: operator-level ≈3% vs composed 1.4–1.6× band distinguished everywhere the 3% is quoted (intro, RQ3, contribution, summary).
- [R] Moving infill details to an appendix — rejected: the correction narrative is a methodological contribution (recorded correction), and the reviewer of THESIS-FEEDBACK explicitly credits it; kept in place, tightened by the raw/infilled labels.
- [x] $f(N)$ figure added (composed vs measured, ratios annotated, + kernel-ledger bars).

### 3.6 Two-Pool Simulation (Ch6)
- [~] Chunk-parallel dispatch — kept as a paragraph (chapter balance) but strengthened: policy-assumption label, runtime grounding, and the sequential alternative's quantified 2.9 s floor. Subsection+diagram deferred.
- [x] "Censored" explained in the caption ("the bound was never crossed within the swept range, s ≤ 32").
- [R] Callout box for Fig 6.2 — rejected as a class-level styling change; the figure keeps full linewidth and its mechanism paragraph directly precedes it.
- [x] Worker-count sensitivity stated with real numbers (grid forward-pointer: burst windows need 6–16 encoders at trace rate vs 2 steady; TP1 floor persists 4→16 workers).

---

## 4. Bibliography & Citations

### 4.1 Manual Bibliography
- [~] DEFERRED (documented decision): biblatex migration postponed to ride with the institutional-template switch, which dictates the citation style — doing it twice churns every entry. Concrete defects fixed in place meanwhile: dataset entry rewritten, "(to appear)" markers, "(Best Paper)" dropped, URLs via `\url` with access dates. Author-list "et al." expansion needs web-verified lists → queued with the migration.
- All 2026-dated venues were web-verified 2026-07-07 (see bib-workflow memory); they are now marked "(to appear)".

### 4.2 Citation Gaps
- [x] Qwen3-VL model family cited (model cards/configs entry; fields verified against HF 2026-07-08).
- [x] FlashAttention-2 cited at the kernel-fidelity paragraph.
- [x] Azure trace: dataset-style entry with repository, release context, access date, and terms-of-use pointer.
- [x] Kubernetes HPA/KEDA/Knative cited in §2.3.

### 4.3 Self-Citation
- [~] PR #1312 now carries a durable reference (branch, campaign commit `1e8b9cac`, local infill commit `656ac8ca`, artifact snapshot pointer). A "Publications and Contributions" front-matter section is deferred to the institutional template (it prescribes the placement).

---

## 5. Figures & Tables

### 5.1 Missing Figures
- [x] **Architecture diagram** — done (TikZ, Fig. 1.1).
- [x] **$f(N)$ curve plot** — done (Fig. 5.1, composed vs measured with per-point ratios + kernel-ledger bars).
- [x] **Multi-model forecast comparison** — done (Fig. 4.5, three TSFMs on the largest burst).
- [x] **Conceptual overview** — same as the architecture diagram (signals → pools → C(t)/N(t)).

### 5.2 Figure Quality
- [~] PNG→vector DEFERRED: the data figures render at 200 dpi (adequate for draft review); regenerating all 13 as PDF touches the GPU-bound EDA scripts and is batched for the final build. The two new Ch.5/Ch.4 figures and the diagram: the diagram is native vector already.
- Captions: kept, with the two caption-overreach fixes from the other reviews applied.

### 5.3 Table Quality
- [x] Table 3.5 forward-referenced explicitly at first mention ("Section 3.7").
- [x] Units clarified in Table 3.5's caption (counts-per-request vs per-second rates as labeled).

---

## 6. Reproducibility & Artifacts

### 6.1 Strengths
- Every chapter states its reproducibility path (versioned scripts, archived parquets, locked clocks).
- The forecast archive and upstreamed AIC data are strong artifact contributions. *(Correction from the adjudication pass: the archive is 21,404,640 rows across 26 Parquet files — the "19.2M" figure was stale and has been fixed in the manuscript.)*

### 6.2 Gaps
- [x] Artifact appendix added (Appendix A: element→script→artifact manifest, distilled from progress/results-ledger.md).
- [x] Workspace structure described in the appendix's closing paragraph.
- [x] Consolidated software-version table (Table A.1: driver/CUDA, vLLM container, AIC, ai-dynamo wheel+source, RAPIDS, torch/transformers/chronos, matplotlib).

---

## 7. LaTeX Build & Packaging

### 7.1 Build System
- [x] `.latexmkrc` added (pdf mode, nonstop, aux handling); `.gitignore` extended for LaTeX artifacts.

### 7.2 Package Choices
- [x] `hyperref` added (hidelinks). `cleveref` **rejected** for now — it would touch every `\ref` for cosmetic gain; batched with the template switch.
- [~] biblatex — see 4.1 (deferred, documented).
- [R] `subcaption` — not needed: multi-panel figures are composed inside matplotlib/TikZ with single captions.

### 7.3 Graphics Path
- [R] Rejected as non-issue (THESIS-FEEDBACK v2 independently dropped the same item); the path is stable under the self-contained build contract.

---

## 8. Argument & Thesis Logic

### 8.1 Core Argument Chain
The argument is: (1) signals decouple → (2) the dangerous signal is forecastable → (3) the platform is calibrated → (4) the simulation reproduces decoupling → **(5) forecasting the right signal improves SLA at lower cost**. Steps 1–4 are done; step 5 is missing.

### 8.2 Threats to Validity
- [x] **Falsifiability** — added to Ch.3 limitations (a rate-carried-vision trace collapses the decoupling and the method reduces to conventional practice), plus the mechanism hypothesis that carries generality.
- [~] **Open-loop** — remains a property of this platform; the closed-loop chapter's charge (workload is still open-loop there by design — replay counterfactuals — which the chapter must state).
- [x] **Image size sensitivity** — explicit scaling added to Ch.6 limitations (per-image cost ~ patch count: 224² ≈ 4× cheaper, 672² ≈ 2.25× dearer; knees shift, queueing mechanism doesn't).

### 8.3 Novelty Claims
- The three precedence claims (first per-pool demand-signal characterization, first provisioning-framed TSFM benchmark, first consumer-GPU encoder cost model) are stated carefully with "to our knowledge." Good.
- The positioning table supports these claims well.

---

## 9. Priority Action Items

| Priority | Status | Item | Chapter |
|----------|--------|------|---------|
| **P0** | [~] scheduled | Write the closed-loop chapter (RQ4 results) — experiments done+ledgered; drafting queued behind the 4.4 aggregate | New |
| **P0** | [~] scheduled | Write the baselines chapter (static-optimal + reactive) — same | New |
| **P0** | [x] 8/9 | Resolve all placeholders (1 intentional survivor: validation anchors) | All |
| **P0** | [x] | Write a real title and abstract (+ resumo) | tese.tex |
| **P1** | [x] | Add architecture diagram to intro (TikZ Fig. 1.1) | Ch1 |
| **P1** | [x] | Add $f(N)$ curve plot (+ kernel-ledger panel) | Ch5 |
| **P1** | [x] | Add multi-model forecast comparison figure | Ch4 |
| **P1** | [~] deferred | Migrate to biblatex + .bib — batched with template switch; entry defects fixed in place | tese.tex |
| **P1** | [~] scheduled | Write conclusion chapter (needs the 4.4 aggregate) | New |
| **P2** | [x] hyperref | hyperref added; cleveref rejected (touches every \ref, batch with template) | tese.tex |
| **P2** | [~] deferred | Convert PNG figures to vector PDF (final-build batch; diagram already vector) | All |
| **P2** | [x] | Add list of figures / tables / abbreviations | tese.tex |
| **P2** | [R] | Break intro §1.2 into subsections — rejected (3-paragraph section; figure added instead) | Ch1 |
| **P2** | [x] | Standardize naming (AIC italics, mocker/DynoSim defined once) | All |
| **P3** | [x] | Add appendix: artifact inventory & reproduction guide (Appendix A) | All |
| **P3** | [R] | Appendix for kernel-time ledger — rejected: load-bearing in Ch5; new figure summarizes it | Ch5 |
| **P3** | [x] | Discuss K8s-native autoscalers in related work | Ch2 |

---

## 10. Summary Assessment

**What's here is excellent.** The four completed chapters form a rigorous, well-argued, quantitatively dense foundation. The writing quality is high, the technical work is original, and the reproducibility discipline is exemplary. The trace-EDA and two-pool chapters are publication-ready as standalone papers.

**What's missing is the payoff.** The thesis currently builds a platform and establishes premises but never closes the loop. The closed-loop chapter — where forecasts actually drive scaling decisions and are scored against baselines — is the contribution the entire document points toward. Without it, the thesis is a very strong "setup" without a "punchline."

**Estimated completion:** The P0 items (baselines + closed-loop + placeholder resolution + abstract) are the critical path. Everything else is polish.
