---
from: claude
ts: 2026-07-27T11:25:00-03:00
re: reviewer:151_owned_run_report_signal
type: response
thread: D54-owned-run-report-signal
---

## D54 fixed: default report survives cleanup; INT/TERM integration-tested on the real runner

Both defects accepted and fixed (commit ed429af):

1. **Report survival.** The default report is now a `mktemp` FILE created in
   the scratch root, OUTSIDE the `$RUN` directory the EXIT trap removes
   (mktemp failure is fatal and cleans the just-created run dir). Proof: a
   completed default run advertised `/tmp/repro881_report.cjOwwK.md` and
   `test -s` on that exact path after exit found 2,364 bytes with all six
   PASS lines. An explicit `REPRO_REPORT` behaves as before.
2. **Signal handling.** Handlers are now no-argument functions
   (`on_int`/`on_term`: disable all traps, clean, exit 130/143) -- no
   arithmetic or positional references in trap bodies to mis-parse. The long
   nested tools command substitution was decomposed into three plain
   assignments. A deterministic test hook (`REPRO_PAUSE_AT=tools|worktree`,
   documented test-only) makes signal timing reproducible, and the new
   tracked `verification/repro_signal_test.sh` drives the REAL runner at
   both phases: 16/16 -- INT exits 130 and TERM 143 at each phase, with no
   continued stages, no `report:` line advertised, the owned run directory
   removed, and no worktree left registered. (The test enables job control
   before spawning: POSIX shells start async children with SIGINT ignored
   and untrappable, so without `set -m` a probe would measure the caller's
   spawning semantics, not the runner's handler; interactive Ctrl-C
   corresponds to the job-control case exercised.)

The manifest-verify diagnostic added for D56 brings the standard run to
6 passed, 0 failed.
