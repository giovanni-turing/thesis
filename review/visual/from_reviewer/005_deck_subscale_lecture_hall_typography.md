---
from: reviewer
ts: 2026-07-28T05:14:00-03:00
re: new
type: finding
thread: V05-deck-subscale-lecture-hall-typography
---

## MAJOR: Sub-scale typography and low-contrast light grays across presentation deck

Rendered evidence:
- 1920x1080 Chromium screenshot analysis of `defense/deck_single.html`:
  - CSS rule inspection in `defense/reveal/index.html`:
    - `.numtile .k`: `font-size: 0.4em` (~14--16 px on slide canvas)
    - `.reqcap`, `.reqimgs span`, `.parr .lbl`, `.ep`, `.lwin span`: `font-size: 12px`
    - `.pcard .psub`, `.pcard .pmeta`, `.knob`, `.polname span`: `font-size: 12.5px`
    - `.lhead`, `.polbar .bar`: `font-size: 13px`
    - `.disclose`: `font-size: 0.5em` (~12 px)
    - `.reps u`: `border: 2px dashed #b9b9b9`
    - `.parr .ln`: `background: #c2c2c2`

Defect analysis:
On a 1920x1080 display or projected screen, 12--13 px text renders at ~1.1--1.2 mm physical character height on standard presentation screens. When viewed from 5--10 meters away in a defense room or lecture hall, sub-16 px labels (tile keys, card subtitles, arrow labels, table sub-headings, disclosure note) become illegible to committee members seated past the front row. Furthermore, thin 2px light gray borders (`#b9b9b9` and `#c2c2c2`) fail projector contrast under ambient room lighting.

Proposed fix:
Raise the floor for secondary text and labels to at least `0.65em` (~18--20 px), bump `.numtile .k` to `0.55em`, and replace pale border grays `#b9b9b9`/`#c2c2c2` with higher-contrast `--muted` (`#5c5c5c`) or `--ink-2` (`#3c3c3c`).
