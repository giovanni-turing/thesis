---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D98-worker-hour-operand-selection-scope
---

# D98 — Threshold-free arithmetic is conflated with convention-free arm selection

The new quick-facts card says that no SLA cut or percentile selection enters
either operand of the 669.7-versus-1,074.8 worker-hour headline
(`defense/defense-qa.tex:2549-2552`). That is true only of the integration
arithmetic **after the arms are fixed**, not of the operands' identities.

- The 669.7-hour arm is explicitly the Chronos **p90** schedule
  (`tex/closedloop.tex:983-988`), and the surface generator passes the selected
  quantile into schedule construction
  (`simulation/run_44_week_surface_issuetime.py:35-48`).
- The deployable static $C=8$ arm is the minimum fleet surviving all windows
  under the evaluation SLA: the grid defines $C^*$ by SLA feasibility
  (`tex/closedloop.tex:140-157`) and then takes the single fleet surviving every
  window (`tex/closedloop.tex:186-191`).

The rigorous convention-minimized claim is: **given the declared population
and these fixed arms, integrating provisioned worker-time uses no burst
definition, latency threshold, or percentile aggregation.** Selection of the
forecast arm still names p90, and selection of deployable static still depends
on the SLA feasibility rule. Please preserve that distinction in the mnemonic.
