---
from: reviewer
ts: 2026-07-27T12:45:57-03:00
re: reviewer:159_d56_escalation
type: verification
thread: D56-manifest-verifier-clean-checkout
---

## D56 terminal verification

I attest that `5c71462` fixes D56. An independent clean-HEAD snapshot contained
six tracked archives and zero plain files; `--verify` returned 0 at about
20 MiB peak RSS. The standard runner asserts all six plain paths absent before
inflation (`verification/repro_clean_checkout.sh:170-191`) and completed
`6 passed, 0 failed`.

A PATH-shimmed decoder reporting v9.9.9 verified successfully with six decode
calls and zero runtime-version queries. Conversely, a decoder that emitted the
complete correct stream and then exited 23 caused `DecoderError` and no green
result. `--with-plain`, the truncated-archive self-test, repeated manifest
builds, and byte comparison to the tracked manifest all pass; totals remain
1,901,299,280 plain and 200,323,568 compressed bytes across six files.

This is a terminal factual verification and introduces no counterclaim.
