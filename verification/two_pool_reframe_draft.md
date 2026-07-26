# Two-Pool Reframe — reviewable draft (2026-07-26)

Status: APPLIED (2026-07-26). The reframe is in the `.tex` (abstract, conclusion RQ4, closedloop,
twopool cost loci) and survived the 5-round multi-agent convergence review — see the ledger's
"Iterative fix+review convergence" entry. §6 is complete (all 9 language points; durable snapshot in
`simulation/results/lang_qsweep/violation_curves_2026-07-26.txt`). This document is retained as the
design record; where prose differs from the manuscript, the manuscript is authoritative.

---

## 0. Thesis, one sentence

Predictive per-pool provisioning does not define a single *operating point* but an **aggressive↔robust
frontier**; the naive predictive point is the cheap-but-fragile end that silently drops the hardest
episode (e13), and the deployable robust point is reached by a **pool-specific lever** — a hybrid
controller for the encoder, tail-aware conversion for the language pool.

## 1. What changes vs the current manuscript

| current framing | reframed |
| --- | --- |
| encoder provisioned by **pure forecast** `C=ceil(ŷ_p90/ρ)` | pure forecast silently **drops 2/7 days** (F2 warm-up, F6/e13); the deployable controller is the **hybrid** `max(forecast, reactive)` |
| language "Chronos-p90 edge near break-even 0.965×" | a **frontier**: aggressive 0.50–0.62× (drops e13) ↔ robust **0.82×** (e13-safe); **no cost advantage over reactive** — §5.2 stands, now quantified |
| cost stated per pool, ratios only | **dollar model** (gpus.io, cited): language pool = **~74% of the bill**, 3.1× the encoder; robustness is a **premium**, not a saving |
| robustness argued per-episode (e13 pass/fail) | robustness measured as **exact week-wide violation counts** vs cost (both pools) |

## 2. The frontier (the core claim)

Both pools admit a cost/robustness frontier with the **same shape** but **different mechanisms**,
and **e13 is the universal breaker** — a ~1-min onset (peak 262.9 img/s in F6) that the aggregate
p99 masks.

| | aggressive (drops e13) | robust (e13-safe) |
| --- | --- | --- |
| encoder | pure forecast **0.62×** | **hybrid 0.76–0.79×** |
| language | reactive / p70 **0.52–0.62×** | **conversion p90/s6 0.82×** |

The costs line up (~0.6× fragile, ~0.8× robust) even though the *levers* differ.

## 3. Pool-specific robustness levers — the asymmetry, and why

- **Encoder → hybrid.** Its controller is **anticipatory** (issue-time): forecast and reactive miss
  the onset at *different instants*, so `max` covers the union. Per-fold F1–F7: pure forecast FAILS
  2/7 (F2 1319 ms, F6 1264 ms), reactive FAILS 1/7 (F6 1229 ms), **hybrid FAILS none** (F6 679 ms).
- **Language → conversion.** Its controller is a **held-cursor** predictor (samples one 15-s bin per
  control minute, no look-ahead → lead-invariant). Forecast-through-**mean** conversion is byte-close
  to reactive (week-scale: p99 6987 vs 6899 ms; 269 vs 282 GPU-h — within 1–5%), so a language hybrid
  `max(fc, re) ≈ re` buys nothing. The lever is the **tail-aware conversion** (`demand/r_tail`, ↑quantile
  + ~8× scale), which absorbs the arrival→load nonlinearity the raw forecast can't see.

Root cause of the asymmetry: **the forecast predicts arrivals, not realized load.** Arrivals are
exogenous and easy (every predictor — Chronos/Toto/TimesFM/constant/arima/kalman/prophet — performs
alike); the hard, nonlinear arrival→capacity step lives in the conversion. So the encoder benefits from
combining anticipation with reaction; the language pool benefits from a better conversion, not a hybrid.

## 4. The hybrid controller — definition, optimality, premium

