---
from: reviewer
ts: 2026-07-28T05:53:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 6: Week of Bursts Plotly Chart

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/6`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_6_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_6_50pct.png`)

### 2. Element & Chart Analysis
- **Kicker & H2**: `The 7-day trace` / `A week of bursts — too fast to react to`.
- **Plotly Canvas (`week_data.js`)**: 7-day image rate time-series plot rendered cleanly. Episode markers `b1` through `b6` and `calm day` labeled with crisp contrast.
- **Chart Caption (`.chartcap`)**: Font floor $14\text{ px}$ post-V05.
- **Lead Handoff Paragraph**: Subtle transition note at bottom (`lead handoff`) in `var(--muted)` font color ($6.7:1$ contrast ratio).

### 3. Contrast, Grid & Spacing
- Canvas vertical height $840\text{ px}$, leaving $80\text{ px}$ bottom clearance above progress controls.
- Legend and axis labels pass weak-projector resolution test at 50% scale.

### Verdict: CLEAN
Chart renders with full data series, zero label collisions, and proper typography.
