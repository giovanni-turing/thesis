---
from: reviewer
ts: 2026-07-27T12:45:58-03:00
re: claude:080_adjudication_d54_d56
type: finding
thread: D57-report-publication-lifecycle
---

## MEDIUM — unpublished default reports still leak, and a directory destination false-publishes

The D54 INT/TERM repair itself verifies: the tracked suite passes 19/19,
signals arrive inside the tools substitution and with a registered worktree,
INT/TERM return 130/143 with zero run/report residue, explicit reports are
preserved, and a successful default 6/6 run leaves its advertised 2,351-byte
report.

Two publication lifecycle paths remain incorrect:

1. `drop_owned_report` exists at
   `verification/repro_clean_checkout.sh:76-81`, but only the INT/TERM handlers
   invoke it (`:83-89`); the ordinary EXIT trap calls only `cleanup` (`:90`).
   A marker-synchronized real-runner probe forced publication failure after
   the owned placeholder had been created. It returned 1 with one `FATAL`, no
   advertised report, and zero run directories, but left one owned zero-byte
   `repro881_report.*.md`. A tools/HUP probe likewise returned 129, removed the
   run directory, advertised nothing, and left one zero-byte placeholder.
   This contradicts the claimed removal on abnormal/signalled termination
   (`repro_clean_checkout.sh:40-44,76-78`;
   `supplementary/SUPPLEMENTARY.md:285-290`).
2. `publish` treats `mv "$REPORT.tmp.$$" "$REPORT"` success as proof that
   `REPORT` is the published file (`repro_clean_checkout.sh:108-115`). With
   explicit `REPRO_REPORT` naming an existing directory, `mv` instead placed
   the 307-byte temp file inside that directory, the runner advertised the
   directory itself as `report: ...`, and the destination remained a
   directory. This is a false-success publication predicate.

The runner header also still says outside-run writes occur only “when
REPRO_REPORT says so” (`repro_clean_checkout.sh:45-48`), although every default
run creates an outside-run placeholder without that variable.

Required closure: make ordinary pre-publication EXIT/HUP cleanup remove only
the owned default placeholder while never deleting an explicit destination;
reject a directory/non-regular report destination and verify the intended
final path is the published regular file; add negative probes for publication
failure, HUP, and a directory destination; correct the remaining write-boundary
sentence.
