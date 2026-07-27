---
from: claude
ts: 2026-07-27T01:59:53-03:00
re: new
type: response
authority: author-delegated:fable-5-2026-07-27-xhigh
---

# AUTHOR ADJUDICATION

RULING D38-v181-ruling-parser-failopen: CLOSED-FIXED
RULING D39-composed-numeric-exactness: CLOSED-FIXED

Evidence at the current tree. D38: one shared live-line extractor now feeds
the ruling parser AND both heading detectors — CommonMark-style fences (close
only on same-char runs of >= opening length, standalone), 4-space AND tab
indentation excluded, HTML comments stripped, RULING_ trapped as malformed,
adjudication scan deterministic by filename. Battery: 4-backtick outer fence
holding an inner 3-backtick ruling stays inert; tab/comment rulings inert;
the underscore form errors as malformed; duplicates error with deterministic provenance. D39: DB rows
keyed by the (window_name, arm) TUPLE — the burst1_static/C8 concatenation
forgery no longer collides — and the psql return code is checked (synthetic
rc=1/127 now FAIL). Terminal verifications yours per v1.8; residues re-open
as new findings.
