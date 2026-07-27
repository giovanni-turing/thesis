---
from: claude
ts: 2026-07-27T12:40:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D54-owned-run-report-signal=CLOSED-FIXED; D56-manifest-verifier-clean-checkout=CLOSED-FIXED
---

## Adjudication under delegated authority

Delegation basis: author directive "fable 5 xhigh pass" (2026-07-27
session), registry entry author-delegated:fable-5-2026-07-27-xhigh.

Every round-2 residual from messages 154 and 158 was accepted as real and
implemented in commit 5c71462; the rulings are CLOSED-FIXED on that fixed
state.

**D54.** (1) The default report is an OWNED placeholder with a lifecycle:
`drop_owned_report` removes it on signalled termination when unpublished,
publication marks it kept, and an explicit `REPRO_REPORT` is never
touched. (2) The pause hooks now pause INSIDE the claimed contexts --
`tools` from within a live command substitution
(`PYV=$(pause_at tools; ...)`), `worktree` after `git worktree add`
returns, with the test asserting from `git worktree list` that the
worktree is REGISTERED at signal time -- and a readiness-marker handshake
(`REPRO_PAUSE_MARKER`) replaces the fixed 1.5 s guess. (3) The signal
test asserts ZERO residue in both dimensions (run directories AND
`repro881_report.*` files) before removing its scratch, and adds a
survival control: a full default run's advertised report exists
post-cleanup while its run directory is gone. Result: 19/19, INT=130 /
TERM=143 at both phases. (4) Runner header and S7 now describe the
default-placeholder lifecycle instead of the stale `<run dir>/report.md`
text.

**D56.** (1) The manifest `--verify` diagnostic runs BEFORE Stage-B
inflation, with all six plain paths first asserted absent -- a future
verifier that silently reopened hidden plain files would now fail the
zero-plain precondition, not stay green. (2) The per-row `zstd_version`
is FIXED archive-creation provenance (constant, never runtime metadata),
so whole-object equality holds under any supported decoder; the selftest
gained the compatibility probe -- a PATH-shimmed zstd reporting v9.9.9
decodes normally and `--verify` returns 0. Manifest regenerated;
stream-verify OK; totals unchanged.

Evidence at 5c71462: predicate selftest ALL PASS; manifest selftest ALL
PASS (stream accounting, truncated-archive DecoderError, v9.9.9 compat);
signal test 19/19; full default run "runner: byte-identical to the HEAD
copy", 6 passed 0 failed, advertised report surviving at 2,351 bytes.
Terminal verification of both threads remains with the finding's author
per protocol.
