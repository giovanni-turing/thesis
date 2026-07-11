# Adjudicated Issue List — Six-Reviewer Verification

**Compiled by:** Claude (adjudicator), from 6 Opus-4.8 tool-grounded verification passes
(`verify-{codex,opus,glm,grok,gemini,fabel}.md`) over the reviews of codex + 5 LLM
committees. Every quantitative item was independently recomputed from artifacts/code;
reference items checked against `./papers`, the RAG corpus, and the web.
**Date:** 2026-07-10.

**Aggregate verification outcome:** across the six passes, essentially **zero factual
denials** — every number the reviewers cited reproduced. The reviews differ only in
*severity calibration*: the 5 LLM committees graded "minor revisions"; codex graded
"not defense-ready," and its blockers were **47/47 confirmed at the code level.**

**Honest bottom line:** the thesis's **descriptive core survives** — request-rate/image
decoupling (R²=0.123), zero-shot forecastability, the silicon-validated encoder cost
model, the two-pool platform. What does **not** survive in current wording: the
**closed-loop anticipation mechanism**, the **end-to-end SLA** claim, the **0.27–0.31×
economic headline**, and the **three precedence ("first") claims**. These are fixable
(see `fix-plan.md`) — several by *consistent recomputation* that may preserve the
result, the rest by honest re-scoping.

Priority key: **P0 blocker** (challenges a headline/mechanism claim) · **P1 factual
error** (verifiably wrong number/statement) · **P2 attribution/scope** (claim outruns
evidence) · **P3 nit**. "×N conf" = independently confirmed by N of 6 verifiers.

---

## P0 — Blockers (all codex; code+artifact verified)

