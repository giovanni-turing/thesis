---
from: reviewer
ts: 2026-07-28T17:56:00-03:00
re: 195_doi_archived_notice
type: finding
thread: D121-doi-pagination
---

# D121 — DOI paragraph creates a cross-page, cross-float sentence break

The 111-to-113-page shift does merit a small numbered layout round.  A fresh
build of current HEAD is mechanically clean (113 A4 pages; no fatal,
undefined-reference, overfull-box, or PDF-string diagnostics), but the new
archive paragraph at `tex/apendice.tex:343-355` pushes the opening paragraph
of Section A.5 (`tex/apendice.tex:401-414`) into a poor reading order:

- physical PDF page 103 / printed page 83 ends mid-sentence after
  “a separate recollection from the Phase-E”;
- physical page 104 first inserts all of floating Table A.3 from the preceding
  Supplementary Archive section;
- only below that unrelated float does the sentence resume with
  “self-lock attempt ...”.

This is a concrete readability regression, not an objection to 113 pages
itself.  In the pre-DOI 111-page build, the same opening paragraph completed
before the page break.

A temporary, non-workspace proof adding a page break immediately before
Section A.5 (`tex/apendice.tex:401`) kept the document at 113 pages and put
Table A.3 first on printed page 84, followed by the A.5 heading and its whole
opening paragraph.  The build remained diagnostic-clean.  Please use that or
an equivalent float/section barrier, then provide the rebuilt page count and
the affected-page render.  No prose or data change is required.
