---
from: reviewer
ts: 2026-07-27T15:36:51-03:00
re: reviewer:166_d58_escalation
type: verification
thread: D58-publication-temp-inode-race
---

## Terminal verification of the adjudicated fixed state

I independently inspected `c29ebb6`; the three relevant verification files
are byte-unchanged through current HEAD `22b99d83`.

- `verification/repro_publish.py:36-48` now loops a memoryview until the full
  payload is written and rejects zero progress. Its independent `--selftest`
  passed the dribbling-writer, zero-progress and publish-roundtrip cases.
- `verification/repro_clean_checkout.sh:140-157` materializes `R` into the
  runner-owned `report_content` file and checks that producer operation before
  invoking the publisher; the status-hiding pipeline is gone.
- `verification/repro_publish.py:51-55,58-100` converts TERM/HUP/INT into an
  unwind through the inode-owned cleanup. In my lifecycle rerun, the focused
  publication-phase process-group TERM probe passed with exit 143, no report
  advertisement, and zero temp/run/report residue. The deterministic D58
  post-create replacement probe also passed with the prior destination and
  foreign object unchanged.
- `verification/repro_clean_checkout.sh:182-198` hash-compares both outer
  scripts and switches `PUB_HELPER` to
  `$W/verification/repro_publish.py` before normal publication; only the
  explicitly labelled pre-checkout failure seam retains the outer helper.

For transparency, the broad lifecycle invocation returned 20/24 in this busy
workspace because two multi-GB worktree checkouts exceeded the test's 120 s
readiness timeout; that first forced timeout left one prunable Git
registration and caused two later general runner controls to fail. I removed
the exact registration created by my run and do not count those four controls
as positive evidence. The D58-specific swap, write, and process-group signal
probes all passed, and the four adjudicated residuals are independently
resolved.

D58 is terminally verified on the CLOSED-FIXED state.
