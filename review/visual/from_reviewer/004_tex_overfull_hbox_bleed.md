---
from: reviewer
ts: 2026-07-28T05:13:00-03:00
re: new
type: finding
thread: V04-tex-overfull-hbox-bleed
---

## MAJOR: Overfull `\hbox` text and float overflow bleeding into margins in `tex/closedloop.tex`

Rendered evidence:
- Build log inspection (`tex/tese.log`):
  - `tex/closedloop.tex` lines 224--226: `Overfull \hbox (42.60999pt too wide)` (bleeds **42.61 pt / ~0.59 inches** into outer margin).
  - `tex/closedloop.tex` lines 256--257: `Overfull \hbox (23.2104pt too wide)` (bleeds **23.21 pt / ~0.32 inches** into outer margin).
  - `tex/closedloop.tex` lines 337--338: `Overfull \hbox (13.66928pt too wide)`.
  - Line 1080: `Overfull \hbox (37.74957pt too wide) has occurred while \output is active` (float/table container overflow).

Defect analysis:
Unbroken inline text blocks containing long numerical ranges (e.g. `1{,}616\,\si{\milli\second}`, `400/40 to 200/20\,\si{\milli\second}`, `18.6\,\to\,20.4`) and unhyphenated compound terms in `tex/closedloop.tex` prevent LaTeX's line-breaking algorithm from inserting breaks or hyphenation. This forces line boxes to overflow the right text margin by up to 42.6 pt, visibly protruding outside the 812 px text column into the outer page margin on rendered PDF pages.

Proposed fix:
Insert soft hyphens (`\-`), break long inline SI math expressions with `\allowbreak` or rephrase paragraph text around lines 220--260 in `tex/closedloop.tex` to eliminate margin bleeding.
