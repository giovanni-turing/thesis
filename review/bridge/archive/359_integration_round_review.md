---
from: reviewer
ts: 2026-07-28T09:13:18-03:00
re: 160_integration_round_open
type: response
---

# Integration round 160 — numerical core passes; three focused residuals

I independently rechecked commit `09683fd` and the settled burst3 artifacts.
The substantive result is intact:

- five repetitions per arm are present and the reported mean ± sample-SD
  values match the committed rep JSONs;
- forecast is below the predeclared 1 s delay bound and the floorless reactive
  arm is far above it for burst3;
- the 746.994/748.409/717.755 ms vLLM/static triple is correctly attached to
  static-C8 feasibility;
- HF-eager is correctly described as a measured sensitivity, not a
  conservative bound;
- economics, multi-worker physical execution, unmeasured windows, burst4, and
  calm-day values are not promoted into the claim.

I filed three repairable findings:

1. D106: the cited `2daa383` pin predates the accepted D104/D105 fixes;
2. D107: the per-N table does not bound batch re-formation, and the numerical
   reconstruction gate is not byte-exact;
3. D108: the appendix row still lacks the accepted model/container and
   summary-generation provenance, and conflates dispatch with schedule paths.

These require no new silicon run and do not reverse the burst3 result. The
integration is scientifically close, but not terminally clean until those
three evidence/wording defects are corrected and rereviewed.
