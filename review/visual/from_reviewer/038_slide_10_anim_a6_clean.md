---
from: reviewer
ts: 2026-07-28T05:57:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 10: Animation `a6_the_week`

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/10` (Iframe `a6_the_week.html#t=0`)
- **Native Canvas**: Full-bleed iframe `r-stretch` rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_10_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_10_50pct.png`)

### 2. Iframe Load & House Rule Verification
- **Packed Mirror Load**: $756{,}949$ non-white pixels rendered on canvas, confirming 7-day replay controls, timeline canvas, and worker capacity charts loaded completely without 404/CORS errors.
- **House Rule Alignment**: Verified against PROTOCOL.md standing rule (week animation approved and immutable).

### Verdict: CLEAN
Animation iframe loads and renders cleanly without error or clipping in packed single-deck mirror.
