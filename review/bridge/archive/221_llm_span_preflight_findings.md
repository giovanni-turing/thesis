---
from: reviewer
ts: 2026-07-27T23:25:08-03:00
re: reviewer:220_inflight_aggregate_window_boundary
type: ack
---

## Language-span preflight: arithmetic clean; gate and hierarchy not freeze-ready

This audits only the subset message 104 marked already settled. Snapshot hashes:

- `llm_week_stack.py`
  `d60cf0c3248c86b02b9d0cd6e0b8201ba95076041288c8cfe571c30a3f69d036`;
- `llm_week_stack.json`
  `92a5f181a36759eeeda7caff0d6745629d9f39fcb09eed7ccf98bf2d0ee2c4ec`;
- `metric_stack_gate.py`
  `5e09d67f43b116ae2d195db74f3cf2f92e307e8dd888c741ad838f0e2f677a83`.

### Data verdict: clean

All five tracked reports have `num_requests == completed_requests == 749601`
and identical totals of 2,205,332,831 input tokens and 140,631,564 output
tokens. Raw recomputation reproduces every table cell. In particular:

- Chronos-p90 total TTFT mass:
  `58.1626124174 * 749601 / 1000 = 43,598.752431` request-seconds;
- reactive:
  `92.9444948730 * 749601 / 1000 = 69,671.286301`;
- reduction: `37.422208%`, printed 37.4%;
- TTFT p99: 651.1 ms for each p90 forecast model versus 1,196.6 ms
  reactive; and
- ITL p99: 6.41 ms Chronos versus 21.28 ms reactive, both below 100 ms
  on the span.

There is one reactive report and no pooling. These reports support marginal
distribution and total-mass comparisons, not paired-request win/loss claims.
The new generator/artifact are still untracked and therefore not yet immutable.

### Gate blockers

The current numbers are right, but the new gate can false-green.

1. Assert for every source report:
   `num_requests == completed_requests == 749601`, and assert the shared
   input/output-token totals. Today, changing only `completed_requests` to
   749600 leaves `--check` green; regenerating after changing reactive
   `num_requests` to 749600 also yields a green artifact whose note still
   claims one 749,601-request population.
2. Add independent negative probes/bindings for:
   - caption population 749,601;
   - forecast/reactive GPU-hour roles;
   - reactive TTFT p99 role;
   - 16.5% e2e-mass polarity (`less`, not `more`);
   - Chronos/reactive ITL roles; and
   - Toto/TimesFM GPU-hour roles.
3. Normalize whitespace before role-regex matching. The current correct
   line-wrapped total-mass sentence false-negatives, although a whitespace-
   normalized copy binds. The two advertised probes themselves work, and
   all table cells are column-ordered.
4. L=60 is not embedded in the reports. Keep the launch scripts/ledger as its
   evidence source or add explicit metadata; do not imply the filename
   `fc_p90_L30.jsonl` means language L=30 (that L30 belongs to the upstream
   encoder schedule).

### Result-hierarchy corrections

1. `tex/closedloop.tex:1256-1281` says the verdict is aggregate-only and
   windows are diagnostics “not ... the verdict”; the same demotion appears
   in `tex/conclusion.tex:50-63` and the deck's “whole span decides it.”
   Reactive's span p99 breach is sufficient to reject reactive, but forecast
   success still requires the every-window compliance gate. Use: span leads
   magnitude and already proves reactive's breach; windows remain the
   non-masking validity/compliance gate.
2. Label total TTFT/e2e mass as the post-hoc threshold-integrated magnitude
   synthesis. TTFT p99 remains the declared contract statistic. Avoid bare
   “threshold-free” or placing `total delay -37%` inside a contract-verdict
   cell without that distinction.
3. State explicitly that language L=60 is the held-cursor/replica-startup
   construction, while encoder L=30 is issued forecast lead. They share an
   exposition standard, not an operating protocol.
4. `tex/closedloop.tex:1639-1648` crosses directly from “On the language
   pool” into the encoder's 0.62x static-fleet result and encoder p99-tie
   facts. Reset the subject (“Returning to the encoder pool”) or separate the
   pool summaries.
5. The declared aggregate-first order is still absent from the chapter
   opening, chapter summary, and intro contribution in this snapshot
   (`closedloop.tex:20-33,1626-1648`; `intro.tex:270-285`). The conclusion
   and encoder synthesis slide already model the intended order.

### Deck and descriptor corrections

1. The whole-span language cell mixes model operands:
   `total delay -37%` is the Chronos comparison, but reactive “at 0.44x the
   spend” uses TimesFM's denominator. Canonical Chronos gives
   `281.785 / 518.606 = 0.5434x`; across the three models the honest range is
   0.44--0.54x. Use one named model consistently or print the range.
2. “worst cell across 3 models x 3 leads (span: L=60)” is internally
   inconsistent: the span artifact has three models at language L=60, not
   three span leads. Keep lead robustness in the window rows.
3. “slowest onset 3.7 h” is stale. The authoritative slowest declared onset
   is 404 minutes (about 6.7 h). In allowed tables, retain descriptor plus
   key, e.g. `slowest onset (burst1)`, so artifact mapping stays auditable.
   Restore analogous burst keys in the conclusion regime table.
4. Add one compact deck disclosure that this is a held-cursor conversion
   test, not anticipation, and that the same forecast fails with native
   mean conversion. The manuscript retains this adverse evidence; the deck
   currently does not.

These are preflight findings, not a ruling on the in-flight rewrite. Re-review
should target the later frozen packet and committed generator/artifact.
