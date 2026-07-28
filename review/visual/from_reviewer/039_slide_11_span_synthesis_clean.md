---
from: reviewer
ts: 2026-07-28T05:58:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 11: Span-Level Synthesis Matrix

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/11`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_11_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_11_50pct.png`)

### 2. Element & Matrix Analysis
- **Kicker & Heading**: `The economics, regraded` / `Same resource-time conclusion in the span-level synthesis`.
- **5x5 Synthesis Matrix (`.mmat`)**:
  - Headers (`.lhead`): `provisioned worker-time`, `total encoder delay`, `requests over 1 s`, `p99.99 delay` ($14\text{ px}$ post-V05).
  - Rows: `static C8`, `reactive`, `forecast p90` (winner blue row), `oracle`.
  - Cell text (`.mcell`): Numbers $15.5\text{ px}$, sub-deltas (`.mcell span`) $14\text{ px}$ post-V05.
- **Bottom Key Cards (`numtile`)**: 3 tiles (`no privileged threshold`, `no privileged bound either`, `windows = the validity gate`).

### 3. Contrast, Grid & Post-V06 Spacing Verification
- Post-V06 CSS padding adjustments reduced canvas content height from $880\text{ px} \to 823\text{ px}$.
- Bottom clearance above presenter controls expanded from $\sim 14\text{ px} \to \mathbf{41\text{ px}}$ ($101\text{ px}$ above bottom progress bar).
- All 25 matrix cells align horizontally and vertically with zero border clipping or text collision.

### Verdict: CLEAN
Vertical crowding resolved by post-V06 CSS spacing give-back; typography floor ($14\text{ px}$) verified.
