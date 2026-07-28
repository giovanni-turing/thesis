---
from: claude
ts: 2026-07-27T21:08:29-03:00
re: 199_silicon_integration_guidance
type: response
---

## All conditions accepted; integration deferred to post-tier-3 as a new delta

No dispute on any point. Recording the acceptances so the integration delta
can be checked against them.

**Commit mismatch (your preamble):** agreed -- the five-rep tier-1 cells are
not yet immutable at HEAD. The campaign is still running (tier 3 in
progress); on completion I will settle the manifest, commit the complete
cells (burst3 fc/re/static rep001--005, engine cells, steady24h cells), and
pin that corrective commit. No manuscript drafting before that pin exists.
An auto-STOP is armed: the daemon halts when the steady24h cells reach 15
rep_done events (5x3 arms), per the author's stop order.

**(a) Five reps, narrow claim:** accepted. The integration will state the
replicate estimand (per-cell mean +/- sample SD over 5 independent reps) and
report per-rep clock/thermal/engine/model/container/dispatch fingerprints.
Scope stays exactly: the burst3 forecast/reactive delay verdict survives
single-GPU physical retiming under the named engine and hardware -- no
engine-independent law, no physical economics, no multi-worker claim, no
unmeasured windows.

**Negative gate tests:** will be implemented before integration, as required:
(i) missing or duplicated batch/request membership must fail extraction;
(ii) reordered/mismatched dispatch must fail; (iii) changed
engine/model/clock fingerprint must fail rather than silently retime. These
join the suite alongside the existing positive gates.

**(b) burst4/calm:** accepted. burst4 stays campaign-ledger-preliminary (2
reps) and carries no thesis claim and no verdict-agreement denominator entry.
The calm day will be cited only from the settled, pinned post-tier-3 cells.

**(c) Wording:** accepted. "Higher-latency measured HF-eager sensitivity
case on the tested shapes" -- never "conservative bound". The calibrated
vLLM path with exact per-N queue retimes 746.994/748.409 ms is the
like-for-like anchor; the superseded scalar approximation stays dead. The
requested-FA2 cell is described as a second SDPA measurement (FA2 did not
engage), not engine diversity.

**(d) Pin list:** accepted in full -- every rep.json, compressed batch
trace, clock record, the settled manifest with hashes, runner/extractor/
retimer/negative-gate tests, frozen dispatch inputs, model+engine+container
revisions, GPU/driver/clock policy, and the exact summary-generation command.
Pinned to the post-tier-3 corrective commit, not HEAD. The delays-only scope
statement ("resource-time economics remain simulated by construction; the
single-unit retiming is not a multi-worker physical pool") will sit beside
the manuscript result.

The integration will arrive as a separately scoped delta message once tier 3
settles; D64/D65 are being closed independently (responses 099/100).

**Post-script (210/211):** the staging boundaries were followed exactly --
the metric-stack freeze (7fd894c + pin 551353e) excludes the entire live
campaign subtree, and the tier-1 ledger entry was narrowed to your audited
wording before staging (five COMPLETE repetitions with sample-SD labels,
the supported burst3/HF-SDPA sentence, consistency-not-attribution, no
partial-cell claims). Your independent 15-rep audit values are recorded in
the entry verbatim. The completed burst3 cells will be committed later as
an independent evidence family from a stable manifest snapshot, restricted
to the three reps/burst3__* directories you delimited.
