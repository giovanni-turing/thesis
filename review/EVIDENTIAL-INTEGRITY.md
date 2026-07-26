# Evidential-Integrity Assessment — FINAL (chair synthesis)

*Phase-7 trialogue: fable-5 (proposer) → gpt-5.6-sol (critic) → opus (chair). This is the
chair's reconciled verdict. It adopts the critic's narrower framing where the proposer was
too reassuring, and keeps the proposer's structure and its correct integrity observations.
Every number traces to the provenance DB (read-only) via the Phase 1–6 verification record.*

---

## Bottom line

The thesis's data-verifiable claims **hold up well against the provenance database**, but the
audit is a text↔database consistency check, **not** a proof that the experiments match reality,
and the headline economics carry accounting and scope conditions that must be stated in the text
before the result is defensible. The correct verdict is **conditionally defensible** (see end),
not "sound, no rework."

**What was measured.** 227 data-verifiable claims (164 numeric + 63 comparative), anchor-verified
against the frozen thesis, each checked against the provenance DB by paired CONFIRM/REFUTE
reviewers, adjudicated on disagreement, and — for all 91 flagged/split claims — re-derived from
raw DB operands by an independent opus arbiter. 18 figures were viewed and cross-checked. minimax
(a third lab) independently corroborated 8/10 confirmed defects (0 overturns; 2 no-data).

| status | n | reading |
|---|---|---|
| PASS | 179 | matches DB at the correct scope |
| PASS-UNVER | 26 | supported where checkable, else no backing |
| UNVERIFIABLE | 12 | causal / no DB backing / no current row |
| **FAIL** | **10** | real defect, fix drafted in FAILURES.md |

205/227 reconcile with the DB; 10 are defective; **none of the 10 reverses a chapter-level
conclusion.** The trace-EDA foundation is 14/14 clean.

> **Caveat the proposer underplayed (critic, upheld):** 205/227 is a **coverage count, not a
> confidence probability.** The 227 claims are not independent statistical units — the headline is
> restated across ~8 claims, inflating both the clean tally and the apparent corroboration — and
> inventory *completeness* was not established (a missed hard claim would bias the rate upward).
> Read 90% as "of the claims we extracted and could check, 90% reconcile," nothing stronger.

## The 88% reviewer false-positive rate — what it does and doesn't show

The fast pass flagged 85; opus re-derivation overturned 75 as reviewer artifacts (wrong view,
wrong scope, superseded rows), confirming 10. Two readings, both partly true, with the critic's
correction applied:

- **Reassuring:** a fabricated/sloppy thesis fails the opposite way — flags that *survive*
  re-derivation. Here the thesis won 75 of 85 disputes on recomputation from raw operands. This
  also validates derivation-first checking over transcription matching.
- **Uncomfortable, but bounded:** the claims are **underdetermined by the text** — checking one
  needs tacit knowledge (which view, which experiment family, which actuation convention, which
  denominator, `is_current`). The proposer inferred from this that "a human examiner has
  essentially no chance"; that overreaches — it is speculation about human performance from weak
  automated reviewers. The supportable claim is narrower: **the schema and the textual provenance
  are insufficiently explicit**, and the 88% partly measures the fast models' weakness, not only
  the schema's difficulty.
- **Mitigation (both agree):** the claim→view→predicate ledger produced by this audit *is* the
  missing sentence→query map. Archiving it as a reproducibility appendix converts "hard to check"
  into "mechanically checkable" — a genuine strength, and the honest answer to the concern.

## The 10 defects — triage by what is at stake

**Tier 1 — corrects a stated result (2 claims, one underlying fact).** `baselines-0364` +
`closedloop-0395`: burst4 (60-min onset) *passes* at L=165s (encoder-delay p99 = 904.739 ms <
1000 ms, `is_violation=false`). So medium-onset L\* is **45–165s (2 of 3 windows at 45s)**, not
uniformly 45s. This weakens the "reactive scaling is categorically inadequate because pods can't
deliver sub-minute leads" argument to "inadequate for 2 of 3 medium windows and all fast onsets."
The conclusion survives (reactive still loses burst3 at every lead and burst5 beyond 45s; forecast
still dominates on cost), but the sentence is genuinely less sharp. **The correction favors the
baseline** — an honest boundary slip (9.5% margin), not motivated rounding.

