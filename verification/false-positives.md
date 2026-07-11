# False Positives & Overstatements — Six-Reviewer Verification

Claims from the six reviews that the tool-grounded verification **denied, downgraded, or
found already-addressed**. Each is kept out of the fix plan, with the grounded reason.
Compiled 2026-07-10.

## Outright false positives (deny)

**FP-1 [grok/fabel dispute] "993.8 ms is a p50 off-frontier cell."**
The grok verifier claimed the 993.8 ms figure was only a failing *p50* per-window cell.
**Wrong.** Direct recompute of `week_matrix/forecast_p90_timesfm_rho25_L300`: **993.829 ms
is the p90 TimesFM ρ25/L300 frontier point** (the p50 cells are 3768–6084 ms). Fabel was
right that it's a real frontier point — but it *passes* (<1000), so it is not a defect,
only a scoping nit (→ P2-6: quote the true loose end rather than Chronos-only 899).

**FP-2 [gemini] Holt–Winters "seasonality starvation" (misconfigured to a 1-hour season).**
Denied on code. `predictors/benchmark.py` adapts the seasonal period per resolution
(`HW_SEASON` = 900 s @1 s, 240 @15 s, …, chosen so two full cycles fit the 1928-step
context) and `holt_winters.py` hard-raises `ValueError` if `2·period` exceeds the data — no
silent degrade. HW is **not** starved of its *configured* seasonality. The real, milder point
(context-capped classical baselines never see a full *diurnal* cycle) is **already stated
verbatim** at `predictors.tex:384-390`.

**FP-3 [gemini] 149k-token extrapolation is unbounded / undisclosed.**
Denied. The disclaimer *and* the analytical bound Gemini asks for already exist:
`aiconfigurator.tex:182-186` states the extrapolation "tracks the theoretical quadratic of
attention within a few percent per octave," validated to 147k; `:476-480` discloses the
3.1%-of-requests scope. Recompute confirms 3.140% / max 148,569 tokens exact.

**FP-4 [gemini] The 245 s stall is a "critical failure / functional outage."**
Denied as framed. No outage: the archived live run *is* the Table-5.1 run (its aiperf p99
matches "Live 695" exactly), and planner logs show 10–15 s gaps. (The separate, valid point —
that the specific "245 s" figure is wrong (≈120 s) and lacks a root-cause note — is kept as
P1-11.)

## Already fixed before the reviews ran (no action)

**FP-5 [grok R1/D1] "both ITL p99 sub-bound" is false.**
The *fact* is correct (reactive ITL p99 = 150.7/160.3 > 100 ms bound), but the wording was
**already corrected** in commit `ba96acf` ("fix false 'both ITL p99 sub-bound' claim"); the
reviews predate the fix by minutes. Current tex reads "reactive above bound in both."

## Downgraded (real but over-graded; kept at lower severity)

**FP-6 [glm R5 / grok / gemini] "ARIMA absent from the benchmark prevents attribution."**
Downgraded major→minor. ARIMA *is* benchmarked (0.521@1min, 0.668@15s, in prose + Fig 8.1a),
and the closed-loop failure is explicitly attributed to *conversion*, not accuracy, via the
predictor-swap triad. The "reader can't tell" framing is wrong; only a presentational table
row is missing.

**FP-7 [glm R9] "14-config reactive claim is under-evidenced."**
Downgraded major→minor. All 14 configs exist as artifacts (`reactive32/`) with the exact
claimed 1,079–3,495 ms range; only the *summary table* is unprinted.

**FP-8 [codex B1 severity] "blocker."**
Downgraded to *at least major, arguably blocker*. If the encoder SLA is intended as
user-population p99 (text-only users genuinely contribute 0 encoder delay), the mixed
statistic is a legitimate metric choice — the defect is then the *wording* ("worst percentile
of vision-pool users") plus the 4/6 optima flip, not a computation error. Still must be
resolved; not necessarily fatal.

**FP-9 [codex B6] "no join can recover original arrival time."**
Overstated. The source index *is* recoverable via `hash_ids` (the verifier used exactly that
join for B1). The substantive claim — that no end-to-end ingress-to-first-token p99 is ever
computed — holds (kept as P0-6); the "impossible to recover" phrasing does not.

**FP-10 [codex R11/R14] Moirai "cross-frequency" term; FlashAttention dispatch / venue
labels.** Partial. The major sub-claims (BurstGPT 213 days; AIC already models the ViT via
`vit_ops.py`) are confirmed; a few minor sub-claims could not be locally re-verified and are
not carried.

## Judgment calls left to the author (not defects)

- **"Order of magnitude" knee** (P2-11) — technically ">10× under calibrated timing" is
  already in the text; the abstract-level "order of magnitude" is defensible. Listed as a
  conditioning suggestion, not an error.
- **k-means vs HDBSCAN** (gemini S2) — the archetypes are already flagged "weak separation,
  interpretive"; no re-run needed.
- **Single-trace generality** (P2-13) — inherent scope of a master's thesis; disclosed;
  tone-only.

**Net:** of ~250 raw findings, the only genuine false positives are FP-1–FP-4 (4 items);
FP-5 is already-fixed; FP-6–FP-10 are real findings the reviewers over-graded. **No
confirmed factual claim in any of the six reviews was wrong** — the disagreements are
severity, not fact.
