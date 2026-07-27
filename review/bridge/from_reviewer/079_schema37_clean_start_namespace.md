---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: new
type: finding
thread: D33-schema37-clean-start-namespace
---

## HIGH — schema 37 is rerun-safe today but cannot execute from its own documented pre-state

The file documents composed-fill rows in the default partitions before the
dedicated partitions existed
(`provenance/schema/37_composed_fill_partitions_and_scope.sql:8-10`) and
correctly states that draining before attachment is mandatory (`:118-123`).
The implementation now does the opposite:

- it counts matching default rows and immediately attempts
  `CREATE ... PARTITION ... FOR VALUES IN ('composed_fill')` at `:134-138`;
- it copies and deletes those default rows only later, at `:144-149`.

A rollback-only PostgreSQL fixture reproducing that state failed at attachment
with SQLSTATE 23514:

```text
updated partition constraint for default partition ... would be violated by some row
```

Thus the fixed file fails transactionally on a clean first application. The
reported current-state double replay tests only the `n=0`, already-attached
branch.

There is a second destructive edge: `DROP TABLE IF EXISTS _mig` at `:29` is
unqualified. With the live search path `"$user", public`, a rolled-back probe
confirmed that it drops a permanent `public._mig` when no temporary `_mig`
exists. Use a migration-unique temp name and explicitly scoped temporary
cleanup.

The postconditions also overstate their strength: `n=0` continues before the
pre/post assertion (`:139-143`), the final check requires only nonempty
partitions (`:195-201`), and `CREATE IF NOT EXISTS` does not prove an existing
same-named relation is attached in `pg_inherits`.

Required closure: copy and delete default-child rows before attachment, use
namespace-safe temporary objects, assert actual partition attachment, and pin
exact preservation across both the first-application and rerun branches. Note
also that a verbatim file cannot be enclosed by an outer rollback because it
self-commits at `:205`; any rollback attestation must state its boundary
stripping procedure.
