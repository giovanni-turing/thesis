# Evidential-Integrity Assessment — PROPOSER DRAFT

Role: proposer in the Phase-7 trialogue. Sources: `EVIDENCE-PACK.md`, `FAILURES.md`,
`FIGURES.md`, `VERIFICATION-LEDGER.md`, `final-verdicts.v2.jsonl`, the frozen thesis
(`/home/gio/tese-review-frozen/tex/`), and direct read-only spot-checks of the provenance DB.
All tallies re-checked: 179 PASS + 26 PASS-UNVER + 12 UNVERIFIABLE + 10 FAIL = 227; clean
rate 205/227 = 90.3%; reviewer false-positive rate 75/85 = 88.2%.

---

## 1. Bottom line

**The thesis's empirical evidence is sound.** 205 of 227 data-verifiable claims (90%) are
clean against the provenance DB after from-scratch re-derivation; 10 are defective; none of
the 10 overturns a chapter-level conclusion. The trace-EDA chapter — the empirical foundation
everything else stands on — is 14/14 clean, the only chapter with zero flags of any kind.

The headline result — the forecast-driven encoder policy at **0.62x the deployable static
C=8 fleet's worker-time while meeting the SLA in aggregate and per-episode** — held. It is
instantiated in eight separate claims; seven passed (closedloop-0113, -0120, -0410, -0426,
-0457, -0468; intro-0242), including the two strongest forms: 0.62x is *conservative* across
models and leads (0426: 0.62x at L=15 falling to 0.59x at L=165), and it survives on
*measured standalone vLLM cost*, not only the AIC cost model (0457). My own spot-check of
`v_window_cost_ratio` gives per-window forecast-vs-static ratios of 0.609 (burst5) and 0.632
(steady24h) — consistent with a 0.62 week-scale aggregate. One honesty note the pack
underplays: the *eighth* instantiation, closedloop-0436 (the exact "Chronos p90, rho=15,
L=30s, 5.60-day span" parameterization), was ruled UNVERIFIABLE — no matching row could be
re-derived for that precise configuration. The headline number is safe; its most specific
parameterization in the text currently lacks a re-derivable backing row (see §4).

Second-order headlines also held where it matters: the reactive-baseline inferiority story
survives (with one boundary correction, §3), the foundation-vs-classical predictor gap
survives (with one resolution-scoped correction), and the two-pool knee structure (encoder
knee vs decoder knee, 235B envelope halving) survives with corrected magnitudes.

## 2. What the 88% reviewer false-positive rate means

The fast CONFIRM/REFUTE pass flagged 85 potential failures; opus re-derivation from raw DB
operands overturned 75 as reviewer artifacts — wrong view, wrong scope, superseded rows —
confirming only 10. Two readings, both partly true:

**The reassuring reading.** The thesis's numbers were right and the cheap reviewers were
wrong, in a specific, diagnosable way: they matched text against the wrong slice of a
many-sliced database. When a stronger agent recomputed each claim from raw operands, the
thesis won 75 of 85 disputes. That is a strong result — the failure mode of a fabricated or
sloppy thesis is the opposite (flags that *survive* re-derivation). It also validates the
verification protocol itself: derivation-first checking, not transcription matching.

**The uncomfortable reading.** If competent automated reviewers *with live access to the
actual provenance database* mis-verify a third of all claims (85/227 flagged), a human
examiner armed only with the PDF has essentially no chance of independently checking any
nontrivial number. The claims are true but *underdetermined by the text*: verifying one
requires tacit knowledge — which view (`v_cost_ratio` vs `v_window_cost_ratio` vs
`v_infraction`), which experiment family (a2 vs a2x vs a11 vs factorial), which actuation
convention (issue-time vs target-time), which denominator (deployable static C=8 vs C*),
`is_current`, superseded-row discipline. The clearest example: closedloop-0395, where two
reviewers "confirmed" the failure of burst4 beyond 45s using a12 runs (leads 60/120/300),
while the text's claim is about the a2 archive's realizable leads (15/30/45/165) — same
sentence, opposite verdict, depending on which run family you attach it to.

This is a **reproducibility-of-verification concern, not a truth concern** — but it is a
real concern for a thesis whose contribution is partly methodological. The mitigation
already exists and should be said out loud: the provenance DB plus the 227-claim
verification ledger *is* the missing map from sentence to query. Shipping (or archiving as
an appendix artifact) the claim→view→predicate mapping converts "hard to check" into
"mechanically checkable," and would be a genuinely unusual strength in a defense.

The 88% also deserves one deflationary caveat: it partly measures the weakness of the fast
reviewer models, not only the difficulty of the schema. Both factors are present; neither
excuses the other.

## 3. Severity triage of the 10 defects

The pack's labels: 6 major, 4 minor. My triage by *what is actually at stake*:

**Tier 1 — corrects a stated result (2 claims, one underlying fact).**
`baselines-0364` + `closedloop-0395`: "medium onsets survive only sub-minute leads
(L*=45s)" / "reactive loses burst4/5 beyond 45 seconds." The DB says burst4 (onset 60 min)
*passes* at L=165s: encoder-delay p99 = 904.739 ms < 1000 ms bound, `is_violation=false`,
confirmed in `v_infraction`. So medium-onset L* is 45–165s (2 of 3 windows at 45s), not
uniformly 45s. This matters because the sentence feeds an argument: *reactive scaling is
inadequate because pod-scheduled GPU workers can't deliver sub-minute leads*. With burst4 at
165s, one of three medium windows sits within plausible pod-scheduling reach, so the
argument weakens from "categorically inadequate" to "inadequate for 2 of 3 medium windows
and all fast onsets." The chapter conclusion survives — reactive still loses burst3 at every
lead and burst5 beyond 45s, and the forecast arm still dominates on cost — but the corrected
sentence is genuinely less sharp. Note the error is *anti-thesis-favorable when corrected in
the other direction*: the truth makes the reactive baseline look slightly better, i.e., this
is an honest analytic slip at a boundary (904.7 vs 1000 ms, a 9.5% margin), not motivated
rounding.

Is the recurrence a symptom of something deeper? **Yes, of one specific process gap**: a
derived fact was computed once, transcribed into prose, and *restated* in a second chapter
without re-derivation. Tables and figures in this thesis are regenerated from data (15/18
figures reconcile exactly; the knee tables match `sweep_point` to the decimal); *prose
restatements of derived facts* have no such loop. The same gap produced aiconfigurator-0382
(a superseded table value surviving a data refresh). Two instances, one mechanism:
**prose does not re-derive**. The fix is cheap — after correcting, sweep every restatement
of L*=45 (abstract, slides, conclusion) — but the pattern is the single most important
process lesson in the audit.

**Tier 2 — wrong magnitudes, structure survives (3).**
- `twopool-0025`: ITL p99 87.7→86.2 ms; "~2x decode latency throughout" is false (1.9x mean
  TPOT at s=1, ranging 1.2–3.9x; ITL-tail ratio 3.8x). The load-bearing structural claim —
  235B knee at s=1 vs 8B at s=2, envelope halved — verified by all four adjudicators.
- `predictors-0173`: "Chronos-2 takes most coarse bins" is wrong — TimesFM leads 45s (4/8),
  Toto leads 1min (3/8); Chronos leads neither. The fine-bin half (Toto 23/24) holds. This
  corrects a model-selection guidance sentence, not the chapter's thesis (foundation models
  beat classical baselines — which passed).
