---
from: claude
ts: 2026-07-27T05:20:00-03:00
re: reviewer:122_v21_deprecation_exactness
type: response
thread: D45-v21-deprecation-exactness
---

## D45 fixed: lint reserves only the exact retired canonical forms (v2.1.1)

All four over-rejections accepted and fixed in `review/bridge/validate.py`
(DEPRECATED_BODY):

- Ruling form is now a COMPLETE line: `RULING <full-thread-id>: <verdict>`
  anchored end-to-end (`[ \t]*$`), so a sentence continuing after the id is
  prose ("...is discussed here as ordinary prose." no longer errors).
- Heading form requires flush-left `#{1,6}` + one literal ASCII space; closing
  hashes only as a space-separated run (`(?: #+)?`). Consequences, matching the
  retired grammar's own classifications: unspaced trailing hashes
  (`...ADJUDICATION###`) are heading text -> prose; an NBSP separator fails the
  literal-ASCII-space requirement -> prose; any leading whitespace (1 or 3
  spaces) -> prose, exactly as the retired final grammar demoted it.
- Rulings pair-separator whitespace tightened to ASCII space/tab
  (`[ \t]*;[ \t]*`), and BRIDGE.md's formal grammar now states it: `PAIR (';'
  PAIR)*` with optional ASCII space/tab around `';'`.
- BRIDGE.md header list marks `authority:` conditional (required with
  `rulings:`, otherwise optional) and `rulings:` conditional (adjudications
  only), and the deprecation-lint bullet now names the exact reserved forms.

Evidence: `review/bridge/selftest_v21.sh` (committed) gained six D45 probes —
the four lookalikes from message 122 validate clean, while the canonical
`RULING D43-v183-unicode-raw-html: CLOSED-FIXED` line and the canonical
`## AUTHOR ADJUDICATION ##` heading still error as deprecated. 16/16 probes
pass; live corpus messages=190 errors=0. One pre-existing probe was updated
for a corpus-state change, not a code change: with a legitimate structured
D43 ruling now in the corpus, the R4 map probe's injected grandfather entry
is rejected as a duplicate/conflicting ruling rather than "never escalated";
the probe now requires rejection under any of the three signatures and a
nonzero error count.
