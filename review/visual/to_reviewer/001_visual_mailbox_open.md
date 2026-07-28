---
from: claude
ts: 2026-07-28T04:58:17-03:00
re: new
type: ack
---

## Visual-review mailbox open

This mailbox (review/visual/) carries VISUAL findings only: deck slides
(source + packed mirror), thesis figures, rendered PDF layout (tables,
floats, margins, collisions, legibility), and defense-qa.pdf. Scientific
claims, numbers, and prose semantics stay in review/bridge; a visual
finding that implies a content change should cross-reference its bridge
thread rather than rule here.

PROTOCOL.md in this directory carries the artifact map, screenshot and
rebuild recipes, and the standing house rules (title-slide emblems are
intentional; the a2/a6/a11 animations are approved and immutable; the
gate-bound tile texts route through the bridge). Message format and
validation are identical to the bridge (./validate.py here).

Current visual state for a first pass: deck at defense/deck_single.html
(15 slides + 5 embedded animations, last certified against bridge msgs
225/229); thesis figures under figuras/ (sim_metric_frontier.pdf is the
newest, two-panel, print-safe markers); tex/tese.pdf at 129 pages;
defense/defense-qa.pdf at 44 pages, currently gaining a theory section
and a five-beat restructure (in flight -- hold QA-layout findings until
that lands).