**P0-1 [B1] Encoder p99 is computed over the mixed population (text-only zeros in the tail).**
`workload/trace_to_two_pool.py:481-495,569-576` appends `encoder_delay=0.0` for every
text-only request and takes the p99 over that mixed list, while the SLA text calls it "the
worst percentile of vision-pool users" (`twopool.tex:193-204`). Recomputed image-bearing
p99 (joining `hash_ids` back to `NumImages`): **4 of 6 burst optima flip to FAIL** —
burst1 995.9→1118, burst3 904.7→1071, burst4 933.7→1037, burst6 933.8→1148; the next rung
C=8 passes each. The retained aggregate `fc_p90_L30` is 588.4 mixed but **825.1
image-bearing** — not the claimed "service floor." *Nuance (defender's room):* if the
intended metric is genuinely user-population p99 (text-only users legitimately see 0
encoder delay), the mixed statistic is a valid choice — but then the "worst percentile of
vision-pool users" wording is wrong and both metrics must be reported with explicit
denominators. Either way the 4/6 flip and the mislabeled floor are real. **Severity:
blocker→ at least major.** ×2 conf (codex + my own silicon-work replication).

**P0-2 [B2] Encoder forecast actuation uses target time, not forecast issue time.**
`simulation/forecast_schedule.py:103-149` sorts/dedups by target `ts` and discards the
horizon `h`; the archive is H=12 at 15 s, so max issue-lead = (12−1)·15 = **165 s**. The
L=300 s "anticipation" cells are therefore *impossible* as forecast-issued, and the
"flat from L=15 to L=300 = signature of anticipation" (`closedloop.tex:91-95`) does not
follow. **Blocker to the anticipation/lead claims.** ×2 conf.

**P0-3 [B3] Language forecast hook consumes a one-minute-old target and mis-aggregates.**
`simulation/replay_with_forecast.py:43-113` starts the series at `T0−1min`, and at each
planner tick selects *one* 15 s target bin × 4 rather than summing the four bins of the
control interval; the first decision at t=60 s selects target `T0` (already elapsed).
"Language mirror of the encoder's lead-invariance" is unsupported by the implementation.
**Blocker to the language anticipation/lead/cost claims.** ×1 conf (code-verified).

**P0-4 [B4] The direct onset proof searches outside every episode.**
`simulation/detect_onsets_44.py:48-50` searches from `episode_start − 30 min`; the stored
"actual" crossings (`riders44/detection_delay.json`) precede all four declared episodes,
and a 1-min 224 img/s threshold is applied at 15 s cadence (the 15 s p99 is 286). Restricted
to declared episodes, the evidence is **anticipation on burst4/5, LATE on burst1/3** — not
"onsets detected at or before the signal on every onset" (`closedloop.tex:115-124`,
`conclusion.tex:51-57`). **Blocker to the stated mechanism.** ×1 conf.

**P0-5 [B5] `C=16` static denominator rests on an endpoint-backlog heuristic.**
`queue_divergent` fires when the queue at the last-arrival second exceeds 10× the median
(`trace_to_two_pool.py:528-534`). burst5 C=8 already passes conditional p99 (852 ms) and its
residual drains in **0.386 s**, yet is flagged divergent. If a p99-plus-bounded-drain
criterion admits C=8, the static denominator halves and the headline **0.27–0.31× →
0.55–0.61×** (exact sensitivity table in `verify-codex.md`). *Interaction:* my earlier
measured-silicon multi-worker run found burst5 divergence-limited at C=16 under real f(N),
so the criterion and the silicon f(N) must be settled together. **Blocker to the economic
headline's magnitude.** ×2 conf.

**P0-6 [B6] End-to-end (ingress-to-first-token) p99 is never computed.**
Original arrival is discarded before language replay, so the "tail SLA reported end to end"
(`twopool.tex:195-204`) cannot be what is measured — the pools are graded separately.
*(Codex's "no join can recover arrival" is slightly overstated — `hash_ids` does recover
the index — but no end-to-end p99 is ever computed, which is the substantive point.)*
**Blocker to the end-to-end framing.** ×1 conf.

**P0-7 [B7/R1-R6] The three precedence ("first") claims do not survive as worded.**
`related.tex:303-309`. Verified against primary sources: **ModServe** (arXiv 2502.00937,
in corpus) already does "Token-Aware Pool Autoscaling" scaling Image Instances on
**image tokens/s** and explicitly contrasts it with request-rate autoscaling — defeats
"first per-pool demand-signal characterization" and "none asks what signal." **Diao et al.
(SoCC 2024)** and **Toner et al. (PMLR 2025)** evaluate zero-shot FMs for cloud-resource
scaling — pressure the "first provisioning-framed zero-shot benchmark." **HeteroServe**
(already cited by the thesis at `related.tex:71`) costs a consumer-GPU vision encoder —
defeats the broad "first consumer-GPU encoder cost model." Narrow, qualifier-loaded
replacements survive (forecast-driven; the R²=0.123 *quantification*; silicon-calibrated
*in a deployment planner*, upstreamed). **Blocker to the novelty framing.** ×2 conf
(codex + my RAG check of ModServe).

**P0-8 [B8/B9] Live anchor cannot validate forecast semantics; "every claim reproducible"
is false as a universal guarantee.** The live and offline paths share the same stale
forecast cursor (P0-3), so agreement proves implementation parity, not timing correctness;
and `apendice.tex:8-16`'s universal reproduction guarantee omits the live-anchor and
physical-anchor artifacts (see P3 manifest). **Scope-honesty blocker.** ×2 conf.

---

## P1 — Factual errors (verifiably wrong; multi-confirmed; mostly quick fixes)

**P1-1 419 → 209.5 TFLOP/s.** `aiconfigurator.tex:58`, `rtx_5090.yaml` ships
`418990000000000` "dense bf16." 419 is the FP16-accumulate/sparse rate; the vLLM path is
FP32-accumulate ≈ **209.5** (measured GEMM peak ~206; tower per-image GEMM = 192 TFLOPS =
92% of 209.5, 46% of 419). **Contained** — the encoder cost model uses measured lookups,
not this field; only the SOL/5.9× bound and PR #1312 yaml are affected. ×4 conf
(fabel+glm+opus+codex).

**P1-2 Spectral harmonics claim false.** `trace-eda.tex:135-137` "12- and 8-hour harmonics
exceed the 24-hour fundamental" — `f_fourier_stats.json`: request 24 h=**3892** > 8 h=2203;
12 h absent from the top-8. ×2 conf (fabel+codex-context).

**P1-3 `tab:base-tp` burst3 row uses C=6, caption says C\*=7.** `baselines.tex:115-133`:
shipped 1,314/**746** are the C6 run; C7 = 1,314.9/**845.7**. Fix TP2×2 746→845.7, tail
cut 1.76→1.55×, range 746–792→763–846. ×2 conf (fabel+my recompute).

**P1-4 Prophet beats naive.** `predictors.tex:194` "Kalman and Prophet trail even naive
(0.764)" — Prophet 0.733 < 0.764 (lower WAPE is better), so Prophet *beats* naive. Kalman
(0.811) is correctly worse. ×3 conf (opus+fabel+codex).

**P1-5 Undisclosed 300-of-2687-origin subsample.** ARIMA/Prophet at 15 s scored on 300
origins vs 2687 for the others — non-matched, undisclosed. ×2 conf.

**P1-6 Clock range 2377–2385 → 2377–2400.** `aiconfigurator.tex:302`; `relock.log` shows
SM rising to 2400 at N=64. ×2 conf.

**P1-7 gen-median band 50–140 → 37–435.** `trace-eda.tex:349`; artifact spans 37 (@25 img)
to 435 (@225 img). ×3 conf.

**P1-8 gen spectral slope 0.82 → 0.81.** `tab:eda-persistence`; artifact 0.8118. ×2 conf.

**P1-9 BurstGPT "year-long" → 213 days.** `related.tex:205`; local PDF + arXiv confirm 213
days. ×3 conf.

**P1-10 engine_rps 5.31 quoted where the live log shows 5.71.** 5.31 is the *offline twin*
value; the live planner log's first tick logs 5.71 (`validation.tex` / M12.3, MF-29). ×2 conf.

**P1-11 "245-second stall" → ~120 s, and no root cause.** codex M12.5 recomputes the max
tick gap at 120.041 s (fabel found no 245 s stall at all; max log gap 10–15 s in its read).
The specific "245" is unsupported; add a root-cause note or restate. ×2 conf (needs a
final direct check — the two verifiers got 120 s vs "no stall").

**P1-12 "~3% attention agreement" is raw-slice; production (infilled) slice ≈ 7.3%.**
`aiconfigurator.tex:17,488`. State on the infilled slice every simulation consumes, or label
"raw slice" at each site. ×3 conf.

---

## P2 — Attribution / scope (claim outruns evidence; wording ± small runs)

**P2-1 Missing reactive+tail-aware cell.** No reactive controller with the tail-aware
conversion exists in any script/artifact; "information, not plumbing" and "the conversion
repairs the defect shared by every reactive configuration tested" are true only because that
config was never run. *Partial mitigation:* the encoder reactive already runs at ρ=15
(tail-aware rating) and still fails burst3 at every lead — so "tail-awareness alone" is
partly answered on the encoder side. ×3 conf (codex M1 + glm R2 + opus M1). **The one
consensus experiment.**

**P2-2 burst1 ladder "information timing, not thrift" contradiction.** `baselines.tex:159-161`
— burst1's 220-min onset cannot fail on timing; contradicts the chapter's own mean-conversion
diagnosis. ×2 conf.

**P2-3 0.96× is Chronos-only.** Toto 625.3→1.16×, TimesFM 641.1→1.19× above static
break-even. Qualify the language cost claim as model-dependent (verdict is model-independent;
cost is not). ×3 conf.

**P2-4 Fabric caveat at 3 of 11 headline sites.** State the ≥100 Gbps / embedding-only
handoff assumption beside each 0.27–0.31× occurrence. ×4 conf.

**P2-5 "each leans conservative" omits the non-conservative caveats.** `conclusion.tex:87` —
token-accounting-convention dependence (and unvalidated H100 timing) are two-sided, not
conservative. ×2 conf.

**P2-6 Frontier loose end mis-stated.** `closedloop.tex:338` "899 ms at ρ25" is Chronos-only;
the honest p90 loose end at ρ25/L300 is **TimesFM 993.8 ms** (verified: p90 cell, still
<1000, passes; Toto 881.6). Quote the real loose end. ×1 conf (+ my direct recompute).

**P2-7 "invisible to utilization monitors" needs a cadence.** Max 1-min vision busy fraction
= **0.90**, so an 80%-utilization HPA on 1-min metrics *would* fire; the claim holds only at
coarser cadence or against rate-only monitors. ×2 conf. (Also S3: 29% uses the infeasible
2-worker topology.)

**P2-8 Provenance overstatement.** "upstreamed / contributed upstream / fixed upstream" →
"submitted as draft PR #1312 (unmerged; infill local)" and "fixed on a local branch."
×3 conf.

**P2-9 Abstract live-reproduction over-broadened.** `tese.tex:60-61` → scope to
language-pool, burst3, mocked engines. ×3 conf.

**P2-10 Queueing/staffing literature gap.** No Erlang-B/Halfin–Whitt/square-root-staffing
anywhere; the tail-aware conversion has no related-work anchor. **The RAG corpus already
holds Kleinrock, *Fundamentals of Queueing Theory*, and an on-topic queueing-grounded
LLM-planner paper** — citable now. ×2 conf.

**P2-11 ">10× / order-of-magnitude" knee separation** measured only on the image-lean steady
head; under measured f(N) the separation falls to ~8×. Condition it or knee-sweep the calm
day. ×2 conf.

**P2-12 "two-pool replay per cell" overstates the 560-cell matrix** — `results_44.jsonl` has
560 encoder-only rows, no TTFT. ×1 conf.

**P2-13 Single-trace generality** in universal register (abstract/intro) + no CI on any cost
ratio + second trace absent from future work. ×4 conf (consensus).

---

## P3 — Nits (quick, no result at risk)

- **P3-1** "Five bodies" vs six `\section`s in `related.tex:9` (+ intro:508). ×1 conf.
- **P3-2** GPU-time vs worker-time label drift (harmless; 1 worker = 1 GPU). ×2 conf.
- **P3-3** R² 0.12 vs 0.123 inconsistency. ×4 conf.
- **P3-4** "forecast-free policy" vs "ARIMA-driven" (`baselines.tex:40` vs :141) — reword to
  "needs no archived forecast." ×2 conf.
- **P3-5** `REPORT.md:24` says duplicates "dropped"; tex says "retained" (tex correct; REPORT
  stale). ×2 conf.
- **P3-6** Silhouette k=8 (0.3871) near-ties k=4 (0.3880) — note in the weak-separation
  disclosure. ×3 conf.
- **P3-7** Appendix manifest missing the `tab:val-anchor` row, `live51/` paths, phaseE
  artifacts, and etcd/Prometheus/aiperf env. ×2 conf.
- **P3-8** phaseE anchors record `clocks_locked: false`; appendix clock-pinning caption should
  scope to the AIC campaign. ×2 conf.
- **P3-9** Load-bearing cold-start numbers live only in an intro footnote (`intro.tex:93-109`).
  ×2 conf.
- **P3-10** Reactive controllers' trailing-window length / [1,32] clamp / 32-worker ceiling
  never stated. ×2 conf.
- **P3-11** Misc one-liners: "windowed-attention" → block-diagonal (`aiconfigurator.tex:262`);
  name the HF+SDPA backend in the f(N) caption; 588 vs static-565 floor sentence; name the
  three TSFMs in the conclusion; 5.60 vs 7-day parenthetical; Toto rounding 0.27→0.28.

---

## Confirmed-count by tier
P0 blockers: 8 · P1 factual: 12 · P2 scope: 13 · P3 nits: 11. **44 distinct confirmed
issues** after deduplication (from ~250 raw findings across six reviews). False positives /
overstatements are in `false-positives.md`.
