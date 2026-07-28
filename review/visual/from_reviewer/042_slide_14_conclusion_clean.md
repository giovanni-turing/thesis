---
from: reviewer
ts: 2026-07-28T06:01:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 14: Conclusion Summary

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/14`
- **Native Canvas**: $1600 \times 1000\text{ px}$ rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_14_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_14_50pct.png`)

### 2. Element & Tier Analysis
- **Kicker & Heading**: `Conclusion` / `Forecast the pool's own signal — spend the lead, hold the tail`.
- **Hero Stat Callouts (`herostrip`)**:
  - `0.62×` (blue `#2a78d6`), `588 ms`, `60/60` factorial cells, `52` planner replays.
- **Contribution Tiles (`numrow`)**: 5 contribution tiles across 2 rows (`1 · the characterization`, `2 · the forecast benchmark`, `3 · the silicon anchor`, `4 · the platform + the knee`, `5 · the closed loop`).
- **Scope Disclosure Box (`.disclose`)**: Blue border callout held at $0.6\text{em}$ ($14.4\text{ px}$) post-V05 floor.
- **Closing Statement**: `Obrigado. — questions welcome; every act has a live replay behind it.`

### 3. Contrast, Grid & Post-V07 Spacing Verification
- Post-V07 CSS margin updates restored tier separation: `.herostrip` bottom margin $15\text{ px}$, `.disclose` top margin $0.85\text{em}$, tile gaps $20\text{ px}$.
- Slide canvas height $937\text{ px}$, leaving $63\text{ px}$ headroom above controls.
- All text and borders exceed WCAG AA standards ($>4.5:1$).

### Verdict: CLEAN
Multi-tier vertical density and disclosure typography resolved by post-V05 floor and post-V07 spacing adjustments.
