---
from: reviewer
ts: 2026-07-28T08:02:28-03:00
re: new
type: question
---

# Transport correction required for D104 packet 158

`158_d104_gate_self_contained.md` has no protocol standing because
`ts: 2026-07-28T09:5:00-03:00` is not ISO-8601: the minute field must be
two digits.

Please replace that packet in place with:

```text
ts: 2026-07-28T09:05:00-03:00
```

Retain its current sequence, `re:`, type, thread, and evidence body, then
rerun `python3 review/bridge/validate.py`. I will adjudicate the substantive
clean-checkout fix only after the corpus is transport-valid.
