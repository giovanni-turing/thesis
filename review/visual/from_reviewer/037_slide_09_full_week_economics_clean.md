---
from: reviewer
ts: 2026-07-28T05:56:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 9: Full-Week Economics Comparison

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/9`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_9_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_9_50pct.png`)

### 2. Policy Bar & Typography Analysis
- **Kicker & Heading**: `The economics` / `A full week: the tail held at 0.62× the always-on cost`.
- **Policy Comparison Rows (`polrow`)**:
  - `static C=8`: $1.000\times$ worker-time, $644\text{ ms}$ p99 (`PASS`).
  - `reactive`: $0.709\times$ worker-time, $35{,}807\text{ ms}$ p99 (`FAIL`).
  - `forecast p90` (Winner): $0.623\times$ worker-time, $588\text{ ms}$ p99 (`PASS`).
  - `oracle`: $0.292\times$ worker-time, $588\text{ ms}$ p99 (`PASS`).
- **Typography Floor**: Bar labels (`.polbar .bar`), pass/fail badges (`.ep`), and policy sub-descriptions raised to $14\text{ px}$ floor post-V05.

### 3. Contrast, Grid & Spacing
- Policy cost bars visually proportioned to worker-time percentages.
- Winner row `forecast p90` highlighted with `--blue` border and soft blue background `#f4f9ff`.
- Canvas height $810\text{ px}$, leaving $95\text{ px}$ bottom margin clearance above progress controls.

### Verdict: CLEAN
No text overlap, misaligned bars, or illegible badge labels on Slide 9.
