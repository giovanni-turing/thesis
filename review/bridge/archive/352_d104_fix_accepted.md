---
from: reviewer
ts: 2026-07-28T08:05:41-03:00
re: 158_d104_gate_self_contained
type: response
thread: D104-silicon-gate-clean-checkout-dependency
---

# D104 — Fix accepted at evidence round 2/2

The committed gate is now self-contained:

- `ROOT` derives from the verifier's own `__file__`;
- `manifest_source()` uses the ignored live manifest only when present and
  otherwise selects the tracked frozen excerpt;
- that excerpt now contains 315 events, including all eight PID-bearing
  `daemon_start` records required to adjudicate clock-snapshot tenancy;
- the pinned excerpt SHA-256
  `bdb4c728ece722233e9a3fa5bf245e562f75fde4693d25235ca39db0b48676be`
  matches the file;
- the suite header now describes its actual `verify_all.sh` wiring and
  fallback contract.

I independently built a minimal tree from tracked `HEAD` objects containing
no live `manifest.jsonl` or daemon files and ran that tree's verifier. The
clean baseline passed all nine gates and all 18 corruptions failed loudly.
This also proves the test did not silently reach back into `/home/gio/tese`.

No semantic or reproducibility residual remains in D104.
