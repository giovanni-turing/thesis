---
from: claude
ts: 2026-07-27T17:21:00-03:00
re: reviewer:071_composed_mixed_estimators
type: response
thread: D30-composed-mixed-estimators
---

## D30 fixed: producer-persisted single-estimator evidence; view derives from it

Accepted in full (commits c6349c8 + b79b34f).

1. **Producer evidence.** The join now persists, per cell, the
   full-precision SELF-CONSISTENT relation: `conv_sum_minus_e2e_ms`
   (CONV sum minus composed p99, 6 decimals) and `conv_sum_relation`
   (overstates / understates / coincides, |delta| <= 1e-6 ms).
   Regeneration reproduces your analysis digit-for-digit:
   burst3/static +0.127588 ms (overstates, your 1481.159797 -
   1481.032209); steady24h/static -4e-9 (coincides); steady24h/fc
   -45.815998 ms -- the ONE genuine understates row.
2. **Persisted and derived.** Migration 39 adds both columns to
   `composed_e2e` (CHECK-constrained), K16 ingests them (DB verified:
   7 overstates / 1 understates / 1 coincides across the nine fill
   rows), and the `v_joint_e2e` comment is rewritten: the corrected
   estimator-consistent classification over the 29 arms is
   14 / 1 / 14; burst3/static's "second above-the-sum case" is
   explicitly documented as a mixed-estimator artifact and
   steady24h/static's "strictly differs" as display rounding. The
   column comments (`e2e_vs_sum_evidence`,
   `naive_sum_minus_joined_ms`) now direct relation claims to the
   persisted evidence, never to re-differencing rounded columns.
3. **Method sentence.** `tex/closedloop.tex` now states what the code
   executes: the naive sum adds the report's TTFT p99 at its native
   0.1 ms precision to the unrounded encoder p99, and the
   estimator-consistent full-precision relation is persisted per cell
   in the artifact itself.

The manuscript's interpretation paragraph (1.0001x; only the calm-day
forecast genuine) was already correct and is unchanged. Suite 57/0/5
DELIVERY-READY.
