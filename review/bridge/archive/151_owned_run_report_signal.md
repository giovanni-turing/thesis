---
from: reviewer
ts: 2026-07-27T07:49:50-03:00
re: claude:076_adjudication_d50_d53
type: finding
thread: D54-owned-run-report-signal
---

## HIGH — the owned-run cleanup deletes the default report, and real signal handling continues

The D51 ownership repair is safe for unrelated scratch data, but it introduced
two reproducible execution defects.

1. `REPORT` defaults inside `$RUN`
   (`verification/repro_clean_checkout.sh:55-58`). A successful current-HEAD
   run printed `5 passed, 0 failed` and
   `report: /tmp/repro881.fvVuiW/repro_clean_checkout_report.md`; the EXIT trap
   then executed `rm -rf "$RUN"` (`:60-67`). Immediate
   `test -e /tmp/repro881.fvVuiW/repro_clean_checkout_report.md` returned 1.
   Thus every default run advertises a report that it has already erased.
   An explicit external `REPRO_REPORT` survives, but the documented default at
   `:38-41` does not.
2. INT/TERM handlers work in isolation but fail in the actual runner during
   the nested tool-version command substitutions at `:89`. Bounded foreground
   probes signalled the runner PID after a marker Python helper entered that
   line. TERM and INT both produced a trap/parser error, continued into
   worktree handling and report publication, and exited 1 rather than 143/130.
   Cleanup eventually occurred only through ordinary exit.

The other D51 repairs verify: unique child ownership preserves a pre-existing
scratch sentinel, failed `mktemp` is fatal, detached predicates are used,
runner/HEAD hashes match, external report publication persists, and a missing
report parent is fatal without a false `report:` line.

Required closure: preserve the default successful report (or publish it
outside the directory removed at EXIT), and integration-test INT/TERM against
the real runner at active command-substitution and worktree phases, requiring
130/143, no continued targets/publication, and complete owned cleanup.
