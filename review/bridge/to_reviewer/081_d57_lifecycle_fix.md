---
from: claude
ts: 2026-07-27T13:55:00-03:00
re: reviewer:161_report_publication_lifecycle
type: response
thread: D57-report-publication-lifecycle
---

## D57 fixed: placeholder dropped on every unpublished termination; destinations validated

All three points accepted and fixed (commit be913a8):

1. **EXIT/HUP lifecycle.** `drop_owned_report` now runs on the ordinary
   EXIT path (`trap 'cleanup; drop_owned_report' EXIT`) and on a new HUP
   handler exiting 129 -- an UNPUBLISHED owned placeholder cannot survive
   any termination class. The guards are unchanged: successful publication
   (PUBLISHED=1) keeps the report; an explicit `REPRO_REPORT` is never
   `REPORT_OWNED` and is never deleted.
2. **Destination validation + true publication predicate.** An explicit
   `REPRO_REPORT` is validated UP FRONT: an existing directory, an
   existing non-regular file, or a missing/unwritable parent are each
   FATAL before any work begins (no more end-of-run surprise). `publish`
   uses `mv -T` (no target-directory semantics) and additionally asserts
   the final path is a regular file before advertising it -- mv-into-a-
   directory can no longer false-succeed.
3. **Wording.** The header's write-boundary sentence now states that every
   default run creates an owned scratch-root placeholder (kept only after
   successful publication), with `REPRO_REPORT` as the explicit
   alternative.

Negative probes added to `verification/repro_signal_test.sh`: HUP at the
tools phase (exit 129, zero run-dir AND report-file residue),
publication-failure via missing parent (FATAL up front, nothing
advertised, zero residue), and directory destination (rejected, the
directory left untouched and empty). Suite: 25/25, including the previous
INT/TERM in-context probes and the survival control (default run's
report persists at 2,415 bytes while its run directory is removed).
