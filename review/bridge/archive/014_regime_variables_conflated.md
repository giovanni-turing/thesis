---
from: reviewer
ts: 2026-07-26T21:08:01-03:00
re: 009_rereview_request
type: finding
thread: D05-regime-variable-conflation
---

## Major — the regime table conflates startup delay, onset duration, and usable issue lead

The table defines `L` as replica startup lead and `T` as burst onset time
(`tex/conclusion.tex:84-91`), then assigns headroom placement to `L >= T`
(`tex/conclusion.tex:105-110`). Its own measured instance contradicts that
condition. Burst3 has `T=60 s`, while the factorial tests
`L={15,30,45,165} s` and reports the same standing-headroom mechanism across
all leads (`tex/closedloop.tex:325-341`). Three of four measured leads satisfy
`L<T`, yet the row would classify them outside headroom placement.

The evidence distinguishes a different quantity: usable forecast issue lead
`U`. Burst3 is headroom placement because `U` is zero/non-usable while the p90
band is already elevated; the classification is not caused by `L>=T`.

The adjacent burst4 value also needs threshold scope. Its `345 s` usable lead
is the coarse `thr_60s_224` result
(`simulation/results/rerun_verify/onset_audit_issuetime.json:275-303`).
At `thr_15s_286`, the same p90 path has only `15 s`
(`onset_audit_issuetime.json:367-395`). Burst4 remains a genuine anticipation
case, but `345 s` is not threshold-invariant.

A defensible regime rule must compare startup delay `L` with usable issue lead
`U` (and name the threshold used to define `U`), rather than compare `L` with
baseline-to-peak onset duration `T`.

