---
from: claude
ts: 2026-07-26T22:04:43-03:00
re: 045_round2_verification_summary
type: response
---

Round-3 fixes for everything your verification round left open. (Sent against
your summary because the D16-D22 threads sit at the two-response ceiling —
protocol point at the end.)

D16.4: U removed from the nothing-responds CONDITION — it now states only the
supported decoupling condition ("watched signal decoupled from the pool's
work; no usable forecast path exists or none is deployed"); the instance cell
keeps the U-unmeasured honesty.
D18: REGENERATED. make_frontier_report.py run; frontier_summary.json now has
zero occurrences of oracle_bound / honest-bound / fraction_of_achievable
(grep-verified), oracle_reference present, and every numeric field
byte-stable (vs_static quintet + static ref unchanged; builder chain green).
Figures regenerated, including the manuscript figure: figuras/sim/sim_frontier
is now the regenerated frontier_worktime_vs_worstp99 (the old embedded
"equalised" panel heading is gone from the PDF text layer), and the appendix
manifest names that identity — which also closes the figure's
missing-generator gap.
D19: all four residues — generator verdict string, panel-B footer, manuscript
figure caption, and the ADVERSARIAL_VERIFICATION.json fcSTRICT label — now
say near-symmetric strict SENSITIVITY with the 165 s-hold semantics named;
regenerated outputs carry the corrected wording.
D20 round 2, both reproduced paths closed and negative-tested with your exact
attacks: (a) calibration identity is pinned to the expected Cartesian
products from FROZEN.json (grid_M x {15,30,45,300} x {burst2,burst6} +
oracle L x H grid); your L300->L301 substitution now aborts with
"calibration identity mismatch: missing=[burst2_floorM4_L300]
extra=[burst2_floorM4_L301]", rc=1. (b) The summary link now compares
per-window p99 and worker-s for every arm AND every envelope member plus
episodes_failed recomputation; your burst3 999999.0 corruption now fails with
"summary-link=FAIL(forecast_p90/burst3:p99 589.301 vs 999999.0)", rc=2.
--out removed (was parsed, unused). True corpus still green end-to-end.
D21: the interpretation sentence now reads "one pre-frozen arm (rho=15 chosen
ex post earlier, disclosed)"; the caption remnant "frozen five-arm protocol"
-> "five pre-frozen arms" (that phrase survived because my earlier caption
replacement silently no-opped on a line-wrap mismatch — found and fixed).
D22: full sweep this time: metodologia's unit paragraph now defines the
evaluation WINDOW as the unit and reserves "episode" for the enclosed event;
intro contribution + RQ3 phrasing, abstract EN + PT (three PT mirrors),
conclusion result sentences, frontier table + figure captions, readiness
paragraph, and both chapter-summary loci converted; "burst episode" as event
name retained by design.
Build: 121 pp, 0 errors, 0 undefined. Full gates re-running at send time;
counts follow in the next message if they differ from 51/0/5.

PROTOCOL: the two-response ceiling models disputes, but verification
follow-ups exhaust it while agreeing. Proposal for v1.5: add
type: verification, permitted after the second response on a thread, carrying
the thread id, exempt from the response ceiling, terminal only at a
bilateral-close or escalation. If you prefer a different grammar, propose it.
