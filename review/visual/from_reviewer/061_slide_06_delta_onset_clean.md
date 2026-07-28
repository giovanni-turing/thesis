---
from: reviewer
ts: 2026-07-28T13:35:00-03:00
re: 017_deck_delta_onset_slide7
type: ack
---

## Re-Verdict Report — Deck Slide 6 (DOM Section 7, `A week of bursts — too fast to react to`)

### 1. Delta Context
- **Target**: Slide 6 (`defense/deck_single.html#/6`, DOM section index 7) at commit `36c9212`.
- **Changed Element**: Median onset corrected from $6.0\text{ min} \to \mathbf{6.5\text{ min}}$ across prose and chart canvas.

### 2. Verification Evidence
- **HTML Lead Text**: `Median onset <b>6.5 min</b>, fastest <b>1 min</b>` verified in source and rendered DOM.
- **Canvas Chart (`#onsetStrip`)**:
  - Vertical dashed marker line re-positioned from $x=6.0 \to \mathbf{x=6.5}$.
  - Canvas text label `median onset 6.5 min` updated at $x=6.5$.
- **1080p & 50% Weak Projector Rendering**: Text and canvas marker verified in `~/tmp_deck_v2/slide_6_delta_1080p.png`. Dashed line and top canvas text label render clearly without overlapping adjacent data points.

### VERDICT: CLEAN (RE-VERIFIED AT COMMIT 36C9212)
