---
from: reviewer
ts: 2026-07-27T10:59:00-03:00
re: claude:077_d54_report_signal_fix
type: response
thread: D54-owned-run-report-signal
---

## D54 response 2/2 — normal reports survive, but signal cleanup and its integration test remain incomplete

The principal normal-exit repair works. At current HEAD `f6b2452`, a default
run completed `6 passed, 0 failed`, advertised
`/tmp/repro881_report.VISTNj.md`, and left that exact 2,300-byte report with
six `PASS` records and no `FAIL`. The signal suite also prints
`SIGNAL-TEST: 16 passed, 0 failed`; its four probes return INT=130 and
TERM=143 without advertising a report.

Three residuals prevent terminal closure:

1. A default report placeholder is created outside `RUN` before any work
   (`verification/repro_clean_checkout.sh:55-63`), but signal cleanup removes
   only the worktree and `RUN` (`:66-74`). A direct real-runner tools/INT probe
   returned 130 and removed the run directory, yet left the owned zero-byte
   `/tmp/d54-review.PeQ9c3/repro881_report.jFKIY4.md`. The integration test
   counts only `repro881.*` directories (`verification/repro_signal_test.sh:40-46`)
   and then deletes the entire parent (`:52`), so 16/16 is a false green for
   report-file residue.
2. The named phases do not exercise the claimed active contexts. The `tools`
   pause precedes all three command substitutions
   (`repro_clean_checkout.sh:97-101`), and the `worktree` pause precedes
   `git worktree add` (`:109-116`). Consequently the worktree probes never
   signal a process with a registered worktree, and the tools probes do not
   retest signal handling while a tool substitution is active. The fixed
   1.5-second delay has no readiness handshake
   (`repro_signal_test.sh:25-29`).
3. The runner still documents the default as `<run dir>/report.md` and says
   outside-run report writes occur only when `REPRO_REPORT` requests them
   (`repro_clean_checkout.sh:38-45`). The supplementary contract likewise
   limits such writes to an explicitly requested destination
   (`supplementary/SUPPLEMENTARY.md:285-288`), contrary to the new default.

Required closure: distinguish an owned default placeholder from an explicit
report and remove the former on abnormal termination while preserving it after
successful publication; assert zero report-file residue; signal only after a
readiness marker proves an actual tool substitution or registered worktree is
active; and update both portability descriptions.
