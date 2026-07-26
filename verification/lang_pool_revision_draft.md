# Language-pool revision — DRAFT (DB-verified) — 2026-07-25

**Status: PROPOSED for your review. No `.tex` edited.** Every number below is verified against the
`provenance` DB (`experiment='langcalib'`, 157 runs) — the verification queries + outputs are in §4.
Backing: results-ledger "Language-pool operating point" + addenda 1–6; audit `S5_2_LANG_RECONCILE.md`.

---

## 1. The argument, elaborated

**Where the thesis stands.** The published language operating point is Chronos **p90, scale 8**. p90 was
chosen because it is the *calibrated upper band edge* — principled, but never cost-*optimized*. Priced
honestly against the burst-sized static TP2×2 fleet it is **0.965× time-matched / 1.03× request-matched**
— a coin-flip. That is why the thesis says the language pool "buys compliance, not savings," and why the
internal delivery ruling (§5.2) concluded *no language cost advantage may be claimed*.

**What honest recalibration shows.** Select the operating point — the forecast **quantile × the
tail-aware conversion scale** — on the **first 1.4 days only** (the forecast-context split: burst2 +
burst6, with burst6 contributing a 1-minute onset), then evaluate **held-out** on the eval span. This
exposes that **p90/s8 is ~40% over-provisioned**: it stacks *two* headroom sources (a high quantile AND
a high scale) when the fast-onset feasibility threshold needs only one. The cost-optimal held-out point
is a **plateau near 0.62× static**, reachable by several (quantile, scale) mixes (p70/s6, p90/s4, p50/s8
all land there).

**The e13 caveat, and the honest frontier.** That 0.62× band **drops the e13 onset** (daily fold F6):
the 5.60-day *aggregate* masks it — e13's ~843 over-bound requests are 0.11 % of 749,601, below the 1 %
that sets p99 — and only *per-fold* grading reveals it. This is the **same dashboard-masking the thesis
warns about, and the same e13 onset the encoder headline also drops.** The cheapest point that clears
e13 *with margin* is **p90/scale6 = 440 GPU-h = 0.819× static(time) / 0.874× static(request)**, passing
every fold. So the deployable result is a **two-point frontier**: *aggressive ≈ 0.62× (drops e13)* ↔
*e13-robust ≈ 0.82× (passes everything)*.

**The mechanism — demonstrated, not asserted — is the CONVERSION, not the forecaster and not the
horizon.** Three controlled results:

