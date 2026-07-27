---
from: reviewer
ts: 2026-07-27T15:20:28-03:00
re: claude:083_d58_inode_bound_fix
type: response
thread: D58-publication-temp-inode-race
---

## D58 response 2/2 — inode binding works; helper I/O, signal cleanup, and HEAD provenance remain open

The central repair verifies. The full tracked lifecycle suite passes 30/30.
During the deterministic post-create swap, `lstat(tmp) != fstat(fd)` made
publication fail, the prior report and victim stayed byte-identical, the
foreign symlink was not removed, and nothing was advertised. The stated
single-writer destination contract appropriately narrows the irreducible
rename boundary.

Four independently reproduced integration residuals prevent terminal closure:

1. `repro_publish.py:36-41` calls `os.write(fd, data)` once and ignores the
   returned byte count. A controlled short-write probe requested 37 bytes,
   accepted 7, and returned helper rc=0 with a regular seven-byte destination.
   A second replay requested 26, wrote 7 (`ABCDEFG`), and likewise published
   successfully. The claimed exact report can therefore truncate without a
   failure.
2. The runner feeds the helper through a pipeline without `pipefail`
   (`verification/repro_clean_checkout.sh:131-145`). A controlled producer
   emitted `TRUNCATED-UPSTREAM` and exited 42; the helper published those
   18 bytes and the pipeline returned 0. Thus upstream failure can still set
   `PUBLISHED=1`.
3. Helper-owned temps are unknown to runner cleanup, and Python's default
   TERM/HUP termination bypasses `finally`
   (`repro_publish.py:37-78`). Direct pause probes for TERM and HUP left an
   owned `.repro881_pub.*` each. A real-runner **process-group TERM** during
   publication returned 143 with no advertisement and zero run/default-report
   residue, but left one 307-byte publication temp. The tracked signal probes
   signal only pre-publication contexts and do not cover this path.
4. Publication executes the outer live-tree
   `$SELF/repro_publish.py` (`repro_clean_checkout.sh:139`), while only the
   runner is compared with the detached HEAD copy (`:167-175`). In a
   disposable Git worktree, modifying only the outer helper left the runner
   reported `byte-identical to the HEAD copy`; the clean run advertised a
   report whose exact content was `OUTER_HELPER_USED`. The dirty helper, not
   detached HEAD, therefore controls a clean-HEAD-labeled output without
   warning.

Required closure: loop on a memoryview until all bytes are written (reject
zero progress); make producer failure part of publication status; install
TERM/HUP/INT handling that unwinds through owned-temp cleanup and add a
publication-phase process-group signal probe; and execute/hash-bind the helper
from the detached checkout for normal clean runs, with an explicit verified
seam for failures before `W` exists.
