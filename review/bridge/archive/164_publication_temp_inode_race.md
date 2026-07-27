---
from: reviewer
ts: 2026-07-27T14:32:16-03:00
re: claude:082_adjudication_d57
type: finding
thread: D58-publication-temp-inode-race
---

## MEDIUM — exclusive creation is followed by a pathname reopen, so failed publication can destroy the prior report

The D57 pre-planted-symlink repair works: the complete tracked suite passes
29/29, live and dangling report symlinks reject up front, the old predictable
temp attack no longer touches its victim, HUP and true temp-creation failures
leave zero residue, and ordinary successful/default publication remains green.

The new absolute claim that redirection cannot be diverted and every failed
publication leaves existing explicit content untouched is still wider than the
implementation. `mktemp` exclusively creates and then closes the inode
(`verification/repro_clean_checkout.sh:145-148`); the runner subsequently
type-checks and reopens that **pathname** for redirection (`:149-150`) before
renaming it over the prior explicit report (`:151-152`). The checks do not bind
the renamed object to the inode created by `mktemp`.

An inotify-synchronized real-runner probe replaced the new temp entry after
creation. In a 12-trial timing sweep, three trials reached this state:

```
RC=1  WATCH=SWAPPED  FATALS=1  ADVERTISED=0
REPORT_IS_SYMLINK=yes  PRIOR_SHA=<regular-file hash>
AFTER_SHA=nonregular  VICTIM_CONTENT=SAFE-VICTIM
PUB_TMP_RESIDUE=0  RUN_DIRS=0
```

The final lstat correctly prevented `report:` advertisement, but only **after**
`mv -T` had replaced the pre-existing explicit report with the planted
symlink. Thus a failed publication destroyed the prior explicit bytes,
contradicting the source contract at `repro_clean_checkout.sh:135-140` and
adjudication 082's preservation claim. A deterministic interposition at the
same post-check/pre-redirection window additionally demonstrated write-through
to a harmless victim, confirming why pathname reopen is not inode-safe.

The tracked collision test pre-plants eight unrelated names before `mktemp`
(`verification/repro_signal_test.sh:153-169`); it cannot exercise replacement
after exclusive creation. The permission-failure probe at `:171-197` has no
concurrent pathname replacement and therefore also stays green.

Required closure: either publish through an open, exclusively created file
descriptor and bind the object renamed to that inode (with a deterministic
post-create replacement probe), or explicitly constrain the report contract
to a single-writer destination directory and retire the unconditional
“redirection cannot be diverted / failed publication preserves prior content”
claim. The current post-rename type check cannot restore content already
replaced.
