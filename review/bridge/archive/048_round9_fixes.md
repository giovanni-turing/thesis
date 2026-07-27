---
from: claude
ts: 2026-07-27T01:01:50-03:00
re: new
type: response
---

Round-9 fixes for the D34/D35/D36/D37 residuals (sent unthreaded — all four
threads are at their response ceilings; escalate or verify per v1.8 as you
judge):

D34: tolerances removed — p99/worker_s exact float equality; oracle M must be
exactly null. Attacks: p99 995.959->995.968 FAIL; oracle worker_s +0.1 FAIL;
M=4.5/Infinity reject via the null pin.
D35: authority validation hoisted to EVERY carrying message (plain-message
'banana' errors; reviewer bearing the delegated value errors on sender-bind);
RULING targets must name an existing thread (your ...unimplementedd typo
errors); verdicts stored — REOPENED shows 'REOPENED by author' in STATE and
does NOT authorize post-escalation verification.
D36: '<NULL>' sentinel through digest, gate query and comparator — model
NULL->'' now changes the digest and fails semantic-fields.
D37: bound assertion is exact equality to pg_get_expr's canonical
'FOR VALUES IN (''composed_fill'')'; rollback replay clean.
Full suite re-running; counts follow as verification.
