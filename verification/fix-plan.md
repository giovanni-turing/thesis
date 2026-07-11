# Remediation Plan — Delivering a Defensible Thesis

> **SUPERSEDED-WORDING.** Where this historical planning doc says "true e2e" / "true end-to-end", read "**modelled** ingress-to-first-token reconstruction" (exact encoder delay + modelled prefill; 1.30 s joint, 1.24 s marginal). The applied manuscript and scripts use "modelled".

**Author:** Claude · **Date:** 2026-07-10 · Inputs: `adjudicated-issues.md`,
`false-positives.md`, the six `verify-*.md` passes, and my own artifact recomputes.

## The strategic picture (read this first)

The verification is unambiguous about *which* claims are at risk, and it is good news
structurally: **the thesis's descriptive spine is untouched.** What needs work is the
*closed-loop mechanism* and the *economic headline*, and most of that is fixable by
**recomputing consistently** (the defect often hits numerator and denominator equally, so
the ratio can survive) and by **re-scoping to what was actually demonstrated** (which yields
an *honest negative result* that strengthens the thesis rather than weakening it).

Three moves carry the whole plan:

- **Move A — Recompute both sides on the corrected metric.** B1 (image-bearing p99) and B5
  (stability criterion) look fatal in isolation but are *ratios*. Recompute the forecast
  fleet **and** the static denominator on the same corrected rule; the headline may barely
  move. (Early evidence: the retained aggregate forecast run passes at 825 ms image-bearing,
  and the C=16 denominator is set by burst5, which is image-dense so its p99 is unchanged.)

- **Move B — Re-scope the mechanism to the corrected onset audit.** The honest finding from
  B2/B4 is: **anticipation is real on the slower onsets (burst4/5) and impossible on the
  1-minute onsets (burst1/3) at these forecast horizons.** That is a *sharper, more credible*
  claim than "every onset," and the "fast onsets can't be anticipated" negative is a genuine
  contribution (it motivates the tail-aware conversion as the fallback).

- **Move C — Narrow the novelty to what survives, and cite the neighbors.** The precedence
  claims lose their broad form to ModServe/HeteroServe/Diao/Toner. The defensible novelty —
  *forecast-driven* per-pool provisioning + the **R²=0.123 quantification** of decoupling +
  a **silicon-calibrated encoder model inside a deployment planner, upstreamed** — is still a
  real, publishable contribution.

