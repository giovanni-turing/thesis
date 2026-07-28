---
from: reviewer
ts: 2026-07-28T05:52:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 5: Animation `a9_dataset_kde`

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/5` (Iframe `a9_dataset_kde.html`)
- **Native Canvas**: Full-bleed iframe `r-stretch` rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_5_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_5_50pct.png`)

### 2. Iframe Load & House Rule Verification
- **Packed Mirror Load**: $391{,}915$ non-white pixels rendered on canvas, confirming Plotly KDE canvas loaded completely without 404/CORS errors.
- **House Rule Alignment**: Verified against PROTOCOL.md standing rule (animation iframe approved and immutable).

### Verdict: CLEAN
Animation iframe loads and renders cleanly without error or clipping in packed single-deck mirror.
