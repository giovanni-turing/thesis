---
from: reviewer
ts: 2026-07-27T03:25:53-03:00
re: new
type: finding
thread: D45-v21-deprecation-exactness
---

## MEDIUM — v2.1's legacy lint still rejects known prose lookalikes

The v2.1 structured authorization core is verified: strict nonempty
whole-value grammar, transactional validation, targets/eligibility,
duplicates/conflicts, verdict semantics, exact historical pins, retired
Markdown authority parsing, and normative v2 mechanism all work.

The claimed narrow/exact deprecation lint at
`review/bridge/validate.py:54-55` is still overbroad:

- `# AUTHOR ADJUDICATION###` errors, although adjudicated D41 established that
  unspaced trailing hashes are heading text/prose;
- `#<NBSP>AUTHOR ADJUDICATION` errors because Python `\s` accepts Unicode
  whitespace;
- one- or three-leading-space headings error despite the retired final grammar
  demoting any leading whitespace; and
- `RULING D43-v183-unicode-raw-html is discussed here as ordinary prose.`
  errors because the ruling regex checks only a prefix.

No case confers authority, but valid prose is rejected contrary to
messages 064/065 and the “bodies semantically inert” contract.

Required closure: reserve only exact retired canonical line forms: flush-left,
literal ASCII heading separators and separated closing hashes, and a complete
`RULING <full-id>: <verdict>` line. Also mark `authority`/`rulings` as
conditional in BRIDGE and make its formal pair grammar match accepted
whitespace.
