---
from: claude
ts: 2026-07-27T14:40:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D57-report-publication-lifecycle=CLOSED-FIXED
---

## Adjudication under delegated authority

Delegation basis: author directive "fable 5 xhigh pass" (2026-07-27
session), registry entry author-delegated:fable-5-2026-07-27-xhigh.

The round-2 residual (message 162) was accepted as real and implemented
in commit 1d9db97; the ruling is CLOSED-FIXED on that fixed state.

Fix, matching the required closure exactly: publication now creates an
EXCLUSIVE random temporary regular file via mktemp (O_EXCL) in the
destination directory -- a planted symlink cannot occupy its name, so
redirection cannot be diverted and `mv -T` moves OUR regular file; the
exact temp path is tracked in `PUB_TMP` and trap-cleaned on every
termination class. Symlink destinations are rejected with lstat
semantics: `-L` up front for explicit destinations (a symlink to a
regular file and a dangling symlink both now fail before any work) and
re-checked immediately before and after the rename, with the final
success predicate requiring `! -L && -f` on the destination. A failed
publication removes only the owned temp and leaves any existing explicit
content untouched.

Negative probes added (suite 29/29): symlink destination (victim
untouched), dangling-symlink destination, a temp-name symlink flood that
the exclusive temp dodges (report published as a regular file, victim
byte-identical), and a marker-synchronized MID-RUN publication failure
(parent made unwritable after upfront validation: fatal, nothing
advertised, prior explicit content byte-identical, zero temp residue).
All previous probes (INT/TERM/HUP in-context, publication-failure,
dir-destination, survival control) remain green.

Terminal verification remains with the finding's author per protocol.
