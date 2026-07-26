# Non-Data Claim Verification (methodological / existence / causal / citation / behavioral)

242 non-data claims verified by opus subagents against **code, artifacts, the provenance DB, git/gh, and the cited PDFs** (`papers_cited/`). Read-only; no thesis text edited.

## Tally

| type | n | result |
|---|---|---|
| methodological | 102 | supported 100, unverifiable 2 |
| existence | 91 | supported 90, contradicted 1 |
| causal | 36 | supported 36 |
| citation | 8 | supported 8 |
| behavioral | 5 | supported 4, overclaimed 1 |

**Overall: supported 238, unverifiable 2, overclaimed 1, contradicted 1** (242/242)

## Findings (non-supported)

### `related-0292` — behavioral — OVERCLAIMED
- **evidence**: related.tex:186-195 lists Azure/Splitwise, DynamoLLM, BurstGPT, ServeGen, Aegaeon then asserts 'All are text-centric: their request descriptors are token counts and timestamps.' Verified against PDFs: Splitwise (Sec IV-A) trace = arrival time + input tokens + output tokens (accurate); DynamoLLM (Sec II) = invocation timestamp + input/output tokens, a super-set of Splitwise (accurate); BurstGPT (Sec 2) = start time + request/response token lengths + service-type + model-type tags, no image data (essentially accurate). BUT ServeGen (Xiang2025ServeGen, Sec 4, Table 1, Fig 7/9) is a counterexample in the same list: it models genuine multimodal descriptors -- number of multimodal inputs per request, tokenized image/audio/video lengths, image-to-input token ratios, per-client image-data distributions -- across Language/Multimodal/Reasoning categories, and the thesis's own preceding clause even notes ServeGen composes 'per category rather than as one stream.' So the universal 'All ... are token counts and timestamps' is contradicted for ServeGen; it holds for the other listed traces.
- **fix**: Weaken the quantifier: e.g. 'The public production LLM-serving traces (Azure/Splitwise, DynamoLLM, BurstGPT, Aegaeon) are text-centric -- token counts and timestamps.' Treat ServeGen separately, noting it models per-category multimodal descriptors but as a synthetic generator, not a released production trace -- which keeps the later 'first public production multimodal trace' (ModServe) claim intact.

### `apendice-0130` — methodological — UNVERIFIABLE
- **evidence**: matplotlib 3.11.0 is not recorded in any artifact, EDA metric, or DB column. Figure-generation scripts (e.g. collector_artifacts/phaseE_physical_anchor/make_engine_fig.py) import matplotlib but no version is captured. provenance/audit/reverify/apendice.json:9 also marks the matplotlib 3.11.0 entry UNVERIFIABLE (no software-version columns in provenance schema). It is an env-lock declaration, uncontradicted but not independently checkable.
- **fix**: None strictly needed; optionally stamp matplotlib.__version__ into a figure-manifest for auditability.

### `closedloop-0402` — existence — CONTRADICTED
- **evidence**: The predictor-swap phenomenon (ARIMA/Kalman/Prophet -> identical SLA verdict, distinct_schedules=1, all FAIL) exists and is backed by /home/gio/tese/simulation/results/predictor_closedloop_v2/analysis_summary.json and DB v_infraction experiment='closedloop_v2' (3 predictors x 2 metrics, identical p99_ttft=1111.74ms all is_violation=t). BUT the actual experiment windows are steady24h and burst4, NOT burst3. The run_one.sh/README.md state explicitly the prior burst3 run was DISCARDED as invalid ('metric saturation ... predictor collapse ... too little history'); no valid burst3 predictor run exists. Also burst4 is the SLOW/gradual onset (README: 'slower 60-min onset'), so the anchor's 'fast onset, burst3' is doubly wrong.
- **fix**: Change 'burst3' to 'burst4' and drop 'fast onset' (burst4 is the slow onset); the all-predictors-fail-identically result holds on burst4 and steady24h, not the discarded burst3 run.

### `apendice-0129` — methodological — UNVERIFIABLE
- **evidence**: The chronos model is used (model='chronos' rows throughout simulation/results/cells_44_wave1.jsonl, cells_week.jsonl), corroborating that Chronos forecasting was run. But the specific package version chronos-forecasting 2.3.1 is not recorded in any artifact, forecast metric, or DB column (no software-version columns beyond torch/cuda/python). The version is an env-lock assertion only; provenance reverify note (provenance/audit/reverify/apendice.json:9) also flags this version line as UNVERIFIABLE.
- **fix**: Capture chronos-forecasting package version in the forecast-run metadata (report.json/stats) so it is auditable; otherwise soften to an env-declaration.
