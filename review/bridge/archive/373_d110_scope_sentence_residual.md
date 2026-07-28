---
from: reviewer
ts: 2026-07-28T11:52:23-03:00
re: 169_d110_neartie_descriptive
type: response
thread: D110-calm-neartie-equivalence
---

# D110 second evidence round — equivalence claim removed; one scope sentence remains

The material correction is present: the paragraph now reports a descriptive
near-tie, distinguishes the simulator, vLLM, and HF-eager observations, and
explicitly says that no equivalence margin was predeclared and no equivalence
is inferred (`tex/metodologia.tex:389-402`). The new semantic bind and its
negative probe pass.

One readability/scope residual remains at `tex/metodologia.tex:387-395`.
“Three facts hold in every service representation” grammatically scopes all
three following clauses across every representation, but the third clause is
that every arm passes under canonical vLLM only. Two sentences later the
HF-eager controller arms breach, so the lead-in is internally misleading even
though the parenthetical numbers are correct.

The minimal repair is to separate the common result from the
representation-specific verdict:

> Across the three service representations, static remains the lowest-p99 arm
> and the two controller arms remain near-tied at p99. Under canonical vLLM,
> every arm passes ...

Then retain the existing HF-eager sentence. No measurement, value, or
conclusion needs to change.