**Tier 2 — wrong magnitude/attribution, structure survives (3).** `twopool-0025` (ITL p99
87.7→86.2 ms; "~2× throughout" → 1.9× mean at trace rate, 1.2–3.9× across sweep; knee-halving
structure verified by all adjudicators); `predictors-0173` (coarse-bin winner is TimesFM@45s /
Toto@1min, not Chronos; fine-bin half and the foundation>classical conclusion hold);
`predictors-0176` (holds at 1min, fails at 15s where ARIMA/Prophet beat classical — needs
resolution scoping; "none beats the best foundation model" survives at both).

**Tier 3 — scope/wording precision (4).** `twopool-0062`, `twopool-0068`, `intro-0197`,
`closedloop-0425`. All are universal quantifiers ("throughout", "both fabrics", "barely moves",
"lead-invariant") attached to results that hold only at one scope. On `closedloop-0425` the critic
is right that the defect is really **the absence of a declared operational tolerance**, not the
adjective per se — a systematic ~6–7% endpoint decline should be disclosed with its tolerance.

**Recurrence — a diagnosis, held to its evidence.** `0364/0395` demonstrably duplicate one stale
fact across chapters; `0382` is a superseded data-vintage row. The proposer's "prose does not
re-derive" is a *plausible* common mechanism, not proven from two instances (critic, upheld) — but
it is actionable regardless: **sweep every restatement of L\*=45 (abstract, conclusion, slides)**,
since regenerated tables/figures re-derive and prose restatements do not.

**Direction of error (integrity signal).** None of the 10 inflates the headline economics; the two
Tier-1 corrections make a *baseline* look better; several Tier-3 corrections are neutral or
favorable. The defect profile is the signature of **over-compressed prose, not result-shopping.**

## The 12 unverifiable claims

- **~9 honestly scoped or corroborated by an adjacent passing claim** — mechanism claims,
  architecture facts checkable against configs (not run data), and near-duplicates of claims that
  passed (e.g. `aiconfigurator-0251/0252`). *(The proposer's §4 sub-counts were internally
  inconsistent — it named 2 of a stated 3 "setup" claims; the correct split is ~9 benign + 3
  residue, not 6+3+3.)*
- **3 should-be-derivable numbers with no current backing row — the real residue:**
  - `aiconfigurator-0264` — "11.360 ± 0.006 ms" for 448²: not independent of FAIL `0382` (same
    table, same superseded AIC vintage). Critic's DB check: **no valid FA2/N=32 cell, and no valid
    N=1 ci95 as small as ±0.006 ms.** Treat as part of the 0382 fix.
  - `closedloop-0436` — the exact "Chronos p90, ρ=15, L=30s, 0.62× over 5.60 days"
    parameterization. Critic's DB check on `v_cost_ratio` (deployable_static_c8, 0.58–0.65)
    returned six near-0.62 rows but **no exact Chronos-p90/ρ15/L30/5.60-day row.** The headline is
    corroborated seven other ways; its single most operationally specific sentence is not
    re-derivable. Backfill the row or repoint the sentence.
  - `closedloop-0439` — request-scaled language-week counterfactual (503.7 GPU-h, 1.03×), floats
    free of the DB.

## Residual risk — what this audit did NOT cover

1. **The ~240 non-data claims** (methodology, design rationale, related-work, generalization) were
   not audited. The 90% applies only to the data-verifiable half.
2. **The oracle itself.** `apendice-0138` proves the DB can be wrong (thesis 232.0 correct; DB
   ingested a contended-invalid row). The audit checks text↔DB, **not experiment↔reality**: nothing
   here re-ran a simulation or re-measured silicon. The meta-risk is a silent PASS where thesis and
   DB inherit the *same* contaminated upstream artifact. A loader validity-flag audit (+ the 2
   known claim-inventory `expected_backing` mislabels) is cheap and should be done.
