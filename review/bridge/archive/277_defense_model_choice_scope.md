---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D87-defense-model-choice-scope
---

# D87 — “The forecaster barely matters” needs within-TSFM scope

The defense answer says the forecaster barely matters, is second-order
everywhere measured, and that information was never scarce
(`defense/defense-qa.tex:1548-1561`). The evidence supports a narrower result:
choice among the three tested TSFMs is second-order after capacity
quantization. It does not establish that forward information or forecast shape
is irrelevant.

The tested forward-EWMA alternatives are outcome-relevant. On burst3,
additive and width-scaled EWMA bands fail at p99 1284.808 and 2083.83 ms,
while multiplicative EWMA passes only with substantially more standing work
(`verification/results/ewma_baseline_burst3.json:1-150`). The manuscript's
own operational conclusion is that the calibrated upper-edge shape is
load-bearing, not merely the identity of the TSFM.

Please scope the defense statement explicitly: model choice *among the three
tested TSFMs* is second-order; the state-adaptive forward band remains
load-bearing relative to the tested EWMA calibrations. “Information was never
the scarce resource” should not survive unqualified.
