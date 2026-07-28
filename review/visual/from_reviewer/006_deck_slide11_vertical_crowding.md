---
from: reviewer
ts: 2026-07-28T05:15:00-03:00
re: new
type: finding
thread: V06-deck-slide11-vertical-crowding
---

## MINOR: Vertical content crowding and tight bottom clearance on Slide 11

Rendered evidence:
- 1920x1080 screenshot analysis (`~/tmp_deck_snaps/slide_11.png`):
  - Slide 11 (`Same resource-time conclusion in the span-level synthesis`) stacks four vertical blocks:
    1. Heading + kicker + lead paragraph (height ~180 px)
    2. 5x5 matrix table `.mmat` (height ~340 px)
    3. 3-column `.numrow` containing three dense `.numtile` cards (height ~220 px)
    4. Bottom reveal.js slide controls / progress bar at `y=1020..1080`
  - Pixel measurement shows the last line of text in `.numrow` extends down to **y=997**, leaving only **23 px** vertical clearance above the slide control overlay (`y=1020`).

Defect analysis:
Slide 11 combines an extended multi-line lead paragraph, a full 5-row table matrix, and three text-heavy number tiles on a single slide canvas. The vertical stack fills 98% of the viewport height, visually crowding the bottom tiles against the presenter controls and creating an unbalanced, overly dense slide layout compared to adjacent slides.

Proposed fix:
Trim the lead paragraph in Slide 11 from 5 lines to 2--3 lines or reduce `.mmat` vertical padding (`margin-bottom` / `padding`) to regain ~50--60 px of bottom margin breathing room above `y=1020`.
