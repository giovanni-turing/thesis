---
from: claude
ts: 2026-07-28T00:57:31-03:00
re: new
type: ack
---

## Micro-delta notice: tab:cl-ledger-enc caption states the forecast-free protocol rule

Author, reading Table 6.8 cold, hit the intended question ("where is the
forecaster in the full-trace rows?") because the context-leakage rule
lives only in the prose above. The caption now states it in place: the
full-trace rows are forecast-free by protocol (the trace's first 1.4 days
are the forecaster's own context; full-trace forecast cells would leak
that context into the graded span), with forecast arms graded on the
forecast-covered evaluation span. One caption sentence; no number, claim,
or protocol change; gate OK; build 0/0 at 127 pages; immutability
rebaselined. Commit hash follows the pinned freeze (this is a
post-676992c reader-clarity delta under the standing scope boundary).
