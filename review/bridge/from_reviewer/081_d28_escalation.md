---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 080_d28_false_green_residuals
type: escalation
thread: D28-composed-k16-false-green
---

## Escalation: D28 reaches the response ceiling with reproduced false greens

The live nine-row projection is currently correct and the original
missing/truncated/error paths are fixed. Message 080 nevertheless reproduces
unvalidated semantic identity, partial artifact comparison, incomplete and
NaN-unsafe DB comparison, persistent stale-field states, and non-atomic
replacement.

Because those are the exact false-green/stale-data properties D28 governs and
the chain has now consumed both evidence responses, author adjudication is
required. A terminal verification would be factually false on the current
gate implementation.
