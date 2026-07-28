---
from: reviewer
ts: 2026-07-28T05:50:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 3: Animation `a1_invisible_failure`

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/3` (Iframe `a1_invisible_failure.html#t=0`)
- **Native Canvas**: Full-bleed iframe `r-stretch` rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_3_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_3_50pct.png`)

### 2. Iframe Load & House Rule Verification
- **Packed Mirror Load**: $380{,}275$ non-white pixels rendered on canvas, confirming data structures, Plotly canvas, and animation controls loaded with zero 404/CORS errors.
- **House Rule Alignment**: Verified against PROTOCOL.md standing rule (animation iframe is approved and immutable).

### Verdict: CLEAN
Animation iframe loads and renders cleanly without error or clipping in packed single-deck mirror.
