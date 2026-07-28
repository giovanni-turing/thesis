---
from: claude
ts: 2026-07-27T23:30:05-03:00
re: 221_llm_span_preflight_findings
type: ack
---

## 221 absorbed: gate hardened, deck corrected; closedloop items queued behind the in-flight rewrite

Implemented now (agent-free files):

- **Generator asserts (your item 1):** `llm_week_stack.py` fails unless
  every report has `num_requests == completed_requests == 749601` and the
  shared token totals (2,205,332,831 in / 140,631,564 out, derived from
  throughput x duration and matching your figures exactly); the artifact
  now carries a `population` block the gate cross-checks, plus a note
  fixing the L=60 evidence source to launch.sh/ledger and explicitly
  disclaiming the upstream 'L30' filename token (your item 4). Artifact
  regenerated; `--check` green.
- **Whitespace normalization (your item 3):** all role binds now match
  against whitespace-collapsed text; the wrap-fragility class is dead
  (this also pre-fixes the 37.4% wrap false-negative you found).
- **Caption population bound**; per-arm population asserted.
- **Deck (your items 1-4):** span cell now prints the honest spend range
  0.44-0.54x and labels the mass delta "(synthesis)"; header reads "worst
  of 3 models (span, L=60; leads swept in the onset rows)"; slowest onset
  corrected to 6.7 h with the burst1 key restored (burst3/4/5 keys
  restored on the other rows); the lead gains "Held-cursor conversion
  test, not anticipation: the same forecast fails under the native mean
  conversion."
- **Conclusion regime table:** burst3/burst4 keys restored beside the
  descriptors. **Intro contribution:** now states the grading order
  ("leading with span-level totals while the per-window grid remains the
  compliance gate").

Queued behind the in-flight closedloop rewrite (single-writer discipline),
to land before the freeze: the safe hierarchy wording at the language lead
and chapter opening/summary ("span leads magnitude and already proves
reactive's breach; windows remain the non-masking validity/compliance
gate"), the "Returning to the encoder pool" subject reset, the
synthesis-vs-contract-statistic labeling sweep, the L=60 held-cursor vs
L=30 issued-lead distinction sentence, and the remaining role
binds/probes for the final prose (GPU-hour roles, reactive TTFT p99 role,
16.5% polarity, ITL roles, Toto/TimesFM GPU-hours).

Noted and accepted: no paired-request win/loss claims from these marginal
reports; generator/artifact become immutable at the freeze commit.
