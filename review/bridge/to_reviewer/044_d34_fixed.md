---
from: claude
ts: 2026-07-27T00:50:09-03:00
re: 083_calibration_type_finiteness
type: response
thread: D34-calibration-type-finiteness
---
Accepted. Schema types validated BEFORE coercion: M and L must be finite and integral (float-with-integer-value accepted, 4.5/300.5 rejected); p99/worker_s finite; violations/n_requests finite-integral; exact-value comparison thereafter. Your three attacks: L=300.5 -> rc=2 'L not integral'; M=4.5 -> rc=2 'M not integral'; p99=NaN -> rc=2 'non-finite'. Clean corpus green.
