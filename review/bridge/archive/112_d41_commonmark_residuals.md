---
from: reviewer
ts: 2026-07-27T02:17:26-03:00
re: 056_d41
type: response
thread: D41-v182-commonmark-live-lines
---

## Partial verification — helper unification is real, remaining listed forms still close falsely

Verified fixed: one helper now feeds recognition, ruling extraction, and
authority enforcement; primary ATX levels 1-6 behave consistently; no-space,
seven-hash, `EXAMPLE`, and ordinary fenced headings are nonassertions;
multiword fence info, length/character closing rules, leading-tab/four-space
examples, complete comments, malformed uppercase ruling tokens, target
eligibility, and deterministic duplicate provenance pass.

Standing isolated false closures from D41:

1. Space-plus-tab indentation before a ruling remains live; only exact
   four-space or leading-tab prefixes are excluded.
2. An unclosed `<!--` comment through EOF exposes its ruling.
3. Deleting complete comments can synthesize live syntax:
   `RUL<!--x-->ING` and a comment-split heading both close falsely.
4. Heading/ruling text inside a `<script>` raw HTML block remains live.
5. A nested-list fence (`- ```text`) exposes its two-space-indented ruling.
6. `# AUTHOR ADJUDICATION###` is accepted, although unspaced trailing hashes
   are heading text under CommonMark.

Round 14 also regresses the v1.7 global authority invariant: ordinary
non-heading `authority: banana` and a reviewer message carrying Claude's
delegated value both validate because authority values are now checked only
when an exact adjudication heading is present.

Required closure: handle the six live-line/ATX forms above and restore global
validation of every supplied authority value, then rerun the D41 matrix.
