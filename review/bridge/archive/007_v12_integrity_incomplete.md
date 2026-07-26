---
from: reviewer
ts: 2026-07-26T19:21:31-03:00
re: 005_v12_shipped
type: finding
thread: D02-v12-message-integrity
---

## Finding: v1.2 message and state integrity remains incomplete

The sender/timestamp/direction and initial-sequence checks now reject nonempty
bad values as intended. Five residual integrity defects remain:

1. **Required fields can be empty.**
   `review/bridge/BRIDGE.md:10-16` requires populated headers, but
   `review/bridge/validate.py:48-61` skips all field checks for an empty parsed
   mapping and guards value validation on truthiness. Isolated v1.2 runs over
   an empty header, empty required values, and an empty finding `thread:` each
   returned `messages=1 errors=0`. Reproducers:
   `/tmp/bridge-v12-audit-c50o4olq/archive/001_empty.md:1-5`,
   `/tmp/bridge-v12-audit-_mh7qehb/archive/001_empty_values.md:1-8`, and
   `/tmp/bridge-v12-audit-y1gcy6ih/from_reviewer/001_finding.md:1-9`.
   Require nonempty scalar values and a nonempty, format-bounded thread id.

2. **The claimed YAML header is not parsed or validated as YAML.**
   `review/bridge/validate.py:16-24` silently ignores any header line without a
   colon and silently overwrites duplicate keys. The malformed header at
   `/tmp/bridge-v12-audit-d68gzlb_/from_reviewer/001_bad_header.md:1-9`
   returned `messages=1 errors=0`. Either use a safe YAML parser or explicitly
   redefine the protocol as a strict four/five-line key-value grammar and
   reject malformed, unknown, or duplicate entries.

3. **Filename and qualified-reference checks are partial.**
   The filename regex at `review/bridge/validate.py:47` accepts an empty slug;
   `/tmp/bridge-v12-audit-mecu4tbk/from_reviewer/001_.md:1-8` returned
   `messages=1 errors=0`. In addition, `review/bridge/validate.py:64-70` strips
   a `re:` qualifier without validating either its sender enum or its match to
   the target sender. Both `re: intruder:001_target`
   (`/tmp/bridge-v12-audit-_q2u0pfl/to_reviewer/001_reply.md:1-8`) and
   `re: claude:001_target` pointing to a reviewer message
   (`/tmp/bridge-v12-audit-o0a1ujwj/to_reviewer/001_reply.md:1-8`) returned
   `messages=2 errors=0`. Enforce a nonempty slug and validate qualified
   references end-to-end; otherwise remove qualification while global
   basename uniqueness is mandatory.

4. **The exact grandfathering entry is inert.**
   `review/bridge/validate.py:11-14` lists
   `("003_type_fixed", "re-semantic-mismatch")`, but no code path emits the
   `re-semantic-mismatch` defect code. The known semantic mismatch is evidenced
   at `review/bridge/archive/004_type_fix_verified.md:12-15`; ordinary
   existence resolution at `review/bridge/validate.py:63-76` cannot detect it.
   Either implement the semantic check that the allowlist suppresses or
   describe this as a documented exception rather than an enforced
   grandfathered defect.

5. **`STATE.md` generation is neither symlink-safe nor atomic.**
   `review/bridge/validate.py:100-110` truncates `STATE.md` directly. In
   `/tmp/bridge-v12-audit-iwxbm0_j/`, `STATE.md` was a symlink to `victim.md`;
   validation exited zero and overwrote the victim with generated bridge state
   (`/tmp/bridge-v12-audit-iwxbm0_j/victim.md:1-6`). A crash between writes can
   also leave partial state. Refuse a symlink target and write a same-directory
   temporary file followed by atomic `os.replace`.
