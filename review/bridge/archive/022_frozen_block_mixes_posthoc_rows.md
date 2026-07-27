---
from: reviewer
ts: 2026-07-26T21:08:09-03:00
re: 009_rereview_request
type: finding
thread: D13-frozen-block-mixes-posthoc
---

## Moderate/major — the "frozen five-arm protocol" table block mixes frozen arms with post-hoc diagnostics

The caption calls the seven-row upper block "the frozen five-arm protocol,
one evaluation pass" (`tex/closedloop.tex:476-495`). It contains:

- the clamp-released oracle marked by the dagger
  (`tex/closedloop.tex:505,528-533`), replacing the clamped frozen oracle;
- forecast strict re-warm (`tex/closedloop.tex:508`), an adversarial repair;
- `M=6 (ex post)` (`tex/closedloop.tex:513-514`), a family-envelope member,
  not the frozen `M=4` arm.

The report builder explicitly records the readiness/oracle repairs as
"NOT frontier arms" run after the frontier was fixed
(`simulation/results/comparator_frontier/make_frontier_report.py:362-365`).
`M=6` is likewise an ex-post envelope read, not one of the five frozen arms.

Those diagnostics are valuable, but presenting them inside a block labeled
the single frozen evaluation makes the protocol status false. Show the actual
five frozen arms in one block and the post-hoc envelope/repairs in a separately
labeled sensitivity block, or change the caption so it does not attribute all
seven rows to the frozen one-pass protocol.

