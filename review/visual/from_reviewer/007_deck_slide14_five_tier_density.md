---
from: reviewer
ts: 2026-07-28T05:16:00-03:00
re: new
type: finding
thread: V07-deck-slide14-five-tier-density
---

## MINOR: Excessive multi-tier vertical density on Slide 14 conclusion

Rendered evidence:
- 1920x1080 screenshot analysis (`~/tmp_deck_snaps/slide_14.png`):
  - Slide 14 (`Forecast the pool's own signal — spend the lead, hold the tail`) packs 5 distinct content tiers into a single slide:
    1. Kicker + H2 title heading
    2. `.herostrip` (4 key stat cards)
    3. Row 1 `.numrow` (3 number tiles: items 1, 2, 3)
    4. Row 2 `.numrow` (2 number tiles: items 4, 5)
    5. Disclosure box `.disclose` + closing `Obrigado` paragraph
  - Text rendered inside `.disclose` is forced down to `font-size: 0.5em` (~12 px) to fit within the slide boundary.

Defect analysis:
Attempting to present the complete conclusion summary (4 stat callouts, 5 structured contributions across 2 rows, a scope disclosure callout box, and a closing acknowledgement) on a single slide forces extreme content compression. As a result, the disclosure box uses tiny 12 px text and tight margins, reducing visual hierarchy and legibility during the presentation wrap-up.

Proposed fix:
Consolidate the 5 contribution tiles into 3 primary contribution tiles or simplify the `.herostrip` to give the disclosure box and closing text higher font size (`0.7em` / ~16--18 px) and proper spacing.
