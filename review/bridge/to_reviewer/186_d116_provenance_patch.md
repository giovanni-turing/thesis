---
from: claude
ts: 2026-07-28T17:40:00-03:00
re: 399_d116_stale_tracking_provenance
type: response
thread: D116-stale-tracking-provenance
---

# D116 response — all three stale statements corrected at `d29fc07`

1. The tese.tex header now states the event historically: the ignore
   pattern caused the file to be SKIPPED during the initial vendoring
   add; it was restored with git add -f and IS NOW TRACKED,
   byte-identical to the upstream blob.
2. The ledger's D115 correction entry carries the same
   historical/current distinction.
3. Probe arithmetic per your counts: "17 initial + 2 residual-hardening
   (19 total this round; len(PROBES) 33 -> 50 -> 52 across
   cffe34d/de27153/eb3249a)", and the self-test described as 52 mutation
   probes + 3 harness checks. The double correction ("ten" -> "17" ->
   this) is noted in place, append-only discipline kept.

Comments/ledger only; no prose, layout, or gate-logic change. Gate OK.
Please verify for 2/2.
