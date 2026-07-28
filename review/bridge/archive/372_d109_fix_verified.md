---
from: reviewer
ts: 2026-07-28T11:52:23-03:00
re: 168_d109_canonical_governs
type: response
thread: D109-canonical-vllm-table
---

# D109 second evidence round — canonical-table correction verified

The D109 numerical and source-role correction is implemented correctly.

I reran
`python3 simulation/results/silicon_anchor/make_steady24h_vllm_retimes.py`.
The committed artifact remained byte-identical at sha256
`606c3f2558216af58eb2f728f107b52bb84f769dac079afbc22693866d413ec9`.
Its two-table gate reproduces both ruled roles digit-exact:

- canonical phase-E: burst3 static 745.758 / 747.169 ms;
- tier-5 replication sensitivity: 746.994 / 748.409 ms.

The top-level fields now come from `phaseE_canonical` and reproduce the
manuscript values: steady forecast/reactive 738.751 / 742.587 ms and static
434.516 / 435.497 ms
(`simulation/results/silicon_anchor/steady24h_vllm_retimes.json:1-571`).
The burst and calm-day values and table roles are propagated at
`tex/metodologia.tex:369-395`; the live metric-stack bind and all semantic
self-test probes pass.

The table-choice defect raised by D109 is fixed. I have separately filed D111
because the appendix still pins the pre-fix tier-3 commit; that provenance-pin
residual does not alter the D109 table ruling or any numerical verdict.
