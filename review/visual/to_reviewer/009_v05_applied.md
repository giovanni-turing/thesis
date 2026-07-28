---
from: claude
ts: 2026-07-28T06:06:00-03:00
re: 005_deck_subscale_lecture_hall_typography
type: response
thread: V05-deck-subscale-lecture-hall-typography
---

# V05 applied — deck minimum font size raised to 14px, CSS-only

All enumerated classes raised: `.numtile .k` 0.4→0.55em, `.disclose`
0.5→0.6em, the ten 12/12.5/13px classes → 14px, and the low-contrast grays
(`#b9b9b9`/`#c2c2c2` across `.reps u`, `.parr .ln`, `.ln.dashed`,
`.ln::after`) → `var(--muted)`. Three classes beyond your enumeration were
also below floor and raised: `.lcell i` (12px), `.pcard .pk` and `.chartcap`
(13.5px). The deck now contains no font-size below 14px.

One reflow regression surfaced and was fixed: at 14px the slide-13 whole-span
note pushed the verdict's trailing check onto a second line; `.lcell i` now
takes the flex slack so the note wraps inside its own box.

Zero HTML text changed (diff confined to `<style>`); animations untouched;
`build_single_deck.py` re-run; gate OK on both mirrors; all 15 slides
re-screenshotted at 1920x1080 with no overflow or collision.
