---
from: reviewer
ts: 2026-07-28T05:51:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 4: Workload Multimodal Trace EDA

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/4`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_4_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_4_50pct.png`)

### 2. Element & Typography Analysis
- **Hero Stat Strip (`herostrip`)**:
  - `1M` requests, `7 days`, `50%` text-only, `972` max images/request.
  - Value size $2.1\text{em}$ ($34\text{ px}$), sub-labels (`.hk`) $18\text{ px}$ post-V05.
- **Bottom Key Cards (`numtile`)**:
  - `1 · concentration` (`numtile info`): Blue accent `#2a78d6`.
  - `2 · spikiness` (`numtile viol`): Purple accent `#4a3aa7`.
  - `3 · persistence` (`numtile grn`): Green accent `#008300`.
  - Card text (`.numtile .d`) font floor $14.5\text{ px}$.

### 3. Contrast, Grid & Spacing
- Vertical stack height $810\text{ px}$, leaving $95\text{ px}$ bottom clearance above progress controls.
- Contrast ratios range between $4.6:1$ and $18.2:1$, exceeding WCAG AA limits.

### Verdict: CLEAN
No text overflow, low contrast, or grid alignment defects on Slide 4.
