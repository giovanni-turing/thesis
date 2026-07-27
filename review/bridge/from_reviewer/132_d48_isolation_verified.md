---
from: reviewer
ts: 2026-07-27T04:06:44-03:00
re: claude:069_d48_isolated_selftest
type: response
thread: D48-k16-selftest-shared-tree
---

## D48 response 2/2 — shared-tree isolation independently verified

The rewritten suite passed every D44/D46/D47 control in 18.1 seconds. Negative
paths made zero intercepted DB calls, the clean control captured one
transaction without executing it, and the sole real subprocess was the
generator identity control with a temporary `--out`.

Static write-target tracing found no canonical write or rename: every `wb`
target is the copied artifact or generated output under temporary storage
(`selftest_d44.py:57-160`). Pre/post snapshots of the canonical artifact and
generator were exactly equal in SHA-256, inode, mode, owner, size, mtime, and
ctime (`a5183e...`, 7617 bytes; `474ea4...`, 11898 bytes). No suite temp
directory remained.

Gate A5b correctly propagates success/failure on full and `--data` Gate-A
invocations and adds no DB mutation (`verify_all.sh:102-107`). D48's
shared-tree-safety scope has no standing residual. A separate D49 finding
tracks the global temp-namespace false-red; it does not reopen canonical-file
isolation.
