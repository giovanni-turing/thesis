---
from: reviewer
ts: 2026-07-28T04:07:35-03:00
re: new
type: finding
thread: D95-defense-tsfm-scope-duplicates
---

# D95 — TSFM-scoped model-choice result remains universal elsewhere

The newly corrected answer properly says choice among the three tested TSFMs
is second-order while forward-band shape versus EWMA is outcome-relevant
(`defense/defense-qa.tex:1575-1597`). Earlier answers still say that any
“model X” demonstrably would not matter and that the forecaster sets cost, not
SLA (`defense/defense-qa.tex:320-333`), or that the SLA is decided “not [by]
the model” in the explicit foundation-model-versus-EWMA comparison
(`defense/defense-qa.tex:808-820`).

Those statements contradict the tested EWMA outcome split already acknowledged
by the corrected answer: additive and width-scaled EWMA fail burst3, while the
multiplicative variant passes only with substantially more standing work.

Please apply the same scope globally: identity among the three tested TSFMs is
second-order after capacity quantization; the band family/shape remains
load-bearing relative to the tested EWMA calibrations. Do not answer an
open-ended “why not model X” with evidence from only the three TSFMs.
