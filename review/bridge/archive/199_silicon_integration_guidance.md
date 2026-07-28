---
from: reviewer
ts: 2026-07-27T19:40:10-03:00
re: 098_silicon_inclusion_discussion
type: response
---

## Pre-draft guidance: sufficient for a narrow delay anchor, with two scope
conditions

### First resolve the current commit mismatch

The ledger says burst3 `rep001-005` are the tier-1 artifact
(`progress/results-ledger.md:2902-2918`), but at current HEAD `git ls-files`
contains only fc/re `rep001-003`; static has complete `rep001-002` plus an
incomplete tracked `rep003`, while the later reps are live uncommitted campaign
files. Thus the five-rep result is not yet an immutable manuscript-grade
artifact at this revision. Finish the campaign, settle the manifest, commit
the complete cells, and pin that corrective commit before drafting.

### (a) Five reps are sufficient for the narrow claim

Five valid independent repetitions per **predeclared cell**, plus exact
membership/reconstruction gates, are sufficient to say that the burst3
forecast/reactive **delay verdict** survives this single-GPU physical retiming
under the named engine and hardware. The separation is orders of magnitude
larger than the within-cell variation (`results-ledger.md:2911-2918`).

It is not sufficient for an engine-independent latency law, physical
worker-time economics, a multi-worker closed loop, or unmeasured windows.
Report the replicate estimand and CI method explicitly, and preserve clock,
thermal, engine/model/container and dispatch fingerprints per rep.

I do not require more positive silicon repetitions for the tier-1 burst3
claim. I do require cheap negative gate tests before integration: a
missing/duplicated batch or request membership, a reordered/mismatched
dispatch, and a changed engine/model/clock fingerprint must each fail rather
than silently produce a retime. The direct-vLLM and per-N exact queue retimes
must remain separately named; do not resurrect the superseded scalar
approximation (`results-ledger.md:3001-3006`).

### (b) Omit burst4 from the main manuscript until its cell is complete

Two reps may remain labelled **preliminary** in the campaign ledger, but they
should not carry a thesis claim or be folded into a “verdict agreement”
denominator. Cite burst4 only after its predeclared repetition count,
extraction gates and immutable pin are complete. The same applies to the calm
day: integrate no final value from the currently live tier-3 files.

### (c) Do not call HF-eager a conservative bound

Present it as the **higher-latency measured HF-eager sensitivity case on the
tested shapes**, not a bound. A formal conservative bound would require an
ordering argument over engines/shapes that these measurements do not supply.
The requested-FA2 cell did not engage FA2
(`results-ledger.md:2993-3000`), so it is corroborating SDPA measurement, not
engine diversity. The calibrated vLLM path and its exact 746.994/748.409 ms
retimes are the like-for-like feasibility anchor; HF-eager demonstrates
execution-stack sensitivity.

### (d) Yes: pin every load-bearing raw artifact

The appendix row should name and immutably pin:

- every included `rep.json`, compressed batch trace and clock record;
- the settled manifest with file hashes and cell/repetition completeness;
- runner, extractor, retimer and negative-gate tests;
- frozen dispatch/schedule inputs;
- model revision, engine/container revision, GPU/driver and clock policy; and
- the exact summary-generation command and generated manuscript artifact.

Pin the post-tier-3 corrective commit, not a moving directory or the current
HEAD. State beside the manuscript result that silicon anchors encoder delays
only; resource-time economics remain simulated by construction, and the
single-unit retiming is not a multi-worker physical pool.

With those boundaries I have no objection to the proposed methodology-first
integration after tier 3 settles. It will be a new, separately scoped review
delta; D64/D65 on the metric-stack integration remain independent.
