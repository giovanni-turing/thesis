---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D102-zero-shot-trace-history-definition
---

# D102 — “Zero-shot” does not mean the forecaster receives no trace history

The new definition says zero-shot entails “no trace history”
(`defense/defense-qa.tex:1918-1923`). That contradicts the actual protocol.
Each origin predicts from a historical context window, and every model
forecasts each signal from its own history (`tex/predictors.tex:56-77`).
Indeed, the first 1.4 days are consumed as rolling history before the first
usable forecast (`defense/defense-qa.tex:1088-1094`).

What is zero-shot here is the absence of target-series fitting/fine-tuning and
per-signal hyperparameter training, not the absence of inference context.
Please replace “no trace history” with language such as “no fitting or
fine-tuning on the target trace beyond the historical context supplied at
inference.” “What an operator gets on day one” should likewise not imply a
cold start without the context window the protocol requires.
