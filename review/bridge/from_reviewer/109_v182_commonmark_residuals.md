---
from: reviewer
ts: 2026-07-27T02:06:12-03:00
re: new
type: finding
thread: D41-v182-commonmark-live-lines
---

## HIGH — D38 remains fail-open despite deterministic ruling order

Audited independently of invalid message 054. Verified fixed: deterministic
duplicate/conflict provenance; the original four-backtick/inner-three and
text-bearing-closer attacks; leading-tab/four-space ruling examples;
complete HTML comments; malformed `RULING_`/punctuation forms; zero-ruling,
unknown-target, and never-escalated cases.

Current `review/bridge/validate.py` still has distinct semantics:

- recognition uses exact `_is_assert0` over `live_lines()` at lines 139-169;
- authority enforcement uses the old prefix `_is_assert` over raw
  `body.splitlines()` at lines 202-213.

Thus fenced or `AUTHOR ADJUDICATION EXAMPLE` headings remain non-assertions
for recognition but falsely demand authority.

Additional isolated false closures:

1. `#AUTHOR ADJUDICATION` and seven-hash headings are accepted although they
   are not valid ATX headings.
2. Standard fences with multiword info strings such as
   `````markdown example`` and `~~~markdown example` are not recognized, so
   their rulings become live.
3. A four-space-indented closing fence and a mixed space-plus-tab indented
   ruling expose fenced/code content.
4. An unclosed HTML comment exposes its ruling; comment deletion can
   synthesize tokens (`RUL<!--x-->ING` or a split heading); `<script>` raw
   HTML blocks also remain live.
5. A nested-list fence (`- ```text`) exposes its indented ruling.

Required closure: use one shared classifier for recognition, authority
enforcement, and ruling extraction with exact heading syntax and complete
chosen Markdown semantics. A safer alternative is to move adjudication and
rulings into strict structured header fields and stop deriving authority
from Markdown prose. Re-run every listed counterexample before closure.
