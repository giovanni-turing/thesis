---
from: reviewer
ts: 2026-07-28T03:53:54-03:00
re: new
type: finding
thread: D88-equal-compliance-conclusion-pair
---

# D88 — RQ3 equal-compliance opening mixes in a failing comparator

The conclusion opens RQ3 as resource-time “at equal compliance,” correctly
gives the passing common-warm floor at 801.8 worker-hours, but then places the
shipped direct-reactive arm at 725.4 hours in the same comparison
(`tex/conclusion.tex:41-51`). That shipped direct-reactive arm fails burst3;
it is not an equal-compliance comparator.

The canonical equal-compliance pairs are:

- common warm: forecast 2,410,754.7 worker-seconds versus passing post-hoc
  $M=2$ at 2,886,614.5
  (`simulation/results/comparator_frontier/frontier_summary.json:1199-1206`);
- shipped strict re-warm: forecast 2,410,754.7 versus the first passing floor
  $M=6$ at 4,033,184.1
  (`simulation/results/comparator_frontier/frontier_summary.json:1181-1188`).

The shipped direct-reactive arm is explicitly a failing diagnostic
(`simulation/results/comparator_frontier/frontier_summary.json:1241-1243`).
Please either use the two readiness-specific passing floors in the
equal-compliance opening, or label 725.4 hours immediately as the failing
direct-reactive point outside that comparison.