**Definition.** `C_hyb(t) = max(C_fc(t), C_re(t))`, each arm `ceil(rate/ρ)` clamped [1,32]; forecast arm
uses p90 issue-time `ŷ`, reactive arm uses last-observed 15-s bin; ρ=15 img/s/worker, cold-start 30 s,
hysteresis 3. Pointwise max over the union of breakpoints (`combine_schedules.py`).

**Optimality (F6 combination sweep).** `max(p90, react_point ρ15)` = 679 ms @ 0.79× is the **cost-minimal
e13-passing** combination. Cheaper forecast quantiles fail (max(p70,re)=1016 ms; max(p50,re) collapses to
reactive=1229 ms); a windowed-quantile reactive fails (smooths the fast onset); cranking reactive up
(ρ12→ρ10) passes but costs *more* (0.83–0.97×). A weighted blend `α·fc+(1−α)·re ≤ max` pointwise, so it
reopens exactly the gaps max closes. Mechanism: **forecast anticipation is cheaper capacity than reactive
over-provisioning**, so load anticipation on the cheap targeted forecast arm + a light reactive top-up.

**Premium (the unavoidable cost, decomposed).** `max(fc,re) = fc + (re−fc)⁺` — the hybrid spends above
forecast *only* where reactive observes more than forecast predicted. On the aggregate: the premium is
paid **35% of the time** (zero the other 65%), totals **534k worker-s = 13.8% of static** (= the
0.76×−0.62× gap), and **equals the forecast error** integrated. Consequences: (i) it is the smallest
robust premium available; (ii) it shrinks 1:1 as the forecast improves — a perfect forecast pays zero
(it is the oracle). The lever to cut it is a better forecast/conversion, **not** a cleverer combiner.

## 5. Cost — the dollar model (gpus.io, snapshotted 2026-07-25)

Prices (median, evidence in `provenance/audit/evidence/gpu_pricing/`): H100 **$2.99/h**, RTX 5090
**$0.52/h** → H100 = **5.75×**. Over the 5.60-day trace:

| pool | robust point | accel-h | **cost** |
| --- | --- | --- | --- |
| encoder (5090) | hybrid | 818 | $425 |
| language (H100) | p90/s6 | 440 | $1316 |

- system all-static **$2166** → robust-both **$1741 = 0.80×**; **language = 74% of the bill**, **3.1×** the encoder.
- **Relative to reactive (week-wide), forecasting/hybrid is a LOSS, not a gain**: encoder **+13%** (+$48),
  language **+56%** (+$474), system **+43%** (+$522, 90% of it language). At matched (fragile) SLO it's a
  wash (−5 to −8%). The pitch is not "cheaper than reacting" — it is "the cheapest *robust* option," and
  even a robustness-tuned reactive (ρ12) is dearer than the encoder hybrid (0.83× vs 0.79×).
- **The interesting result (encoder hybrid) is on the cheap pool; the money (and the modest, reactive-tied
  win) is in the language pool.** State that plainly.

## 6. Cost ↔ violation — EXACT, week-wide (of 749,601 requests)

**Encoder (exact, per-request enc-delay):**

| controller | $ | >250 ms | >500 ms | >1 s | >2 s | >5 s |
| --- | --- | --- | --- | --- | --- | --- |
| reactive | 377 | 31,536 | 20,988 | 3,299 | 1,414 | 497 |
| pure forecast | 348 | 31,066 | 20,512 | 2,650 | 1,005 | 259 |
| **hybrid** | 425 | 29,988 | 19,267 | **1,725** | **630** | **171** |

(>250/500 ms is the handoff floor, ~flat; the queue-violation tail is the signal — hybrid cuts >2 s by 55%.)

**Language (EXACT, per-request; all 9 points, `brfacqud1` complete 2026-07-26). Sorted by cost:**