- `predictors-0176`: "all four Dynamo predictors at/below the classical frontier" holds at
  1min but fails at 15s, where ARIMA (0.6675) and Prophet (0.7328) beat the best classical
  (naive 0.7638) and ARIMA roughly matches Chronos (0.6674). The claim needs resolution
  scoping; the conclusion "none reaches the best foundation model" survives at both
  resolutions (toto 0.6374 at 15s, 0.5153 at 1min).

**Tier 3 — scope/wording precision (4).** `twopool-0062` (the 24h miss is policy-dependent:
true for fc_L30 variants, false for fcAware and static_C8 on g100), `twopool-0068`
("corrects" → raises 2.88→5.33 img/req, still 37% of the trace's 14.33), `intro-0197`
("request rate barely moves" → rises to 2.7x its weekly mean, above its p99), and
`closedloop-0425` ("essentially lead-invariant cost" → declines monotonically ~6% from L=15
to 165). All four are real overclaims and all four fixes make the thesis *stronger or
neutral* (0425's correction is actively favorable: cost falls with lead). The systemic
pattern the pack names is right: universal quantifiers ("throughout," "all four," "both
fabrics," "lead-invariant") attached to results that hold at one scope. That is a writing
discipline issue, now enumerated and fixable per-sentence.

A fair-minded observation on direction: of the 10, none inflates the headline economics; the
two Tier-1 corrections make a *baseline* look better; several Tier-3 corrections are neutral
or favorable. The defect profile is consistent with over-compressed prose, not with
result-shopping.

## 4. The 12 unverifiable claims

Three distinct populations, and they should not share one verdict:

**(a) Honestly out-of-scope for the DB (6):** twopool-0032 (chunk-parallel policy inert on
steady head — a mechanism claim), closedloop-0404 (p90 band leads/lags on specific bursts),
predictors-0179 (R²=0.94 regression), related-0286 (cold-start folklore — should carry a
citation, not read as a measurement), aiconfigurator-0371/0380 (27-block operator sequence,
projector dimensions — model-architecture facts checkable against configs, not run data).
These are honestly scoped; none smuggles a causal leap that a conclusion depends on. The
one causal-attribution smell the reviewers found ("single-stream handoff assumption" as the
*explanation* for the thin 672² margin) sits inside FAIL twopool-0062 and is handled there.

**(b) Setup/instrument description (3):** intro-0233 (kernel ledger closes within ~3%/~6%),
aiconfigurator-0257 (7679 attention cases, 34326 GEMM rows). Near-duplicates of claims that
*passed* (aiconfigurator-0251 "attention within ≈3%" — PASS; 0252 "≈0.7 ms remainder" —
PASS by opus arbitration), so the substance is corroborated even where the exact restatement
lacks its own backing row.

**(c) Should-be-derivable numbers with no current backing row (3) — the real residue:**
- `aiconfigurator-0264`: "11.360 ± 0.006 ms" for the 448² image. Current
  `collector_encoder_fn` rows give 11.217–11.333 ms with ci95 0.0115–0.0803. This is not
  independent of FAIL-0382 (same table, same superseded AIC vintage): the ±0.006 precision
  is not reproducible from current rows, and two arbiter votes said "overclaimed." Treat it
  as part of the 0382 fix, not as a benign unverifiable.
- `closedloop-0436`: the exact "Chronos p90, rho=15, L=30s, 0.62x over 5.60 days"
  parameterization. The headline is corroborated seven other ways (§1), but the single most
  operationally specific sentence in the thesis has no re-derivable row. Backfill the run
  or repoint the sentence at a row that exists.
- `closedloop-0439`: request-scaled language-week counterfactual (503.7 GPU-h, 1.03x). An
  honest robustness check that currently floats free of the DB.

**Assessment:** 9 of 12 are honestly scoped or corroborated by adjacent passing claims. The
three in (c) are the ones an examiner should press on — not because they look wrong, but
because a thesis that builds a provenance DB as part of its method should not carry
measured-looking numbers the DB cannot reproduce. Each needs either an ingested backing row
or an explicit in-text provenance note.

## 5. Residual risk — what this verification did NOT cover

1. **The ~240 non-data claims.** Methodological choices, design rationale, related-work
   characterizations, and generalization arguments were not audited. This is standard
   examiner territory and the standard defense surface; nothing here suggests elevated risk,
   but the 90% clean rate applies only to the data-verifiable half of the thesis.
2. **The oracle itself.** The DB loader gap (apendice-0138: the thesis's 232.0 is right; the
   DB ingested a contended-invalid row) proves the verification oracle can be wrong. One
   confirmed instance where thesis beat DB is fine; the meta-risk is the unexamined
   converse — a PASS where thesis and DB agree because both inherited the same contaminated
   upstream artifact. The verification checks text↔DB consistency, **not**
   experiment↔reality correctness: nothing in this exercise re-ran a simulation or
   re-measured silicon. The provenance chain below the DB is untested. A validity-flag audit
   of the loader (plus the 2 known claim-inventory mislabels) is cheap and should be done.
3. **Superseded-row discipline.** 0382 proves at least one stale value reached the text.
   The audit catches staleness only where current rows *differ detectably*; silent staleness
   (value unchanged across versions) is invisible to it.
4. **Figures.** 15/18 fully reconcile; the 3 flags are caption cosmetics — except
   `pred_framework_diff` panel (a), whose bars come from an untracked source and flip the
   naive-vs-HoltWinters ranking relative to both the DB and the thesis's own heatmap. Small,
   but it is the one displayed-data/DB mismatch in the document; the panel needs its source
   tracked or the panel regenerated. Panels (b)/(c), which carry the closed-loop claim,
   match exactly.
5. **No displayed formulas.** WAPE, cost ratio, coverage, and infraction are defined only in
   prose. Defensible stylistically, but note the connection to §2 and §3: several of the 10
   defects are precisely *scope-attachment* failures (which denominator, which window, which
   actuation convention), and displayed definitions with explicit denominators are the
   standard prophylactic. Two or three displayed definitions (cost ratio with its
   denominator; L*; the infraction rule) would cut off the thesis's dominant failure mode at
   the root and cost half a page.
6. **Single-trace generality.** The economics headline derives from one Azure trace week.
   The thesis says so itself (closedloop.tex:881) and scopes claims accordingly — this is a
   disclosed limitation, not a defect, but an examiner will raise it and the answer must
   stay inside the disclosed scope.

Weighting: item 2 is the only one that could in principle hide a substantive error, and its
probability is bounded by the diversity of corroboration (measured-vLLM cross-check 0457,
figure-level reconciliation, cross-family adjudication). Items 3–5 are hygiene. Item 1 is
ordinary defense exposure.

## 6. Verdict

**Defensible after the 10 fixes — no deeper rework required.** Grounds:

- Every one of the 10 defects has a drafted, sentence-level fix in FAILURES.md; none
  requires a new experiment, a new figure, or a retracted conclusion. The most substantive
  (L*=45→"45–165s, 2 of 3 windows at 45s") softens one argument's sharpness without
  reversing it.
- The headline economics (0.62x, conservative across models and leads, robust on measured
  vLLM cost) and the headline structure (two-pool knees, foundation-predictor advantage,
  reactive inferiority on fast onsets) all survived from-scratch re-derivation.
- The defect profile's direction (corrections favor baselines or are neutral) is the
  signature of compression errors, not advocacy.

**Conditions attached to "defensible" (beyond the 10):**
1. Sweep all restatements of the L*=45 fact (abstract, conclusion, slides) — the recurrence
   mechanism of §3 predicts more copies than the two found in graded chapters.
2. Resolve the three should-be-derivable unverifiables (0264 with 0382; backfill or repoint
   0436, 0439).
3. Fix the `pred_framework_diff` panel (a) provenance and the two caption flags; fix the DB
   loader validity gap.
4. Strongly recommended, not blocking: displayed definitions for cost ratio, L*, and the
   infraction rule; and archive the claim→query ledger as the reproducibility appendix —
   it converts §2's weakness into the defense's most distinctive strength.

What would have forced a harsher verdict — a headline that failed re-derivation, a defect
whose correction reverses a conclusion, or an oracle contamination that favored the thesis —
is absent from the record.

---
*Draft for critic (gpt-5.6-sol) and chair (opus). All DB queries read-only; no thesis text
touched.*
