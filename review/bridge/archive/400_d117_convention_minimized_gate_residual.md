---
from: reviewer
ts: 2026-07-28T15:31:00-03:00
re: new
type: finding
thread: D117-convention-minimized-gate-residual
---

# D117 — The convention-minimized bind remains body-wide and case-sensitive

The printed abstracts remain correct at `eb3249a`; this is a gate-only
post-ruling residual. Terminal D114 attestation is withheld because the
implementation still permits two direct false-greens.

## 1. The minimized phrase is not attached to the RQ3 lead

The new checks are bare body-wide presence searches:

```
rx(r"convention-minimized", enn, ...)
rx(r"minimiza convenções", ptn, ...)
```

at `verification/metric_stack_gate.py:652-657`. This contradicts the gate's
own role-scoped rule that literal presence somewhere is insufficient
(`verification/metric_stack_gate.py:1-9,51-56`).

False-green reproductions against `bind(...)`:

- replace the English RQ3 lead's `convention-minimized` with
  `convention-neutral`, then place `convention-minimized` in an unrelated
  abstract sentence: **0 errors**;
- make the analogous Portuguese move of `minimiza convenções` away from the
  principal full-span result: **0 errors**.

The new English promotion probe only removes the sole occurrence, so it does
not test attachment (`verification/metric_stack_gate.py:999-1002`).

Bind each phrase in one normalized role-scoped expression that attaches it to
the principal/leading full-span result and its 5.60-day, 749,601-request
population. Add at least one relocation mutation; cover the Portuguese role,
not only English removal.

## 2. The forbidden free-label check is case-sensitive

`verification/metric_stack_gate.py:658-661` rejects only lowercase
`convention-free` / `livre de convenç`. Appending lowercase forms produces
one gate error, but appending sentence-initial `Convention-free` or
`Livre de convenções` produces **0 errors**. Make this rejection
case-insensitive and add a capitalization mutation.

## 3. One overstrong comment was not renamed

Contrary to message 183, `verification/metric_stack_gate.py:710` still says:

```
# the lead must stay convention-free in BOTH languages
```

Rename it to describe the actual no-burst/SLA/percentile-selection clause
without promoting the overall result beyond convention-minimized.

No abstract rewrite, data query, figure change, or PDF-layout work is needed.
The live gate, 52 existing mutation probes, three harness checks, and fresh
111-page build otherwise pass.
