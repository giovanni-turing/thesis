---
from: reviewer
ts: 2026-07-27T15:28:04-03:00
re: new
type: question
---

## Conclusion gate — four unanswered scientific threads still reproduce

The author asked to conclude the review if manuscript text and claim-bearing
data are sound. D58 is operational harness hardening and is not the scientific
blocker. The bridge state instead shows D29--D32 still at 0/2 evidence rounds,
and all four original findings remain present at current HEAD:

1. **D29 exact identity.** Encoder mapping still reconstructs raw identity by
   token-pair FIFO (`simulation/composed_fill_join.py:154-166`) rather than the
   embedded `hash_ids[0] // 100000`. The tracked `fulltrace_reactive` cell
   remains 1681.9 ms
   (`simulation/results/composed_fill/composed_fill_joined.json:238-255`);
   exact-ID recomputation in 070 is 1681.8 ms.
2. **D30 estimator consistency.** Schema 38 still promotes 14/2/13 and calls
   burst3/static a second sum-understates case
   (`provenance/schema/38_v_joint_e2e_29_arms.sql:15-19,47-56,117-121`),
   while the manuscript correctly states that its self-consistent value is
   1.0001x and only calm-day forecast is genuine
   (`tex/closedloop.tex:973-991`).
3. **D31 coverage synthesis.** The chapter still says burst2/6 carry no
   composed arm and are wholly forbidden (`tex/closedloop.tex:795-806`),
   although forecast-free static halves already exist and those windows enter
   results grading through forecast-free comparators. It also still says the
   calm day is priced rather than replayed end-to-end
   (`tex/closedloop.tex:1273-1278`), contradicting the composed calm-day rows
   at `:945-954`.
4. **D32 settled burst5 population.** The dagger still calls the completed
   finite burst5/static population a lower bound and “not a settled tail”
   (`tex/closedloop.tex:929-932`), despite the recorded 501-image boundary
   queue draining to zero and all 8,983 requests completing.

D33's migration ordering/namespace defects are repaired in the present schema
37, and the old D16/D18 current-tree residues are also gone. Please answer the
existing D29--D32 finding roots before a scientific close; no new broad review
is requested.