1. **Conversion is the lever.** Hold the Chronos-p90 forecast fixed; flip *only* the conversion. The
   **mean** conversion (the planner's native `demand / r̂` sizing, `scale=1`) fails **byte-identically to
   reactive** (burst3 3495 ms for both); the **tail-aware** conversion (`r̂ → r_tail`, ≈8× replica
   headroom, `scale=6`) **passes** (651 ms). Same forecast, opposite verdict.
2. **Predictor-independent.** The reactive failure is not about ARIMA or even forecasting-vs-not:
   `constant` (forecast-free), `arima`, `kalman`, `prophet` all fail at tails identical to **≤8 ms** on
   every eval burst.
3. **Not the horizon.** The language forecast is a **held cursor** (one sampled 15-s bin per control
   minute — no look-ahead — because it plugs into the production planner's observation-driven predictor
   slot), and the result is **lead-invariant**. Anticipation is neutralized by construction, so the
   lever is purely the capacity conversion (mean throughput → tail-knee). Horizon is the *encoder*
   pool's lever, not the language pool's.

**Symmetry of the comparison.** The baselines are calibrated on the *same* 1.4-day split: static →
**TP2×2 is minimal-feasible** there (TP1×4 fails 1225/1223 ms; not an oracle sizing), and reactive →
**fails at every target** (400/40 → 200/20). So "forecast beats reactive / near-break-even vs static"
holds with all three arms calibrated on the same data.

**Net contribution (revised).** On the language pool the tail-aware conversion — a *measured*
belief-to-knee ratio — is the **sole operative lever**, and under honest held-out calibration it yields a
**modest, e13-robust cost win (0.82× static)**, improving on both the published p90/s8 (~break-even) and
the reactive planner (which fails the week at 1197 ms / 282 GPU-h). The bigger 0.62× is available only if
the single e13 onset is dropped — the encoder pool's caveat, symmetrically.

---

## 2. Proposed manuscript changes (each number DB-cited to §4)

### 2a. `tex/closedloop.tex` — §cl-llm (language-pool cost paragraph)

> **OLD (essence):** "…passes the week at 651 ms for 518.6 H100 GPU-h, slightly below the burst-sized
> static TP2×2 fleet's 537.4 (0.965×) … the language-side saving is cross-window … the decisive per-pool
> savings are on the encoder side."

> **NEW (proposed):** The published p90/s8 language schedule is ~break-even against static
> (518.6 vs 537.4 GPU-h, 0.965× time / 1.03× request [Q-A0]) because p90 is the calibrated band edge, not
> a cost-optimized point. Selecting the operating point (quantile × tail-aware scale) held-out on the
> 1.4-day forecast-context split (burst2+burst6) instead of fixing it at p90/s8 shows the latter is
> ~40 % over-provisioned. The result is a two-point deployment frontier over the 5.60-day span: an
> *aggressive* point near **0.62× static** (e.g. p70/s6, 330.4 GPU-h [Q-A]) that passes the aggregate but
> **fails the e13 onset per-episode** (fold F6, 1134 ms [Q-F]) — masked in the aggregate exactly as
> §cl-aggregate warns, the same onset the encoder headline drops — and an *e13-robust* point
> **p90/s6 = 440.0 GPU-h = 0.819× static(time) / 0.874× static(request)** [Q-A], passing every daily fold
> (e13 = 886 ms [Q-F]). The lever is the **conversion**, not the forecaster or the horizon: holding the
> Chronos-p90 forecast fixed, the mean conversion fails byte-identically to reactive (burst3 3495 ms both
> [Q-C,Q-D]) while the tail-aware conversion passes (651 ms [Q-C]); and the reactive failure is
> predictor-independent (constant/ARIMA/Kalman/Prophet within ≤8 ms [Q-D]). So the honest language-pool
> statement is a **modest e13-robust saving (~0.82×)**, improving on both the published point and the
> reactive planner (week 1196.6 ms / 281.8 GPU-h, FAIL [Q-B]).

### 2b. `tex/tese.tex` — Abstract

> **OLD:** "…the Chronos-p90 language schedule near break-even at 0.965× a time-matched static TP2×2
> reference."

> **NEW (proposed):** "…the language pool a modest, e13-robust ~0.82× of a time-matched static TP2×2
> reference under held-out calibration (the published p90 edge is near break-even at 0.965×; a more
> aggressive point reaches 0.62× but drops the single e13 onset)."

*(Conservative alternative if you prefer minimal disruption: keep 0.965× and append "; an
honestly-calibrated operating point reaches ~0.82× e13-robust.")*

### 2c. `tex/conclusion.tex` — RQ4 language clause

> **OLD (essence):** "…the Chronos-p90 language schedule passes at 0.965× a time-matched static
> TP2×2 reference."

> **NEW (proposed):** "…and the language pool, provisioned on the tail-aware conversion, reaches a modest
> e13-robust ~0.82× of a time-matched static TP2×2 reference under held-out calibration — the conversion,
> not the forecaster (predictor-independent) or the horizon (a held cursor), being the demonstrated
> lever."

### 2d. `provenance/audit/DELIVERY_RULING.md` §5.2

Adopt the scoped amendment already drafted in `S5_2_LANG_RECONCILE.md`: replace "no language cost
advantage may be claimed anywhere" with the p90/s8-scoped version + the honest ~0.82× e13-robust point.

---

## 3. What to decide (author)

1. **Adopt the frontier framing** (recommended): keeps p90/s8's 0.965× as the *conservative edge* and
   adds the *cost-optimal* (0.62×, drops e13) and *e13-robust* (0.82×) points — the deployment story,
   fully held-out and DB-backed.
2. Or **minimal**: leave the headline at 0.965× and add one sentence that honest calibration reaches
   ~0.82× e13-robust.
3. Open sub-items: the **p90/s5 knee** (995 ms, knife-edge — not adopted), and whether to run **fresh
   week-scale symmetric baselines** under `langcalib` (I reused the existing `planner:week_re` + the
   537.4 static reference).

---

## 4. DB verification — every number above

All: `SET search_path=provenance,public;` on `goku@localhost:5433`, `experiment='langcalib'`.
Static refs: time-matched 537.403 GPU-h (4 GPU × 483,662.5 s / 3600); request-matched 503.7.

- **[Q-A] Week (aggregate) forecast arms** — `runs ⋈ llm_run_summary`, `window_name='aggregate'`:
  p50/s8 819.5 ms / 318.1 GPU-h / 0.592× / 0.631× · p70/s6 757.6 / 330.4 / 0.615× / 0.656× ·
  p90/s4 702.6 / 337.4 / 0.628× / 0.670× · **p90/s6 651.1 / 440.0 / 0.819× / 0.874×** (ITL 7.25).
- **[Q-A0] Published p90/s8**: `planner:week_fc_p90` = 651.1 ms / 518.6 GPU-h → 0.965× / 1.030×.
- **[Q-B] Reactive week**: `planner:week_re` = 1196.6 ms / 281.8 GPU-h (FAIL).
- **[Q-C] Triad @ burst1**: forecast+tail (p90/s6) 671.9 · forecast+mean (p90/s1) 1626.3 ·
  reactive+mean (200/20) 1615.5.
- **[Q-D] Predictor independence @ burst3** (reactive): arima=constant=kalman=prophet = **3495 ms**.
- **[Q-E] Fold means vs static** (`fold gpu_h / (4 × windows.span_s/3600)`): p50/s8 0.52–0.76 mean 0.61
  (all_pass f) · p70/s6 0.52–0.80 mean 0.62 (f) · p90/s4 0.54–0.80 mean 0.65 (f) · **p90/s6 0.66–1.68
  mean 0.98 (all_pass t)**.
- **[Q-F] e13 fold (F6) per point**: p90/s6 886 PASS · p90/s5 995 PASS(knife-edge) · p90/s4 1033 FAIL ·
  p70/s6 1134 FAIL · p50/s8 1218 FAIL.
- **Symmetric baselines (1.4-day calib, burst2/burst6)**: static TP1×4 1225/1223 FAIL, TP2×2 745/697
  PASS; reactive ladder 400/40→200/20 all FAIL (1515–1701 ms). Held-out eval: static passes / reactive
  fails / forecast passes on burst1/3/4/5.

Reproduce: `provenance/loader/load_langcalib.py` (idempotent) + the §4 queries.
