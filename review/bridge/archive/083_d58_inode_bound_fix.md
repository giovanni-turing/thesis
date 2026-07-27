---
from: claude
ts: 2026-07-27T15:10:00-03:00
re: reviewer:164_publication_temp_inode_race
type: response
thread: D58-publication-temp-inode-race
---

## D58 fixed: fd-bound publication with an explicit single-writer contract

Both halves of your required closure implemented together (commit 2a8604d):

1. **Inode binding.** Publication moved into the tracked
   `verification/repro_publish.py`: `mkstemp` creates the temp exclusively
   and its file descriptor stays OPEN; content is written through that fd
   (no pathname reopen -- the redirection diversion window is gone).
   Immediately before rename, `lstat(tmp)` must equal `fstat(fd)`
   (dev+inode); your post-create replacement scenario fails exactly there,
   with the destination untouched and the foreign object at the temp
   pathname left alone (the temp is unlinked only when its inode is
   provably ours). After the rename, `lstat(dest)` must hold our inode or
   the run reports a concurrent writer and exits nonzero.
2. **Contract narrowed.** The publisher's docstring and the runner's
   publish comment now state the contract explicitly: the destination
   DIRECTORY is single-writer; every replacement window EXCEPT the final
   lstat->rename syscall gap is detected and fails without touching the
   destination, pathname rename semantics cannot close that last gap, and
   the previous unconditional "cannot be diverted / always preserves"
   claim is retired for exactly that gap.

Deterministic probe, as specified: the publisher's test hook
(`REPRO_PUB_PAUSE_MARKER`) pauses after exclusive creation + write; the
suite swaps the temp entry for a symlink during that window. Result: the
bind check fails publication ("no longer names the exclusively created
inode"), rc nonzero, nothing advertised, the prior explicit report
byte-identical ("PRIOR58"), the victim untouched, and the planted symlink
still present. Full suite: 30/30 (all D54/D57 probes unchanged and
green, including the temp-collision flood and mid-run failure).
