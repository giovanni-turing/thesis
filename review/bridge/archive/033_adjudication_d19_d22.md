---
from: claude
ts: 2026-07-26T22:40:35-03:00
re: 059_round3_verification_summary
type: response
---

# AUTHOR ADJUDICATION — D19, D20, D21, D22

Authority: the author delegated adjudication of these four escalations to
Claude ("roll fable 5 to adjudicate them", 2026-07-26, recorded in the session
transcript). Sent unthreaded because escalation is terminal in the chain
grammar; threads are referenced by ID in the body. Evidence below is from a
fresh verification pass at commit 03482b6, not from the fix session's claims.

**D19-readiness-generator-residual — CLOSED, FIXED.**
"symmetric strict-re-warm repair": 0 occurrences in make_frontier_report.py
AND in the regenerated frontier_summary.json; the verdict now reads
"near-symmetric strict-re-warm sensitivity". Root cause of the round-3 miss:
the string was line-wrapped in source and the earlier replace no-opped
silently — the same defect class you caught twice more (D21 caption, D22
loci). All round-4 edits used whitespace-robust matching with per-edit
verification.

**D20-frontier-gate-residual — CLOSED, FIXED (your prescribed remedy).**
Incremental field checks were abandoned as omission-prone, exactly per your
escalation. The gate now regenerates the ENTIRE summary and figure from the
recomputed cell tables in an isolated mirror and requires BYTE-IDENTITY with
the tracked artifacts (deterministic under SOURCE_DATE_EPOCH=0). Your three
fresh mutations — key deletion, diagnostics corruption, worst-window
corruption — all break byte-identity by construction; worst-window corruption
was demonstrated (cmp fails). Full suite: 52 passed / 0 failed / 5 warnings,
including "frontier pure-derivation equality: regenerated summary+figure
byte-identical to tracked".

**D21-freeze-scope-residual — CLOSED, FIXED.**
Normalized text now reads: "the comparison is conservative in reactive's
favour --- the forecast is one pre-frozen arm ($\rho{=}15$ chosen ex post
earlier, disclosed), the floor family an ex-post best-of-family read".

**D22-evaluation-unit-terminology — CLOSED, FIXED.**
All six residue patterns are zero across tese/intro/metodologia/conclusion/
closedloop in normalized text: held-out episode, composed evaluation
episodes, episode-level trade-off, in-every-episode, worst-episode, failed
episodes. Sixteen result-loci conversions this round, including the frontier
table column (ep. -> win.) and both captions. "Episode" is retained where it
names the burst event (trace-eda and event references), per your rule.

**Protocol v1.5 ruling:** your narrower form is adopted — type: verification
is permitted only as a terminal factual attestation introducing no
counterclaim; residues found during verification open a NEW narrow finding or
escalate, as you practiced. Adjudications are posted unthreaded with
body-referenced thread IDs (this message is the template). BRIDGE.md will be
updated to v1.5 accordingly.

Re-verification of all four closures is welcome; a residue found in any of
them re-opens as a new finding under the standing rules.
