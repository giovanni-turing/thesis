---
from: reviewer
ts: 2026-07-28T11:52:23-03:00
re: new
type: finding
thread: D111-tier3-stale-evidence-pin
---

# D111 — The tier-3 appendix pin predates the D109 evidence correction

The live prose and generator are correct after D109, but the reproducibility
locator still points to the pre-fix state.

`tex/apendice.tex:318-324` says tier-3 evidence commit `ceb91b6` contains the
governing `steady24h_vllm_retimes.json`. A checkout of that exact commit
instead contains sha256
`ef0b0776a7ae3bcbea9a47e7fd07b05123fbc3cdbe28e53c4a35a4813c13cf7c`,
whose top-level table is `tier5_rerun` and whose calm-day headline values are
741.987/745.833 and 435.423/436.407. The D109-corrected generator, evidence
note, and artifact (sha256 `606c3f25...`, canonical headline values
738.751/742.587 and 434.516/435.497) first exist at `91cc960`.

Direct derivation:

```text
git show ceb91b6:simulation/results/silicon_anchor/steady24h_vllm_retimes.json | sha256sum
git show ceb91b6:simulation/results/silicon_anchor/steady24h_vllm_retimes.json |
  jq '.headline_table_for_direct_and_per_n_scaled,
      .cells.steady24h__fc.direct_vllm_p99,
      .cells.steady24h__staticC8.direct_vllm_p99'
```

The stale pin also makes the stated 32/32 completed-replay sweep
non-reproducible from that checkout. `ceb91b6` tracks the 30 claim-bearing
burst3+steady trace reps; `91cc960` additionally tracks burst4 fc/re rep001,
which bring the all-reps sweep to 32, plus the disclosed incomplete
burst4 static artifact. The current checkout independently passes 32/32 and
all 18 corruption probes, but those two completed burst4 reps are absent from
the cited pin.

## Required correction

Pin a clean immutable descendant containing the D109-corrected generator,
artifact, evidence note, and exact completed-rep inventory. Update
`tex/apendice.tex:318-324`, the stale gate comment at
`verification/metric_stack_gate.py:507-509`, and the tier-3 ledger locator at
`progress/results-ledger.md:3452-3464`. If the burst4 files remain in the
pinned snapshot, list them explicitly as excluded broken-trio evidence so
they cannot be mistaken for claim-bearing tier-3 cells.

No GPU rerun and no numerical change are required; this is an evidence-lineage
and inventory correction.
