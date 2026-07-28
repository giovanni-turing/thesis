---
from: reviewer
ts: 2026-07-28T05:48:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 1: Two-Pool Provisioning Problem

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/1`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_1_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_1_50pct.png`)

### 2. Architecture Diagram & Tile Analysis
- **H2 Heading**: `Serving a multimodal model is a two-pool provisioning problem` ($1.35\text{em}$ / bold).
- **Process Cards (`pcard`)**:
  - Request ingress card (`pcard preq`): Sub-labels and metadata (`.psub`, `.pmeta`) raised to $14\text{ px}$ floor post-V05.
  - Encoder & Language pool cards (`pcard pool`): Knobs and replica indicators (`.knob`, `.reps u`) upgraded from `#b9b9b9` to `var(--muted)` ($6.7:1$ contrast).
  - Pipeline connector lines (`.parr .ln`): Dashed lines and arrowheads upgraded from `#c2c2c2` to `var(--muted)`.
- **Bottom Number Tiles (`numtile`)**:
  - 3-tile row (`numtile info`, `numtile warn`, `numtile viol`): Keys (`.numtile .k`) raised from $0.4\text{em} \to 0.55\text{em}$ ($18\text{ px}$).

### 3. Contrast, Grid & Spacing
- All text and borders exceed WCAG AA standards ($>4.5:1$).
- Vertical stack height $790\text{ px}$, leaving $105\text{ px}$ top/bottom margin clearance.

### Verdict: CLEAN
No collisions, illegible small text, or low-contrast line defects detected on Slide 1.
