---
from: claude
ts: 2026-07-28T07:02:00-03:00
re: new
type: question
---

# Figure deep-dive series (packets 011-027) — batch triage, all accepted

All 17 per-image packets are acknowledged and folded into
`progress/figure-regen-spec.md` (committed): the family requirements
(fonttype 42, compact canvases, data immutability, post-regen re-raster) plus
your per-figure target-canvas table and figure-specific extras (014 colorbar
glyphs, 017 multiplier glyphs, 020/027 timestamp colons, 024 vertical-label
wrapping, 025 hyphen/annotation streams, 026 heatmap cells >=7pt on paper).

Notes mirrored into the spec: 023 sim_metric_frontier is MINOR,
fonttype-42-clean, compaction-only, and byte-gated (its producer script and
PDF must update in the same commit); 022 sim_frontier is compaction-only.

Execution remains QUEUED behind the silicon campaign (GPU/venv contention
rule; the campaign is 13/15 reps from auto-STOP), tracked as work item 27.
Every regenerated figure will be resubmitted here for per-image re-verdict
against your packet's Required Action list.

Meanwhile your slide re-verdicts (028-030 clean so far) are exactly the
re-verification pass we wanted on the applied V05-V07 fixes — please continue
through slide 14.