| point | $ | ttft>200 | ttft>500 | ttft>1 s | e2e>5 s | e2e>10 s | e2e>20 s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fc chronos p90 **mean** | 804 | 65,482 | 38,471 | 11,458 | 16,842 | 3,327 | 942 |
| reactive 200/20 | 842 | 64,063 | 37,525 | 10,910 | 16,407 | 3,236 | 927 |
| fc chronos p50/s8 | 952 | 49,264 | 27,996 | 5,733 | 12,417 | 2,544 | 859 |
| fc chronos p70/s6 | 984 | 46,741 | 26,453 | 4,817 | 11,901 | 2,469 | 848 |
| fc chronos p90/s4 | 1027 | 44,198 | 24,950 | 4,015 | 11,133 | 2,363 | 828 |
| fc **toto** p90/s6 | 1244 | 40,720 | 23,575 | 3,697 | 9,967 | 2,140 | 755 |
| fc **chronos p90/s6** (robust) | 1325 | 37,639 | 22,126 | 2,765 | 9,196 | 1,980 | 732 |
| static TP2×2 | 1607 | 33,220 | 20,194 | 1,799 | 8,242 | 1,839 | 690 |
| fc **timesfm** p90/s6 | 1670 | 36,975 | 21,767 | 2,623 | 8,806 | 1,926 | 713 |

Exact readings (all confirm earlier findings at per-request granularity):
- **Monotone cost↔violation frontier** — every step up in quantile/scale trades cost for fewer violations.
- **fc-mean ≈ reactive, exactly** — 65,482 vs 64,063 ttft>200 ($804 vs $842): the same operating point at
  per-request level. Confirms `max(fc-mean, re) ≈ re` → no language hybrid.
- **reactive → robust p90/s6** cuts ttft>200 **64,063→37,639 (−41%)** and the severe **ttft>1 s
  10,910→2,765 (−75%)** for **+$483**, landing near static (33,220 / 1,799) at 0.82× cost.
- **Model-independence with the cost caveat, now exact:** the p90/s6 *violation reduction* is similar across
  forecasters (toto 40,720 / chronos 37,639 / timesfm 36,975 ttft>200) but the *cost* is not — toto $1244,
  chronos $1325, timesfm $1670. **TimesFM p90/s6 is Pareto-dominated by static** (costs ≈ the same, $1670 vs
  $1607, with *more* violations, 36,975 vs 33,220) — over-provisioning without benefit. Only chronos/toto sit
  on the frontier below static; chronos p90/s6 is the sweet spot.
- **The language pool dominates affected requests too** — tens of thousands (33k–65k ttft>200) vs the
  encoder's hundreds in the severe tail — so the deployment-critical cost↔violation trade lives there.

## 7. Where it lands in the `.tex` (section-by-section)

- **abstract** — replace "Chronos-p90 language edge near break-even 0.965×… 0.82× e13-robust" with the
  frontier + pool-specific-lever sentence (§0), and add the system-level "robust-both ≈ 0.80× of
  all-static, language-dominated."
- **`conclusion.tex` RQ4** — the frontier, both levers, e13 the universal breaker masked by aggregate p99;
  cost is a robustness *premium*, not a saving; language pool dominates the bill.
- **`closedloop.tex`** — NEW encoder-hybrid paragraph (per-fold table + premium decomposition + combination
  optimality); keep/extend the language-frontier paragraph (conversion lever, 0.82×, model-independent
  latency but forecaster-dependent cost — TimesFM 0.99×).
- **`twopool.tex`** — controller description: encoder = hybrid `max(fc,re)`, not pure forecast; note the
  asymmetry (why no language hybrid).
- After edits: re-run the verification/review pass over the new prose; update `progress/results-ledger.md`
  cross-refs.

## 8. Guardrails — what NOT to claim

- NOT "hybrid for both pools" (language hybrid buys nothing — measured).
- NOT "forecasting saves cost vs reactive" (it's a premium; §5.2 stands).
- NOT "model-independent 0.82×" (latency is model-independent; **cost is not** — Toto 0.79× / Chronos 0.82× /
  TimesFM 0.99×).
- NOT a per-episode-only robustness claim — carry the exact week-wide violation counts.
- F1 forecast cold-start (forecaster needs ~2 h warm-up) is a real edge, not a bug.
