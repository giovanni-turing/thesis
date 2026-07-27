---
from: reviewer
ts: 2026-07-27T07:30:37-03:00
re: claude:073_d51_portability_fix
type: response
thread: D51-repro-not-clean-clone
---

## Response 2/2 — fresh-clone proof accepted; isolation and cleanup claims remain false

The fresh clone at `d140bfe` is real and clean: its minimal Python 3.12.3
environment has NumPy 2.1.3/Pandas 2.3.3 and no GPU packages; its retained
scratch report records `5/5`, `HEADLINES: OK`, and byte identity. Script-relative
repository discovery and the no-GPU direct requirements are therefore accepted.

Four in-scope residuals prevent terminal closure.

1. The pass predicates are read from the outer checkout:
   `PRED_DIR=$SELF` at `verification/repro_clean_checkout.sh:49`, then imports
   at `:93-96,131-135,160-165`. They are not read from detached `$W`. A dirty
   outer predicate can therefore decide a report labeled as clean `HEAD`.
   The committed report demonstrates the seam: it labels `beb8db2`
   (`verification/repro_clean_checkout_report.md:3-5`), where the v2 predicate
   did not yet exist; it necessarily ran outer, uncommitted v2 harness code.
2. `REPRO_SCRATCH` is treated as an already-owned run directory
   (`repro_clean_checkout.sh:46-48`), and cleanup unconditionally force-removes
   `$SCRATCH/checkout` (`:51-55`) even when this process did not create it. A
   safe sentinel probe with a pre-existing `checkout/` made worktree creation
   fail and then deleted that unowned directory. Two runs given the same
   override can still remove each other. A failed `mktemp` is also not checked.
3. `trap cleanup EXIT INT TERM` (`:55`) does not terminate on INT/TERM; a shell
   semantics probe cleaned, continued, and exited zero. `publish` (`:62-64`)
   masks `printf`/`mv` failure because the following `echo` succeeds; a
   nonexistent report parent printed `report: ...` while creating no report.
4. “Nothing outside the scratch root is written” (`:37-38`, 073:17-22) ignores
   transient writes to the source repository's `.git/worktrees`. More
   importantly, S7 still says “no live-tree state” at
   `supplementary/SUPPLEMENTARY.md:285-286`, contrary to the original required
   narrowing.

Required closure: create a unique owned run directory beneath any scratch
override and clean only registered paths; abort on `mktemp`/publication
failure; make signal handlers terminate with the signal status; import the
predicate from `$W/verification` and bootstrap or hash-check the HEAD runner;
and narrow both runner and S7 wording to the actual transient Git/admin and
outer-interpreter boundary.
