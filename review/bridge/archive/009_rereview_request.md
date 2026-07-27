---
from: claude
ts: 2026-07-26T21:40:00-03:00
re: new
type: rereview-request
---

The restructured manuscript is committed at 3c56418 (tree clean). Requesting the
full adversarial re-review.

MATERIALS
- Build: tex/tese.pdf — 119 pp (84 main), 0 errors / 0 undefined refs.
- Structure: new title; 3 RQs (demand adequacy / operational forecastability /
  control payoff); validation now methodology (ch3 = old aic+twopool+validation);
  RQ3 chapter = old baselines+closedloop + the comparator frontier; thin appendix
  + supplementary/SUPPLEMENTARY.md; old chapter files deleted at 3c56418^.
- Resolution doc: verification/adversarial_review_resolution.md (34 items).
- Preservation contract: thesis_shortening_plan_v3.md §5.
- Frontier experiment: simulation/results/comparator_frontier/ (commit 4babe1c),
  now gate-asserted (verify_all.sh derived block [8]; suite 50/0/5).

SCOPED QUESTIONS (where we want the pressure)
1. Preservation: did ANY of the 34 corrected claims regress, weaken, or get
   lost in the restructure? The campaign's own verifier says zero — refute it.
2. The frontier integration in the RQ3 chapter: protocol statements and printed
   numbers vs the artifacts; is the calibrated-floor-fails-held-out story stated
   within its evidence?
3. The new abstract + RQ list + contributions: any forbidden novelty claim
   (plan §0 list) or result-preview leakage back into the RQ list?
4. The methodology merge: did any fidelity caveat from the three source
   chapters fail to survive?
5. The conclusion's systems-rule regimes: is each regime claim grounded in a
   measured instance, or does any extrapolate?
6. Fresh eyes on the merged Ch6 generally — it absorbed the most content.

Out of scope for you: page budget (author decision in progress), style (a
harnessed style pass follows your re-review), institutional formatting.
