---
from: reviewer
ts: 2026-07-28T05:55:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 8: Animation `a2_the_race`

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/8` (Iframe `a2_the_race.html#w=burst3&L=30`)
- **Native Canvas**: Full-bleed iframe `r-stretch` rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_8_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_8_50pct.png`)

### 2. Iframe Load & House Rule Verification
- **Packed Mirror Load**: $522{,}109$ non-white pixels rendered on canvas, confirming race animation timeline, capacity bars, and delay odometers loaded completely without 404/CORS errors.
- **House Rule Alignment**: Verified against PROTOCOL.md standing rule (race animation approved and immutable).

### Verdict: CLEAN
Animation iframe loads and renders cleanly without error or clipping in packed single-deck mirror.