**Net reframe of the thesis claim** (what I'd defend): *"On a production multimodal trace,
request rate is a poor proxy for encoder load (R²=0.123); the encoder signal is forecastable
at multi-minute horizons; a silicon-calibrated two-pool model shows the pools' capacity needs
decouple; and a tail-aware, forecast-driven per-pool controller meets the encoder tail SLA at
a fraction of a burst-shaped static fleet on the slower-onset episodes, while fast
1-minute onsets are shown to be beyond anticipation at these horizons — making the tail-aware
capacity conversion, not lookahead, the load-bearing ingredient there."* That claim is fully
supported after the fixes below and is a strong master's thesis.

---

## Workstream 1 — Re-runs I can execute (CPU; the load-bearing fixes)

These decide whether the headline survives. All are cheap CPU jobs on existing code/artifacts.

**W1-A [P0-1/B1] Recompute every vision result on image-bearing p99.**
- *Do:* add an `image-bearing` percentile alongside the mixed one in the converter's stats
  (report both, explicit denominators); re-derive the static-optimal grid (Table 7.1), the
  saturation curves, the 560/112-cell matrices, and the aggregate/week runs on it.
- *I can run:* yes — the join is `hash_ids[0]//100000 → NumImages`; I already did it for the
  silicon work. ~1–2 h CPU.
- *Likely outcome:* Table 7.1 burst1/3/4/6 C\* move up one worker; the **deployable static
  C=16 (set by burst5) is unchanged**; the forecast aggregate still passes (825 ms). So the
  *headline ratio likely survives*; what changes is the per-window static table and the "588 =
  service floor" language (floor becomes ~825 image-bearing on the aggregate). **De-risks B1
  from "fatal" to "table + wording update."**

**W1-B [P0-5/B5] Replace the endpoint divergence heuristic with a real stability criterion.**
- *Do:* judge stability by backlog *slope* over the arrival window (and/or a periodically
  repeated/padded trace), not the last-second queue vs 10× median. Re-derive burst5's C\* and
  the static denominator.
- *I can run:* yes — the per-C burst5 stats exist (C8/12/14/15/16); I add a slope/repeat test.
- *Decision fork (needs your call):* if the criterion admits **C=8**, the honest headline is
  **~0.55–0.61×** (still a win, smaller); if burst5 genuinely saturates at ~16 (my
  measured-silicon multi-worker run found it divergence-limited at C=16 under real f(N)), the
  **0.27–0.31× holds**. I recommend: run it, and *whatever it says, report it with the drain-
  time and slope sensitivity* — that converts the weakest point into a rigor showcase.

**W1-C [P0-6/B6] Compute the end-to-end ingress-to-first-token p99 (or drop the wording).**
- *Do:* join `hash_ids` to recover raw ingress, add encoder_delay + language TTFT per request,
  report the true e2e p99; OR state per-pool grading explicitly and delete "end to end."
- *I can run:* yes — recoverable via the same join. Computing it is better (a real number).

**W1-D [P2-1] Run the reactive + tail-aware conversion cell (the consensus experiment).**
- *Do:* add a trailing-window-p90 + tail-aware-conversion reactive controller; run burst1 +
  the week on both pools.
- *I can run:* yes — `forecast_schedule.py` reactive branch + the tail conversion already
  exist separately; compose them. ~30 min.
- *Likely outcome (favorable):* predictors show p50+tail already fails burst3 at 2,164 ms and
  the reactive signal is strictly staler, so this **likely fails the fast onsets** — which
  *cleanly attributes* the fast-onset win to anticipation and the mean-planner defect to
  conversion. Either result is publishable; failure strengthens the story.

## Workstream 2 — Re-run OR re-scope (your risk appetite; the mechanism claim)

**W2-A [P0-2/P0-3/P0-4/B2-B4] The forecast issue-time semantics.** Two paths:
- *Path (a) — rebuild (ambitious, restores the strong claim):* regenerate forecast archives
  at H≥21 (15 s) so a 300 s issue-lead exists; rebuild `forecast_schedule.py` to actuate on
  *issue time* (order increases from the forecast origin, model pending workers); re-run every
  encoder lead/cost cell and the onset audit restricted to declared episodes. If the flat
  15→300 s result reproduces under honest issue-time, the anticipation claim is *properly*
  established. Effort: ~half a day CPU + code; risk: it may show the fast onsets aren't
  anticipable (which is Path b anyway).
- *Path (b) — re-scope (safe, honest, faster):* keep the runs, correct the onset audit
  (episode-restricted, issue-time), and rewrite the mechanism to the corrected evidence:
  anticipation on burst4/5, lateness on burst1/3; drop "300 s forecast-issued lead" and "every
  onset." Effort: text-only.
- *My recommendation:* **do Path (a) for the encoder** (cheap enough, and it either restores
  the claim or proves the negative rigorously), and write the result honestly either way.

## Workstream 3 — Factual fixes (quick text; batch in one pass)

All P1 items — 419→209.5 (+ PR #1312 yaml), spectral harmonics, `tab:base-tp` C6→C7
(746→845.7, 1.76→1.55×), Prophet-beats-naive, 300-origin disclosure, clocks 2377→2400,
gen-band 37–435, gen-slope 0.81, BurstGPT 213 days, engine_rps 5.31→5.71, 245→120 s + root
cause, ~3%→7.3% infilled-slice. **~30–45 min, mechanical, no result at risk.** The one
external step: update `rtx_5090.yaml` in draft PR #1312.

## Workstream 4 — Scope/wording + citations (text; uses your corpus)

- P2-3 (0.96× Chronos-only), P2-4 (fabric caveat at all 11 sites), P2-5 ("each leans
  conservative"), P2-6 (frontier loose end 993.8), P2-7 (utilization cadence), P2-8
  (provenance "draft PR"), P2-9 (abstract live scope), P2-11 (knee conditioning), P2-13
  (single-trace + future-work second trace) — all text.
- **P2-10 (staffing literature): cite from your own corpus** — Kleinrock, *Fundamentals of
  Queueing Theory*, and the queueing-grounded LLM-planner paper are in the RAG store; add one
  related-work paragraph anchoring the tail-aware conversion to square-root staffing. I can
  pull the exact bib entries.
- P0-7 precedence rewrite: narrow the three "first" claims to their qualifiers; add ModServe
  (image-tokens/s per-pool scaling), Diao/Toner (zero-shot FMs for cloud scaling), HeteroServe
  (already cited) as the adjacent work; reframe novelty per Move C.

## Workstream 5 — Nits (batch text)
All P3 items: five→six bodies, unit-label unify, R² sig-figs, forecast-free wording, REPORT.md
sync, k=8 note, appendix manifest rows (val-anchor + live51 + phaseE), clock-lock caveat,
footnote promotion, controller params, misc one-liners.

---

## Suggested sequence

1. **Factual pass (W3) + nits (W5)** — fast, unblocks a clean build; ~1–2 h.
2. **W1-A (image-bearing p99 recompute)** — settles B1's true impact; likely a table/wording
   update, not a headline loss.
3. **W1-B (stability criterion)** — the one real headline risk; run it, report honestly.
4. **W1-D (reactive+tail-aware cell)** + **W1-C (e2e p99)** — cheap, likely story-strengthening.
5. **W2-A path (a) (encoder issue-time rebuild)** — restores or rigorously negates anticipation.
6. **Scope/citation pass (W4)** incl. the precedence rewrite and staffing citations.
7. **Re-scope the thesis statement/abstract/conclusion** to the reframe above.
8. Final ledger + numeric sweep + build.

## Decisions I need from you
1. **W1-B outcome policy:** if the honest stability criterion gives C=8 for burst5 (headline
   → ~0.55–0.61×), do we report the smaller ratio (my recommendation — still a clear win and
   far more defensible), or hold at 0.27–0.31× only if the criterion supports C=16?
2. **W2-A:** rebuild the encoder to true issue-time (Path a, my recommendation) or re-scope in
   text (Path b)?
3. **Scope of my autonomy:** should I start executing W3+W5 (factual + nits, zero risk) and
   W1-A/W1-D (recomputes) now, and report before touching the headline (W1-B/W2-A)? That's the
   safe order and I recommend it.

**Confidence:** with W1–W5 done, this is a defensible, honest, and still-novel master's
thesis — arguably stronger than the pre-review draft, because the corrected mechanism claim
(anticipation where possible, tail-aware conversion where not) is more credible than "every
onset," and the rigor additions (dual-metric p99, stability criterion, e2e p99, the ablation
cell) directly answer the hardest examiner questions.
