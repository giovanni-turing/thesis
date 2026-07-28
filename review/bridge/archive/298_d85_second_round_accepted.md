---
from: reviewer
ts: 2026-07-28T04:40:14-03:00
re: 131_D85_closed
type: response
thread: D85-encoder-violation-fraction-available
---

## D85 second round — accepted

Verified at `849ffd7`: the body reports the available request-count
fractions (189/3093 on burst3; 2650/3299/599 full-span counts) and correctly
states that per-request delay is reconstructable from raw completion minus
arrival (`tex/closedloop.tex:1157-1170`). The unavailable quantity is now a
wall-clock statistic lacking a declared aggregation convention, not missing
request-level instrumentation. No D85 counterclaim remains.
