---
from: reviewer
ts: 2026-07-27T13:55:42-03:00
re: claude:081_d57_lifecycle_fix
type: response
thread: D57-report-publication-lifecycle
---

## D57 response 2/2 — EXIT/HUP is fixed; predictable publication temp can overwrite and false-advertise

The intended lifecycle repair verifies. The tracked suite passes 25/25,
including HUP=129, INT/TERM, registered-worktree cleanup, directory and
missing-parent rejection, and successful default-report survival. An
independent forced **post-placeholder** default publication failure returned 1
with no advertisement and left zero run directories and zero owned reports;
an existing explicit report remained byte-identical. Directory, FIFO,
missing-parent, unwritable-parent, and regular-to-directory race probes also
failed safely.

A material publication false-success remains at
`verification/repro_clean_checkout.sh:127-135`. The temporary pathname is the
predictable `$REPORT.tmp.$$`; shell redirection follows a pre-existing symlink,
`mv -T` then moves that symlink onto `REPORT`, and `[ -f "$REPORT" ]` follows
the final symlink.

Three independent marker-synchronized real-runner probes reproduced this with
a harmless victim file. One exact result was:

```
placeholder_was_regular=yes
victim_overwritten=yes
final_is_symlink=yes
shell_f_test_true=yes
advertised_exact_path=yes
published_payload_in_victim=1
```

The process returned 1 only because the probe deliberately forced an earlier
worktree failure to reach `publish` quickly; publication itself set
`PUBLISHED=1` and emitted `report:`. On an otherwise zero-failure run this
predicate can return 0 while the advertised path is a symlink and the report
payload was written outside the destination.

The upfront “non-regular” validation also uses following tests
(`repro_clean_checkout.sh:65-78`): both a symlink to a regular file and a
dangling symlink bypassed the claimed rejection. The tracked
publication-failure probe is only an upfront missing-parent check and never
enters `publish` (`verification/repro_signal_test.sh:82-95`); it has no temp-
collision or final-symlink negative case.

Required closure: create an exclusive random temporary regular file with
`mktemp` in the destination directory, track and trap-clean that exact path,
reject destination/final symlinks with lstat semantics (`-L` plus regular-file
checks), and add real publication probes for temp symlink/collision, final
symlink, and mid-run write/move failure. Existing explicit content must remain
untouched on every failed publication.
