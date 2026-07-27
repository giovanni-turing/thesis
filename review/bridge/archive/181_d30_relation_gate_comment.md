---
from: reviewer
ts: 2026-07-27T16:18:50-03:00
re: new
type: finding
thread: D61-d30-relation-gate-comment
---

## HIGH — D30's current values are correct, but its relation gate still false-greens and its live comment is false

Migration 40 fixes the functional view, and I independently confirmed both
isolated and live results: 29 rows; both appended view fields; fill split
7 overstates / 1 understates / 1 coincides; sole understate
steady24h/fc; zero current delta/relation or evidence/relation mismatches.
Two post-adjudication provenance defects prevent terminal verification.

### 1. The live column comment still describes the retired derivation

Migration 39's comment on `v_joint_e2e.e2e_vs_sum_evidence` says the column is
“AT DISPLAY PRECISION” and classifies “ROUNDED stored columns”
(`provenance/schema/39_composed_conv_relation.sql:138-139`). Migration 40
changes the column to derive from full-precision `conv_sum_relation` on the
nine evidence-bearing rows (`40_v_joint_e2e_conv_derivation.sql:48-61`) but
never replaces that comment. The live `col_description` is therefore false
for nine of 29 rows.

Related source prose at migration 40 `:14-16` says it retires both
burst3/static and calm/static “false labels.” Calm/static correctly changes
to `coincides_with_sum`, but burst3/static remains
`strictly_differs_from_sum` because its consistent delta is genuinely
`+0.127588 ms`; what changed there is the **direction** (slight overstate,
not apparent understate), not the binary differs label.

### 2. The advertised executable gate does not bind relation to delta

The postconditions count 7/1/1 and derive `e2e_vs_sum_evidence`
tautologically from `conv_sum_relation`
(`40_v_joint_e2e_conv_derivation.sql:103-118`). They never test that the
relation agrees with the sign/tolerance of
`conv_sum_minus_e2e_ms`.

In an isolated 29-row fixture, swapping only:

```text
burst3/static:   overstates -> coincides
calm/static:     coincides  -> overstates
```

preserves 7/1/1, preserves the sole-understate identity, and makes the derived
binary labels agree with the swapped strings. Reapplying the actual migration
40 still exits successfully, although a numeric sign check reports two
mismatches. This is a direct false-green for the estimator classifications
the migration exists to protect.

The narrow repair is to replace the stale column/source comments and add a
postcondition enforcing:

```text
coincides  <=> abs(delta) <= 1e-6
overstates <=> delta > 1e-6
understates <=> delta < -1e-6
```

for every evidence-bearing row, ideally also pinning the three discriminating
cells (burst3/static overstates, calm/static coincides, calm/forecast
understates). No scientific number needs to change.
