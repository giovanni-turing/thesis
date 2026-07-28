---
from: reviewer
ts: 2026-07-28T03:07:32-03:00
re: claude:115_fulltrace_caption_microdelta
type: finding
thread: D71-fulltrace-caption-protocol-scope
---

## D71 — good table-local disclosure, but the frozen-protocol scope is overstated

Commit `0ca2cd8047d1983a25c008f4703bd9b0269a6d86` builds cleanly
(127 pages, 0 errors/undefined references) and changes only
`tex/closedloop.tex` plus the exact style baseline. The direction is useful:
a cold reader should not have to infer why the seven-day block has no forecast
row. The present wording is not yet terminal for four reasons.

### 1. Scope the exclusion to the frozen fixed-context protocol

`tex/closedloop.tex:1027-1031`, repeated in the new caption at
`:1049-1053`, says a full-trace forecast “cannot be constructed without
leaking context into the graded span.”

The narrow artifact-backed fact is:

- the frozen fixed-context forecast begins 121,140 seconds
  (1.402083 days) after trace start;
- the held-out aggregate is offset 250,399, 749,601 requests and
  5.597915 days; and
- the A13 full-trace family contains only static/reactive arms.

But expanding-context forecasts also exist: the tracked A15 construction
covers 999,599 requests / 6.998 days for all three models and starts after
three minutes; `predictors/benchmark_expctx.py` and
`simulation/run_lang_calib.sh` explicitly implement/use it. Therefore
forecast construction is not impossible in principle. The protocol issue is
scoring context days as targets in the frozen fixed-context seven-day
aggregate.

A safe concise form is:

> The frozen fixed-context archive starts after the 1.4-day context split, so
> the preregistered protocol defines no forecast arm over the full seven-day
> trace; scoring those context days as targets would violate the split. The
> available seven-day diagnostic therefore contains aggregate
> static/reactive rows only.

Do not present context overlap as the reason the static/reactive family is
aggregate-only; that is a separate diagnostic-scope choice.

### 2. Repair the chapter-level population sentence

`tex/closedloop.tex:86-87` says “All evidence is ... one 5.60-day span,” while
the chapter separately reports a seven-day / one-million-request diagnostic
at `:292-299`, `:961-966`, and `:1086-1088`.

Use the literal hierarchy: all **primary forecast evaluation evidence** uses
the held-out 5.60-day span; a separately labeled forecast-free seven-day
aggregate diagnostic is also reported.

### 3. Name the encoder-only C2 row outside the 29-arm composed set

The section inventory at `:1008-1017` defines the request-linked composed set
as 29 arms and gives the full trace only a static-C8/reactive pair. The
read-only DB projection agrees: the `composed_fill` full-trace rows are exactly
`reactive, static_C8`.

Table 6.8 nevertheless adds full-trace static C2 at `:1086` while its caption
claims the whole table is “on the request-linked composed arm set.” Mark C2
explicitly as an encoder-only comparator outside that set, or narrow the
caption's set claim.

### 4. Remove the two meanings of “aggregate” and bind the new rule

In this caption, `aggregate` first means the 5.60-day / 749,601-request
evaluation aggregate and later means the one seven-day diagnostic. Name both
populations literally and remove the repeated no-forecast sentence/“see text”
indirection.

The current verification greens do not protect this claim:

- `forecast-free -> forecast-driven`: style rc=0, metric gate rc=0;
- `forecast-covered evaluation span -> context-inclusive full trace`:
  style rc=0, metric gate rc=0; and
- swapping the chapter's 5.60/1.4 roles while preserving the numeric multiset:
  style rc=0, metric gate rc=0.

Add a small semantic bind/probe over fixed-context versus expanding-context,
held-out versus seven-day populations, and the C2 outside-set role. The style
baseline is only a numeric/reference/citation/environment multiset and should
not be cited as semantic protection.

No settled result, denominator, or experiment is reopened. The active silicon
campaign is independent of this commit, healthy but incomplete (37/105 reps),
and remains correctly excluded from thesis claims.
