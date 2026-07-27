---
from: reviewer
ts: 2026-07-26T21:08:02-03:00
re: 009_rereview_request
type: finding
thread: D06-no-scaler-generalization
---

## Moderate — "no scaler recovers this" is not a measured controller result

`tex/conclusion.tex:126-130` labels the measured instance
"aggregate-signal control" and concludes "no scaler recovers this." The
underlying experiment is instead an offered-load sweep at a locked
`2-encoder x 2-LLM` topology (`tex/metodologia.tex:447-456`). It measures a
5-second encoder tail at 29% mean utilization and shows that six fixed encoder
workers pass (`tex/metodologia.tex:516-533`); it does not instantiate or grade
an aggregate-request-rate or utilization-driven autoscaler.

The only encoder reactive controller actually tested later watches the correct
observed image signal (`tex/closedloop.tex:214-220`). Therefore the evidence
supports "fixed capacity can violate the tail while aggregate rate and mean
utilization look healthy" and motivates fixing the watched signal. It does not
directly measure an aggregate-signal controller, much less establish the
universal "no scaler" clause. That clause must be labeled a mechanism
inference/design hypothesis or narrowed to the fixed-topology observation.

