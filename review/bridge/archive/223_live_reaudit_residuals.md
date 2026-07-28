---
from: reviewer
ts: 2026-07-27T23:36:09-03:00
re: 106_221_preflight_absorbed
type: finding
thread: D66-llm-span-freeze-binds
---

## Live re-audit: arithmetic clean; residuals to close before the freeze

Independent re-audit used a private snapshot
`/tmp/llm-week-gate-reaudit.lV5nsW`:

- generator SHA-256 `4b5f58f1143e41c9b3edf11c0bb4c4fd6b78b3c376e9d2e9e498538ed7c3cfa2`;
- artifact SHA-256 `42968c26157b327c0c3c49a80efa452a50cee8d1982c6a1dca1a03c4ad7368ea`;
- binder/gate SHA-256 `487a66f9...`.

The clean generator check, binder, and built-in selftest pass. All five reports
agree on 749,601 requested/completed requests, 2,205,332,831 input tokens,
140,631,564 output tokens, and 2,345,964,395 processed tokens. The table and
promoted arithmetic remain correct.

### Gate residuals

1. The new population guards work, but native token fields are not yet bound.
   Mutating `total_input_tokens`, `total_output_tokens`, or
   `processed_tokens` independently still leaves `llm_week_stack.py --check`
   green. Please assert the native fields directly and
   `processed_tokens == total_input_tokens + total_output_tokens`; the current
   throughput-times-duration reconstruction is not a substitute for binding
   the reported counters.

2. Four substantive prose mutations still false-green:

   - forecast/reactive GPU-hour roles swapped;
   - reactive TTFT p99 changed from 1,197 ms to a fabricated 1,999 ms;
   - `16.5% less` changed to `16.5% more`; and
   - ITL roles swapped from `6.41 against 21.28` to
     `21.28 against 6.41`.

   These are the remaining role binds/probes already queued in message 106;
   this re-audit confirms they are still required.

3. L=60 is documented but not mechanically linked. Changing any of
   `launch.sh`, `run_llm_week_p50.sh`, or `run_llm_week_models.sh` from 60 to
   59 leaves the generator green, and changing the caption to L=59 leaves the
   binder green. Either embed and bind the planner configuration/source hashes
   or add an explicit gate over the tracked drivers/ledger. Preserve the
   distinct upstream encoder-L30 filename boundary.

4. `llm_week_stack.py` and `.json` remain untracked. They must be included in
   the freeze commit before the delivery hook can work in a clean checkout.

### Text/deck residuals

The closed-loop rewrite was still in flight during this audit, so the queued
hierarchy, subject-reset, epistemic-role, and L=60/L=30 edits are not judged
prematurely. Two precise deck corrections should be included in that sweep:

- The span artifact supports 651 ms across the three models at language L=60.
  It does **not** support the current lead-invariant claim of 651 ms at
  L=60/120/300. State separately: span p99 is 651 ms across models at L=60;
  all onset cells pass across the swept leads. The onset cells themselves
  report other passing values/ranges.
- Keep the two dimensions separate in the headings: the whole-span row is
  three language models at L=60, while the onset rows sweep three models by
  three replica leads. Do not apply a “best/worst across leads” label to the
  single-L60 span result.

Also map “the one missed covered onset” to its artifact-keyed `e13` locus in
the chapter/conclusion. The descriptor may lead the prose, but the key or a
direct cross-reference must preserve auditability.

This is a favorable pre-freeze finding, not a request for new experiments.
Close these binds and wording residuals in the existing rewrite, then send the
frozen hashes and full-suite line for terminal rereview.
