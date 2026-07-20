Report written to `/home/gio/tese/provenance/audit/crosschapter.md`.

# Cross-Chapter Consistency Pass

Scope: `/home/gio/tese/tex/*.tex` (13 files, 5,212 lines). All line numbers refer to those files. This pass establishes what disagrees with what; no edits proposed. Where two phrasings are equivalent, I say so explicitly rather than filing a defect.

---

## 1. Restatement consistency

### 1.1 The 0.62x cost ratio — value consistent everywhere, wording drifts

Source of truth `closedloop.tex:465-469`: 2.41M / 3.87M worker-seconds = 0.6227 → 0.62x. 19 sites, all numerically consistent: `tese.tex:67` (EN), `tese.tex:112` (PT, "0,62"), `intro.tex:50, 271, 481, 514`, `baselines.tex:98`, `closedloop.tex:242, 265, 465-469, 481, 500, 530, 630, 666`, `conclusion.tex:81, 95`, `related.tex:361`, `apendice.tex:11, 333`.

Sensitivity band **0.59–0.62x** (strict re-warm): `intro.tex:274`, `closedloop.tex:124, 446, 498, 669`, `conclusion.tex:84` — consistent, all six carry the qualifier. rho-frontier 0.89/0.62/0.48/0.40x and language-pool 0.96x also consistent.

- **[1a, Low]** `conclusion.tex:95` restates 0.62 as "roughly two-thirds" (0.667) — 14 lines after stating 0.62x at `:81`. Rounds away from the measured value.
- **[1b, Low]** `related.tex:361` and `tese.tex:67` quote 0.62x with no span or readiness-model qualifier; every other prose site carries one.

### 1.2 588 ms encoder floor — TWO VALUES IN CIRCULATION

Derivation at `closedloop.tex:452-457`: f(64)=316.4 + handoff 272 = **588.4 ms**.

- **588** at ~28 sites (`intro.tex:265, 479, 514`; `conclusion.tex:68, 101`; `twopool.tex:215`; `baselines.tex:221-227`; `closedloop.tex:80, 92, 113, 121, 142, 202, 452, 468, 469, 472, 483, 499, 523, 531, 543, 593, 627`).
- **589** at `closedloop.tex:241, 254, 265, 606, 622`; `apendice.tex:211`.

- **[1c, High]** The same "zero-queueing service floor" is 588 ms in Tab. `tab:cl-aggregate` (where it is derived) and 589 ms in Tab. `tab:cl-ewma` (`closedloop.tex:254, 265`) — same chapter, both labelled "service floor".
- **[1d, High]** The AIC baseline is quoted inconsistently within one paragraph: vLLM reprice says "606 versus **589** under AIC" (`:622`); HF-eager reprice five lines later says "784 versus **588** under AIC" (`:627`). Same AIC schedule replay. Contrast `:636-638`, where an analogous 647-vs-644 gap *is* explicitly disclosed as a harness difference.

### 1.3 734 ms calm-day bound — consistent
`baselines.tex:228` (source), `closedloop.tex:80, 115`, `intro.tex:266, 480`. The 548 lower end agrees too. No disagreement.

### 1.5 R² = 0.123 vs 0.12
0.123 at `intro.tex:146`, `trace-eda.tex:241, 482`, `related.tex:188, 335`. 0.12 at `tese.tex:51, 92`, `intro.tex:406`, `trace-eda.tex:257`, `predictors.tex:232`, `related.tex:225`, `conclusion.tex:17`.

- **[1e, Medium]** No site is wrong (0.123 → 0.12 rounds correctly), but the two roundings are mixed **inside the same chapter** three times: trace-eda (`:241`/`:482` vs `:257`), related (`:188`/`:335` vs `:225`), intro (`:146` vs `:406`). Note the asymmetry — the paired decode figure 0.654 is never rounded.

### 1.6 Coverage span — consistent
Clean two-level distinction maintained: trace extent (7 days / 1,000,000 requests) vs graded closed-loop span (5.60 days / 749,601 requests, defined at `closedloop.tex:47-53`). **No site claims closed-loop results over all 1M requests or the full 7 days.** The "full 1,000,000-request" language exists only in git history and `defense/`, not in `tex/`.
- **[1f, Low]** "covered week" / "week-scale" used for 5.60 days at `intro.tex:50`, `closedloop.tex:665` without the adjacent disambiguation that `closedloop.tex:437` provides.

### 1.7–1.10 Consistent
29% encoder utilization (8 sites, identical subject and claim); C*=8 / C*=2 and the 4x/2x derivation; WAPE headlines (98.8 / 146.1 / ~53%) match Tab. `tab:pred-wape`.

- **[1g, Medium]** Engine ratio: measured values are 1.36–1.62 (`aiconfigurator.tex:269-274`), yet the four summary sites (`intro.tex:249, 510`, `apendice.tex:194`, `conclusion.tex:106`) all say "~1.4–1.6x" — a band containing **neither** endpoint. The precise statements also disagree with each other: `apendice.tex:180` says 1.61 top-of-range, `aiconfigurator.tex:274` says 1.62.
- The **12.8%** figure is by contrast correctly scoped ("across the whole N≤64") at all eleven restatement sites. The 11.4% at `apendice.tex:186` is a narrower three-shape residual, correctly distinguished. No overclaim.

