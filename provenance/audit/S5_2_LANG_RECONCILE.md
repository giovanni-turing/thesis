# §5.2 reconciliation — language-pool static dominance, revisited under honest calibration

**Status: PROPOSED (2026-07-25). Does NOT amend `DELIVERY_RULING.md` §5.2 — it proposes the amendment.**
DB-backed: the 16 eval-span + 70 calibration runs are ingested under `experiment='langcalib'`
(`provenance/loader/load_langcalib.py`); the numbers below are queryable via `v_pool_latency` and
`llm_run_summary.gpu_hours` (real quantile in `config->>'forecast_quantile'`, scale in
`config->>'forecast_req_scale'`). Fold runs (F1–F7) remain artifact-only (their window names aren't in
`windows()`). Pending (a) author adoption into the thesis, (b) the actual §5.2 / cl-llm / abstract
amendment. Backing: `progress/results-ledger.md` "Language-pool operating point" entry (2026-07-24) +
addenda 1–4 (2026-07-25); artifacts under `simulation/results/lang_qsweep/`.

## What §5.2 ruled, and on which operating point

`DELIVERY_RULING.md` §5.2 (lines 594–610): *"no language-pool cost advantage may be claimed for
forecasting anywhere in the thesis or the defence."* Evidence:
- **G1** (burst2, burst6): static C=8 passes at 7.60 / 5.47 GPU-h — **2.9×–4.9× cheaper than every forecast cell.**
- **G4** (7 folds): static passes all seven; the forecast arm costs **1.02×–3.81×** in six of them.

**Both were measured on the PUBLISHED forecast point: Chronos p90, `FORECAST_REQ_SCALE=8` (p90/s8).**
That point stacks two headroom sources (p90 quantile *and* scale 8); the calibration below shows scale 8
is wasteful.

## New evidence — honestly-calibrated operating point (held-out)

Operating point *selected* on the 1.4-day forecast-context split only (burst2 + burst6, expctx archive;
burst6 = 1-min onset), then *evaluated held-out* on the eval span. Full method + numbers in the ledger.

**5.60-day span (749,601 req, standard archive), per-episode graded:**

| point | week GPU-h | vs static (time) | vs static (req) | per-episode incl. e13 |
|---|---:|---:|---:|:--|
| p70/s6 (aggressive) | 330.4 | 0.615× | 0.656× | **fails e13** (F6 1134 ms), masked in aggregate |
| **p90/s6 (e13-robust)** | **440.0** | **0.819×** | **0.874×** | **passes all** (F6 886 ms) |
| published p90/s8 | 518.6 | 0.965× | 1.030× | passes all |
| static TP2×2 | ~537 | 1.000× | — | passes all |

**Per-fold (§5.2's own lens), p90/s6 vs static (=1.00×):** F1 0.96 · F2 0.69 · F3 0.73 · F4 1.42 ·
F5 0.66 · F6 0.71 · F7 1.68 — **cheaper than static in 5 of 7 folds** (vs the published p90/s8's 1 of 7),
above parity only on the two heaviest burst folds (F4, F7). On the e13 fold (F6) specifically, p90/s6
**passes at 0.71× static** — where §5.2 noted the *encoder* forecast arm fails and needs static C=5.

## Reconciliation

1. **§5.2 was correct for the point it measured (p90/s8).** That arm is over-provisioned; static dominates it.
2. **Under honest calibration the absolute claim softens.** The e13-robust calibrated point (p90/s6)
   **beats static on the 5.60-day span under BOTH denominators (0.82× / 0.87×)** and in **5 of 7 folds**,
   while passing every episode incl. e13. So *"no language cost advantage may be claimed anywhere"* is
   **modestly overturned**: a modest, e13-robust advantage exists.
3. **But §5.2's caution largely holds in spirit.** The advantage is **modest** (0.82–0.87×, not the
   encoder's 0.62×), **day-to-day fold-variant** (above parity on F4/F7), and the only way to reach the
   bigger 0.62× (p70/s6) is to **drop the e13 fold** (masked in the aggregate — the same dashboard-masking
   the thesis warns against, and the same onset the encoder headline also drops).

## Proposed amendment (pending adoption)

- **`DELIVERY_RULING.md` §5.2:** scope the ruling to the *published p90/s8 arm*. Replace *"no language-pool
  cost advantage may be claimed anywhere"* with: *"the published p90/s8 language arm is static-dominated;
  an honestly-calibrated e13-robust point (p90/s6) modestly beats static (~0.82–0.87× over the covered
  span, 5/7 folds), but the advantage is modest and fold-variant, and the larger 0.62× (p70/s6) requires
  dropping the e13 fold."*
- **`cl-llm` / abstract / RQ4:** the language pool is a **modest ~0.85× e13-robust cost win** (not the
  encoder's 0.62×), with an aggressive 0.62× available only if the e13 episode is dropped. The
  *"encoder buys savings, language buys compliance"* framing softens to *"encoder buys savings; language
  buys compliance plus a modest saving once scale-8 over-provisioning is removed."*
- **Unchanged:** the encoder RQ4 result (0.62×) — §5.2 already ruled it unaffected, and it remains so.

## Open items before this is thesis-grade

1. **DB ingestion — DONE** (`load_langcalib.py`, 86 runs, `experiment='langcalib'`). Fold runs (F1–F7)
   still artifact-only; ingesting them needs F1–F7 added to `windows()`. Separately, note the store's
   pre-existing **C305** physical-partition-misfile failure (unrelated to this load — see ledger addendum4).
2. **p90/s5 knee** (untested) could shave the robust floor slightly (~0.82× → ~0.78×).
3. A **language static denominator in `v_cost_ratio`** (currently encoder-focused) so the 0.82×/0.87×
   ratios are view-computed, not hand-divided by the 537.4 GPU-h TP2×2 reference.
