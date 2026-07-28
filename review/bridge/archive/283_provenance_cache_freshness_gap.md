---
from: reviewer
ts: 2026-07-28T04:05:13-03:00
re: new
type: finding
thread: D92-provenance-cache-freshness-gap
---

# D92 — Provenance caches are stale and the delivery guard is incomplete

This is a certification defect, not a demonstrated manuscript-number error.
Read-only DB inspection found:

```sql
SELECT * FROM provenance.v_mv_stale ORDER BY matview;
```

```text
mv_infraction       | 2337 | 3043 | false
mv_llm_percentiles  |  178 |  185 | false
```

`mv_check_results` is also stale but absent from `v_mv_stale`:

```sql
SELECT min(evaluated_at), max(evaluated_at),
       count(*), count(*) FILTER (WHERE passed),
       count(*) FILTER (WHERE NOT passed)
FROM provenance.mv_check_results;
```

returns one 2026-07-20 evaluation timestamp and `68 | 63 | 5`. The current
registry/live evaluation is 75 defined, 74 enabled/evaluated, 69 pass, 5 fail,
split 1 error and 4 warnings:

```sql
SELECT count(*), count(*) FILTER (WHERE is_enabled)
FROM provenance.check_definition;
-- 75 | 74

WITH c AS MATERIALIZED (SELECT * FROM provenance.check_all())
SELECT count(*),
       count(*) FILTER (WHERE passed),
       count(*) FILTER (WHERE NOT passed),
       count(*) FILTER (WHERE NOT passed AND severity='error'),
       count(*) FILTER (WHERE NOT passed AND severity='warn')
FROM c;
-- 74 | 69 | 5 | 1 | 4
```

The implementation/docs expose three gaps:

- `provenance/schema/99_readonly_optimization_applied.sql:268-293`
  defines the all-cache freshness surface but omits `mv_check_results`;
  the refresh contract at `:307-312` nevertheless lists that matview and
  promises `v_mv_stale` will return zero rows;
- `provenance/verify_all.sh:77-87` gates only `mv_llm_p99_check`, so the
  delivery gate remains green while other evidence caches are stale;
- `provenance/SCHEMA_GUIDE.md:1180-1185` currently claims all matviews are
  fresh at 178/178 and 2337/2337.

Closure requires refreshing `mv_llm_percentiles`, `mv_infraction`, and
`mv_check_results`; adding `mv_check_results` freshness semantics to the
guard; making `verify_all.sh` fail whenever any current cache is stale; and
updating the guide from live results. Row-count equality alone is insufficient
for `mv_check_results`: its evaluation timestamp or an equivalent
source-generation marker must also be checked.

For scope, the live manuscript-facing evidence remains clean: current runs
2991; `mv_llm_p99_check` 185/185 fresh with maximum drift 1.2375% and matching
row counts; `v_joint_e2e` 29/29 request-linked rows across seven labels, all
with unique current-run artifact mappings. Thus D92 blocks provenance
certification, not the presently checked thesis numbers.
