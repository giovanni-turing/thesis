# Verification Evidence Pack (for the Phase-7 evidential-integrity trialogue)

## Method
Unit = claim. 227 data-verifiable claims (164 numeric + 63 comparative) extracted from the frozen thesis, anchor-verified. Each claim verified against the provenance Postgres DB (read-only) by paired CONFIRM/REFUTE reviewers (gemini-3.5-flash + gpt-5.6-sol), adjudicated on disagreement, and every flagged/split claim (91 total) re-derived FROM SCRATCH by an opus arbiter querying the DB directly. 18 figures visually verified vs captions + DB. All read-only; no thesis text edited.

## Definitive tally
```
PASS: 179
PASS-UNVER: 26
UNVERIFIABLE: 12
FAIL: 10
```
Clean (PASS+PASS-UNVER) = 205/227 (90%). Real defects = 10. Unverifiable = 12.

## Key epistemic fact
The fast reviewer pass flagged 85 potential failures; opus re-derivation overturned 75 as reviewer artifacts (wrong view / wrong scope / superseded rows), confirming only 10. The reviewers' false-positive rate was ~88%. This is the central evidential-integrity question: the THESIS's numbers held; the REVIEW process was the noisy element, corrected by from-scratch DB re-derivation.

## The 10 confirmed data defects (all have fixes in FAILURES.md)
- [overclaimed/major] twopool-0025 (twopool): v_pool_latency + llm_run_summary (g3_32b, is_current). 235b_tp8_s1 ITL p99 = 86.15097699995385 ms; 8b_tp1_s1 = 22.62208. Mean TPOT s=1: 14.70/7.76 = 1
- [overclaimed/minor] twopool-0062 (twopool): The 'misses on both fabrics at 24h' statement is policy-dependent: true for fc_L30/fc_L30_cap28 but false for fcAware and for the deployable static_C8
- [overclaimed/minor] twopool-0068 (twopool): The 24h steady window raises the rate from 2.879 to 5.326 img/req, still only 37% of the trace-wide 14.332. It moves toward the trace but does not res
- [contradicted/major] predictors-0173 (predictors): The Toto-2 fine-bin half holds (23/24 across 1s-30s). But Chronos-2 leads NEITHER coarse resolution: TimesFM leads 45s and Toto leads 1min. Chronos wi
- [overclaimed/major] predictors-0176 (predictors): Holds at the 1min resolution the claim quantifies: arima (0.5213) ties best classical ewma (0.5217) and trails best foundation toto (0.5153) by ~0.6 W
- [overclaimed/minor] intro-0197 (intro): The two quantitative anchors hold: CV2 ratio 11.93x supports 'an order of magnitude burstier', and 15.62x supports 'nearly sixteen times its weekly me
- [contradicted/major] baselines-0364 (baselines): The universal L*=45s for medium onsets is contradicted by burst4 (onset 60 min): it passes the 1000ms encoder-delay SLA at L=165s (p99 904.739ms, v_in
- [inconsistent/major] aiconfigurator-0382 (aiconfigurator): The table's predicted value (7.822) and ratio (1.45) are the SUPERSEDED earlier AIC data version; current provenance is 8.162 ms / ~1.39. Measured 11.
- [contradicted/major] closedloop-0395 (closedloop): burst3-at-every-lead holds, but burst4 does not lose beyond 45s: at the sole >45s realizable lead (165s) it passes at 904.74 ms < 1000 ms bound. Gemin
- [overclaimed/minor] closedloop-0425 (closedloop): Over the exact scope the claim names (the a2x archive episodes, leads 15-165s), cost is not invariant: it falls monotonically ~6% from L=15 to L=165. 

## Systemic patterns
- RECURRING FACT ERROR: baselines-0364 + closedloop-0395 both state reactive/medium onsets lose 'beyond 45s' but burst4 passes at L=165s (904.7ms). One underlying fact wrong in >=2 places.
- SUPERSEDED TABLE ROW: aiconfigurator-0382 quotes an older AIC version.
- SCOPE-SENSITIVE OVERCLAIMS: several (predictors-0176, twopool-0025, closedloop-0425) hold at one scope/resolution but are stated universally ('throughout','all four','lead-invariant').
- DB LOADER GAP (NOT a thesis defect): apendice-0138 — thesis value 232.0 correct; the DB ingested a contended-invalid row. Also 2 claim-inventory expected_backing mislabels.

## 12 unverifiable claims
Causal-necessity or no DB backing — not derivable from observational run data. These are honesty-of-scope items, not errors.

## 3 figure flags (caption/label cosmetics; data reconciles)
- sim_knees: Terminology inconsistency between plot and caption/table: the figure legend and right-panel annotation label the blue window 'head
- eda_l_request_clusters: Caption color mapping is incorrect. Caption states the two text archetypes are '(blue, orange)' and the two vision archetypes '(gr
- pred_framework_diff: Panel (a) bar values do not match forecast_metrics and flip the naive-vs-HoltWinters ranking. Panels (b)/(c), which carry the load

## Methodological observation
Thesis has NO displayed equation environments; metrics (WAPE, cost ratio, coverage, infraction) defined inline/prose. Defensible for a systems thesis; an examiner may want headline formulas displayed.