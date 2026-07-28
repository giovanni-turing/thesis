---
from: reviewer
ts: 2026-07-28T05:54:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 7: Forecast Image Rate Method

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/7`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_7_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_7_50pct.png`)

### 2. Element & Typography Analysis
- **Kicker & Heading**: `The method` / `Forecast the image rate — spend the lead building capacity`.
- **Method Pillar Cards (`numtile`)**:
  - Pillar 1 (`numtile info`): `12-step zero-shot TSFM` (Blue `#2a78d6`).
  - Pillar 2 (`numtile warn`): `p90 provisioning band` (Orange `#eb6834`).
  - Pillar 3 (`numtile viol`): `30 s lead time` (Purple `#4a3aa7`).
  - Card titles (`.numtile .k`) $18\text{ px}$, descriptions (`.numtile .d`) $14.5\text{ px}$ post-V05.

### 3. Contrast, Grid & Spacing
- 3 equal-width columns ($31\%\text{ width}$ each with $2.5\%\text{ gap}$).
- Canvas height $780\text{ px}$, leaving $110\text{ px}$ top/bottom margin clearance.

### Verdict: CLEAN
No text overflow, low contrast, or grid alignment defects on Slide 7.
