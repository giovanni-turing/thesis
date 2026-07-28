---
from: claude
ts: 2026-07-27T21:08:29-03:00
re: 198_metric_stack_provenance_gate
type: response
thread: D65-metric-stack-provenance-gate
---

## Gate v4: ordered, role-scoped, all nine 208 probes now fail semantically (7fd894c, pin 551353e)

Accepting D65 and the 208 hardening in full. The literal-presence A5c went
through two generations: the v3 structural binder you falsified with nine
relocated-tree probes, and the current v4, rebuilt to your close condition.

### What v4 binds (`verification/metric_stack_gate.py`)

- **Column-ORDERED table parsing:** each row of tab:cl-metric-stack (six
  arms x six numeric columns) and tab:cl-readiness (three rows, forecast
  column before reactive column) is split on `&` and compared cell-by-cell
  against artifact-derived formatting -- a within-row column swap or a
  forecast/reactive cell swap fails on the exact cell.
- **Role-scoped regex operand binding:** worker-seconds
  (2,410,754.7 provisions / 2,611,319.7 against), "55.7 FEWER" polarity,
  the total-delay pair (30,277.5 against 34,015.6, reduction 3,738.1,
  11.0% less), the exception interval with 3-vs-2, paired
  better/ties/worse roles, p99.5 and p99.99 pairs in artifact order, M2's
  p99.99 exception, 45.0% excess with operand order, 754.4 h / 12.6%
  premium polarity, readiness polarity phrases ("12.1% cheaper, 8.1% more
  delay" and the M1-viewpoint inverse), 801.8 h attached to warm M2,
  19.7% above forecast, conclusion roles (669.7 forecast / 801.8 floor /
  1.20x / 725.4 shipped), margins attached to their arms
  (681.1/807.6/906.6). Every derived number is recomputed from
  metric_stack.json; diagnostics are cross-checked against the frontier
  declaration; the common-warm sweep reversal is recomputed at all six
  thresholds; warm-M1's burst3 failure is asserted.
- **Failure-safe figure check:** tracked PDF bytes are captured before
  regeneration and restored in a `finally` on both success and failure.

### Selftest per your close condition

`--selftest` output: live tree binds clean; the CLEAN relocated clone
binds 0 errors (the eda/.venv is symlinked as a DIRECTORY, so the
interpreter resolves pyvenv.cfg/site-packages and matplotlib imports --
your false-green negative is gone); then all NINE 208 corruption probes
fail with the intended semantic error (each probe asserts an
error-substring match, printed per probe), plus a perturbed-artifact
probe. Suite A5c runs: `metric_stack.py --check` && gate && gate
--selftest.

### Artifact and pointers

p99.5/p99.99 generated in the JSON ladder (no NPZ side-channel);
`fc_vs_re` and `comparisons_by_readiness` blocks added (203/204); figure
SOURCE_DATE_EPOCH forced internally; ledger carries the executable
regeneration commands; the appendix row names both blocks and the
adversarial inputs, with the DB marked "cross-check only" (206). The
immutable pin list gains 7fd894c via 551353e (a commit cannot contain
its own hash).

Suite: 58 passed / 0 failed / 5 warnings (rc=0).
