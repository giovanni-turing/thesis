# Reviewer <-> Claude bridge — protocol v1.7 (stabilized 2026-07-27)

Transport: this directory (shared filesystem). `from_reviewer/` = reviewer's outbox,
`to_reviewer/` = Claude's outbox, `archive/` = processed mail (moved by the reader,
never deleted). `python3 validate.py` lints all messages and regenerates STATE.md.

## Message format
- Filename: `NNN_<slug>.md` — NNN = zero-padded sequence, strictly increasing PER
  DIRECTION (each side numbers its own outbox; gaps = lost mail).
- Header (fixed key-value form, NOT general YAML; all required unless marked):
  - `from:` `reviewer` | `claude`
  - `ts:` ISO-8601 with timezone
  - `re:` exact filename (without .md) of the message being answered, or `new`
  - `type:` `finding | question | response | rereview-request | ack | escalation | verification`
  - `authority:` (required on any message asserting AUTHOR ADJUDICATION as a
    heading) — must be one of the recognized registry values
    (`author`, `author-delegated:fable-5-2026-07-26`, `author-delegated:fable-5-2026-07-27-xhigh`)
  - `thread:` (required on finding/escalation and every reply in a dispute) stable
    dispute id, e.g. `D01-oracle-convention`
- Body: markdown. Cite as `path:line`. Numbers carry their derivation (artifact/DB
  command) — assertions without derivations have no standing.

## Dispute-round accounting (author directive)
- A dispute thread = `finding` -> `response` (counter) -> `response` (reply) = the two
  evidence rounds. After that, either side posts `type: escalation` on the same
  `thread:`; the AUTHOR adjudicates. Neither side closes a disputed thread
  unilaterally. STATE.md tracks per-thread round counts mechanically.
- Correctness, not agreement, is the endpoint. Neither side defers.

## Standing uses
1. Re-review requests (Claude posts build + resolution doc + scoped questions).
2. Findings and clarifications, either direction.

## Ground rules
- Reviewer is read-only on the manuscript (findings, not edits).
- No instructions to third parties through this channel.
- Claude auto-responds to factual/verification traffic; asks the author before
  anything that would commission heavy reviewer work.
- DOCUMENTED EXCEPTION (not machine-enforced): claude/003_type_fixed's `re:`
  names 002_state_received_hold but semantically answers the reviewer's third
  message — a pre-v1.1 threading defect, machine-undetectable, recorded here.
  v1.3 removed the inert allowlist (D02-4).
- v1.2 invariants (reviewer/005): thread propagation, sender enum + outbox
  ownership + ISO ts with offset, sequences from 001 gapless, unique basenames.
- v1.3 invariants (threads D01/D02): dispute chains built from the `re:` graph —
  one root finding, linear (no branches/cycles), <=2 responses, escalation only
  after the second response and terminal, threaded types restricted; strict
  header grammar (the header is a fixed key-value form, NOT general YAML —
  unknown/duplicate/empty entries rejected); nonempty bounded slugs and DNN-
  thread ids; sender-qualified `re:` validated end-to-end; STATE.md written
  atomically and never through a symlink. Timestamps are metadata, never order.
- v1.4 invariant (thread D03): evidence rounds must alternate — response 1 is
  authored by the non-finding agent, response 2 by the finding's author;
  escalation by either. A single agent cannot exhaust a dispute alone.
- v1.5/v1.6 (D26): `type: verification` is a terminal factual attestation
  introducing no counterclaim (body semantics not machine-checkable; the
  mechanical rules are): NOTHING may reply to a verification (global
  terminality); its `re:` must name an exact target (never `new`); in a chain
  it is valid only after the second response or an escalation, and only
  terminal. Escalation is terminal EXCEPT for a single following verification.
  Author adjudications are posted UNTHREADED with body-referenced thread IDs;
  a body asserting AUTHOR ADJUDICATION (as a heading) MUST carry an
  `authority:` header naming the delegation (033 grandfathered by exact
  identity); STATE marks escalated threads ADJUDICATED when an
  authority-bearing message references them.
- v1.7 (D26 round 3): the authority VALUE is validated against the registry
  (presence alone is insufficient; STATE trusts only registry values or the
  exact-identity 033 grandfather). A chain's terminal verification must be
  authored by the FINDING's author — the fixer can never attest its own fix
  closed. Unthreaded verifications are listed in STATE.
