---
from: reviewer
ts: 2026-07-28T05:49:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 2: Invisible Failure Signal

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/2`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_2_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_2_50pct.png`)

### 2. Element & Typography Analysis
- **Kicker & Heading**: `The invisible failure` / `The failure is invisible in the signal everyone watches`.
- **Lead Text**: 2-line intro paragraph at $1.05\text{em}$ ($21\text{ px}$).
- **Hero Stat Cards**:
  - `29%` (`numtile ok`): Green `--good` (`#0ca30c`, contrast $4.8:1$).
  - `R² = 0.12` (`numtile info`): Blue `--blue` (`#2a78d6`, contrast $4.6:1$).
  - `5,000 ms` (`numtile bad`): Red `--critical` (`#d03b3b`, contrast $5.2:1$).
  - Sub-descriptions (`.numtile .d`) and card keys (`.numtile .k`): Font floor $14.5\text{ px}$ and $18\text{ px}$ post-V05.

### 3. Contrast, Grid & Spacing
- 3 equal-width columns ($31\%\text{ width}$ each with $2.5\%\text{ gap}$).
- Canvas height $720\text{ px}$, leaving $140\text{ px}$ top/bottom margin clearance.

### Verdict: CLEAN
No text clipping, misalignment, or legibility issues on Slide 2.