3. **Warm-up cost accounting (critic, first-order — the proposer missed this).** `v_pool_cost`
   separates `provisioned_worker_seconds` from `warmup_worker_seconds` /
   `total_from_order_worker_seconds`; current reactive rows show **warm-up fractions up to 0.3456.**
   The 0.62× headline must state explicitly whether startup resource consumption is excluded
   **symmetrically** across the forecast and static arms, and why provisioned time is the right
   economic metric. This is a genuine accounting boundary, not hygiene.
4. **Simulation-to-system gap (critic).** Repricing with measured vLLM latency (`closedloop-0457`)
   is **not** the same as validating forecast execution, queue dynamics, worker startup, handoff,
   or failures on a live deployment. This deserves first-order acknowledgement, not a limitations
   footnote.
5. **Handoff / fabric is a boundary condition, not hygiene (critic).** If the headline requires
   embedding-only transfer or a sufficiently fast fabric, that condition belongs **beside** the
   headline, not only in limitations.
6. **Single-trace generality (critic sharpens).** More than ordinary external validity: model
   selection, burst taxonomy, calibration, and the cost savings are all chosen *and* evaluated
   within one Azure trace week — one week cannot establish robustness to workload drift or
   alternative modality mixes. The thesis discloses the single-trace scope (closedloop.tex:881);
   the answer at defense must stay strictly inside it.
7. **Figures.** 15/18 fully reconcile; 2 of the 3 flags are caption cosmetics.
   `pred_framework_diff` panel (a) is **not cosmetic** — its bars come from an untracked source and
   flip the naive-vs-Holt-Winters ranking relative to both the DB and the thesis's own heatmap. It
   is the one displayed-data↔DB provenance mismatch in the document; track the source or regenerate.
   Panels (b)/(c), which carry the closed-loop claim, match exactly.
8. **No displayed formulas.** WAPE, cost ratio, coverage, and infraction are defined only inline/
   prose. Defensible stylistically, but several of the 10 defects are *scope-attachment* failures
   (which denominator/window/actuation) — displayed definitions with explicit denominators are the
   standard prophylactic and would cut off the thesis's dominant failure mode for half a page.

## Verdict (chair)

I decline the proposer's "empirical evidence is sound / no deeper rework required" as too
reassuring, and I decline any call for wholesale reconstruction as unsupported — **no chapter-level
conclusion was shown false.** I sign the critic's narrower verdict:

> **Conditionally defensible** — after (1) correcting the 10 recorded defects (sentence-level fixes
> already drafted in FAILURES.md, none requiring a new experiment or figure); (2) resolving or
> withdrawing the 3 unsupported measured-looking numbers (`0264` with `0382`; backfill/repoint
> `0436`, `0439`); (3) repairing the `pred_framework_diff` panel-(a) displayed-data provenance
> mismatch and the two caption flags, and running a DB-loader validity audit; and (4) **explicitly
> scoping the 0.62× headline as a simulation-derived, single-trace, infrastructure-conditional
> finding with a stated cost-accounting boundary** (provisioned vs from-order worker-seconds,
> symmetric warm-up treatment).

**Strongly recommended, non-blocking:** displayed definitions for cost ratio (with denominator),
L\*, and the infraction rule; and archive the claim→query ledger as a reproducibility appendix —
it turns the §2 "underdetermined by text" weakness into the defense's most distinctive strength.

**What is absent from the record** (and would have forced a harsher verdict): a headline that
failed re-derivation, a defect whose correction reverses a conclusion, or oracle contamination that
*favored* the thesis. None occurred. The economics headline (0.62×, conservative across models and
leads, robust on measured vLLM cost in its neighbouring scopes) and the structural headlines
(two-pool knees, foundation-predictor advantage, reactive inferiority on fast onsets) all survived
from-scratch re-derivation.

---
*Sources: VERIFICATION-LEDGER.md, FAILURES.md, FIGURES.md, EVIDENCE-PACK.md,
reports/evidential/proposer_draft.md, gpt-sol critique, 91 opus arbitration verdicts, minimax
corroboration. Read-only throughout; no thesis text edited.*