---

## 2. Scope / overclaim

**2.1 Is the live-vs-simulated band TTFT-only at source but quoted broadly? — No.** All five restatements explicitly bind 1.1–6.8% to TTFT p99: `validation.tex:97, 159`, `intro.tex:535`, `conclusion.tex:53`, `closedloop.tex:421`. Correctly scoped everywhere.

**2.2 Does any ITL pair fall outside the band? — Yes.** Forecast p90 ITL p99: live 11.5 vs offline 9.7 = **+18.56%**, well outside 1.1–6.8%. It *is* disclosed (`validation.tex:160-162`, `intro.tex:536-538`).

- **[2a, High]** The disclosed percentage is wrong: `validation.tex:161` says **18.0%**; the table's own values give **18.56%**. Against the live value it would be 15.7%. 18.0% matches neither.
- **[2b, Medium]** Band lower endpoint: reactive TTFT 3531 vs 3495 = **+1.03%**, quoted as **1.1%**. Rounds the wrong way and propagates to all five restatement sites.

**2.3** **[2c, Medium]** `twopool.tex:216-217` "within 8% at p99: 706 modelled versus 651 replayed" — that is **8.45%** against the replayed value (7.79% against the modelled). Flagged cross-chapter because a *different* "within 8%" (replica-time, `validation.tex:84`, `intro.tex:539`) circulates concurrently. **The two 8% claims are not the same claim.**

---

## 3. Denominator drift on 0.62x — none

Five phrasings: (A) "provisioned worker-time", (B) "worker-time", (C) "GPU-time", (D) PT "tempo de GPU da menor frota estática viável", (E) bare "static". **All five denote the same denominator:**

1. A≡B — source gives 3.87M worker-seconds of standing capacity; dropping "provisioned" loses a disambiguation, not the referent.
2. A/B≡C — settled explicitly at `baselines.tex:17-19`: costs are scored "with provisioned **GPU-time** per hardware class (**RTX 5090-class worker-seconds for the encoder pool**...)". Corroborated by the "5090 GPU-h" column at `:75` and the 5090-hours at `:93`. One GPU per encoder worker.
3. C≡D — "menor frota estática viável" = smallest feasible static fleet; EN "deployable static" is defined at `baselines.tex:118-119` as the single config feasible across all windows (max over per-window C* of 6–8). Same fleet; the PT is arguably clearer.
4. E≡A — pinned by the table row "Static C=8 (deployable) ... 3.87 Mworker-s ... 1.00x".

Residual risk is presentational only: the worker-time≡GPU-time equivalence is established once, in `baselines.tex:17-19`, and never restated where a reader meets `tese.tex:67` first. Readability gap, not an inconsistency.

---

## 4. Stale limitations

Verified as **not** stale: the "modelled reconstruction" language at `twopool.tex:218-219` (nothing elsewhere calls the e2e figure measured); the encoder-pool live-loop gap (`validation.tex:153` ≡ `conclusion.tex:108`); the physical-anchor gap, correctly scoped to a *live worker* at all three sites rather than to physical measurement generally; language-pool "calibrated" vs "physically validated" kept distinct; coverage (Sec. 1.6).

- **[4a, High]** `apendice_ecosystem.tex:144` attributes the `live_fc`/`live_re` runs and their aiperf exports to **`cap:closedloop`**. They belong to `cap:validation` (`validation.tex:2-4, 31`). Clearest cross-chapter defect in this pass.
- **[4b, Low]** `apendice_ecosystem.tex:166-167` "a full-serving-path run with real GPU engines behind aiperf remains future work" — aiperf is already in use, live, two paragraphs above. Intended reading recoverable; surface reading contradicted.
- **[4c, Low]** `closedloop.tex:571-575` places "the full evaluation span" and "the remaining windows are priced by the grid ... rather than replayed end-to-end" in adjacent clauses without a connective. Both true at different granularities, but the 0.62x per-episode claim depends on which windows were replayed.

---

## Severity summary

**High:** 1c, 1d (588/589 floor split across tables and within one paragraph); 2a (ITL 18.0% vs 18.56%); 4a (wrong chapter cross-ref).
**Medium:** 2c (8.45% quoted as "within 8%", plus collision with an unrelated 8%); 1g (1.4–1.6x excludes its own endpoints; 1.61 vs 1.62); 2b (1.03% quoted as 1.1%, five sites); 1e (0.123/0.12 mixed within three chapters).
**Low:** 1a, 1b, 1f, 1h, 4b, 4c.

**Checked and clean:** the 0.62x denominator across all five phrasings; the live-band TTFT scoping across all five restatements; 734/548 ms; 29% utilization; the 5.60-day vs 7-day distinction and absence of any full-1M grading claim; C*=8/2 and 4x/2x; 0.96x; 0.59–0.62x; the rho-frontier; the 12.8% N≤64 scoping at eleven sites; the "modelled reconstruction" language.