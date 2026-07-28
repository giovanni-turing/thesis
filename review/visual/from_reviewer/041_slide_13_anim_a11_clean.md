---
from: reviewer
ts: 2026-07-28T06:00:00-03:00
re: 007_per_image_deep_order
type: ack
---

## Per-Slide Deep Inspection Report — Slide 13: Animation `a11_llm_race`

### 1. Rendered Evidence & Dimensions
- **Source**: `defense/deck_single.html#/13` (Iframe `a11_llm_race.html#w=burst3&m=toto&L=60`)
- **Native Canvas**: Full-bleed iframe `r-stretch` rendered at $1920 \times 1080\text{ px}$ (`~/tmp_deck_v2/slide_13_1080p.png`)
- **Weak Projector Simulation**: $960 \times 540\text{ px}$ downscale (`~/tmp_deck_v2/slide_13_50pct.png`)

### 2. Iframe Load & House Rule Verification
- **Packed Mirror Load**: $513{,}786$ non-white pixels rendered on canvas, confirming LLM race timeline, TP2-replica staircase, TTFT/ITL p99 odometers, and GPU-h meters loaded completely without 404/CORS errors.
- **House Rule Alignment**: Verified against PROTOCOL.md standing rule (LLM race animation approved and immutable).

### Verdict: CLEAN
Animation iframe loads and renders cleanly without error or clipping in packed single-deck mirror.
