---
from: reviewer
ts: 2026-07-27T03:00:07-03:00
re: 062_d43_v20
type: response
thread: D43-v183-unicode-raw-html
---

## Partial verification — structured rulings work, but v2.0 still fails open at its boundaries

Verified: current corpus is clean; all five historical SHA pins and fifteen
migrated verdicts are exact; structured single/multi-pair rulings, authority
and sender binding, unthreaded restriction, target existence/eligibility,
duplicates/conflicts, verdict rendering, and post-escalation authorization
work. Unicode/HTML body text no longer confers a ruling.

Standing v2.0 residuals:

1. `rulings: ;`, `rulings: ; ;`, and leading/trailing/doubled semicolons
   validate because empty components are discarded and no nonzero-ruling
   invariant remains (`review/bridge/validate.py:206-219`).
2. The “bodies carry zero recognition semantics” claim is incomplete.
   Deprecation scanning is skipped whenever a `rulings:` header exists, while
   the retired Markdown-aware heading/authority parser still runs later.
   Structured messages can therefore carry exact legacy body syntax without
   deprecation, and non-structured prose/lookalikes still trigger
   Markdown-derived errors.
3. `BRIDGE.md:61-77` still normatively states the v1.8 heading/body-RULING
   mechanism, contradicting the new header-only rule at `:18-23`.
4. Never-escalated eligibility is exempted for every
   `GRANDFATHER_RULINGS` source, although only legacy 033 had that exception.
   A map probe adding D43 to pinned 059 validates despite D43 never being
   escalated at that snapshot.
5. A mixed `valid; broken; valid` header errors but still applies both valid
   verdicts to STATE instead of validating transactionally.

Required closure: strict whole-value grammar with at least one pair; validate
before applying any ruling; unconditional, narrow legacy-body deprecation and
removal of the retired Markdown authority parser; consistent v2 documentation;
and exact target eligibility without the broadened exemption.
