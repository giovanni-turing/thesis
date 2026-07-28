---
from: reviewer
ts: 2026-07-28T07:58:45-03:00
re: new
type: finding
thread: D104-silicon-gate-clean-checkout-dependency
---

# D104 — The wired silicon gate depends on an ignored live manifest

The 18 corruption probes pass in the current campaign workspace, but the
committed delivery gate is not reproducible from commit `2daa383`.

- The settled commit deliberately untracks and ignores
  `simulation/results/silicon_anchor/manifest.jsonl`
  (`.gitignore:136-142`).
- `verification/silicon_negative_gates.py` nevertheless always calls
  `runner_pids(CAMPAIGN / "manifest.jsonl", ...)`
  (`verification/silicon_negative_gates.py:151-175`,
  `verification/silicon_negative_gates.py:213`).
- `provenance/verify_all.sh:147-154` invokes that script as a delivery gate.
  Its success here therefore depends on the ignored live manifest still being
  present in this working directory; a clean checkout has no such file and
  fails before the probes run.
- The tracked `burst3_manifest_excerpt.jsonl` is not presently a drop-in
  substitute: it contains 307 cell events but no `daemon_start` event, while
  its `rep_start`/`rep_resume` events carry no PID. The gate needs the daemon
  timeline to adjudicate the recorded compute-app PID per clock snapshot.

There is also a direct documentation contradiction: the suite header still
says “NOT WIRED INTO verify_all.sh YET”
(`verification/silicon_negative_gates.py:69-70`) although this commit wires
it.

Please make the settled gate self-contained: commit the minimal frozen daemon
PID/timestamp evidence needed by the 15 burst3 reps (or include the relevant
`daemon_start` events in the frozen excerpt), make the suite consume that
tracked evidence, and test it from a clean checkout. Then update the stale
header. Until then, 18/18 demonstrates the verifier logic in this workspace
but not a reproducible committed delivery gate.
