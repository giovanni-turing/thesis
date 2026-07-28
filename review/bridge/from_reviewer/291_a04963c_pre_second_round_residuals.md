---
from: reviewer
ts: 2026-07-28T04:33:04-03:00
re: new
type: ack
---

## Hold second-round acceptance: residuals in `a04963c`

Independent checks pass mechanically (metric-stack, negative selftest,
immutability, thesis 129 pages, defense 44 pages), but the exact commit still
has the following high-confidence precision/certification residuals.

### Main text

1. D80: `tex/predictors.tex:128-136` calls $h=1\ldots12$ at 15-second bins
   “15--180 seconds of lead.” These are forecast **target horizons**:
   `tex/closedloop.tex:332-335` defines $h=1$ as zero usable lead and $h=12$
   as 165 seconds. The next sentence already states the correct mapping.
2. D80: `tex/closedloop.tex:109-113` assigns the
   15/30/45/300-second lead grid to reactive **and static** comparators.
   Static is lead-invariant: `simulation/comparator_frontier_eval.sh:92-95`
   emits constant `[[0,C]]`; `$L$` only enters its tag.
3. D85: `tex/closedloop.tex:1163-1167` says encoder wall-clock violation
   duration is unavailable because per-request latency was not instrumented.
   The raw emissions do reconstruct every request's delay from completion
   timestamp minus arrival
   (`simulation/results/comparator_frontier/build_frontier_summary.py:84-100`;
   `simulation/results/comparator_frontier/metric_stack.py:55-65`). What is
   absent is a declared/reported temporal aggregation convention for
   wall-clock time in violation, not request-level latency evidence.
4. D90: EN/PT abstracts (`tex/tese.tex:120-124,223-227`) call the cheaper
   language bracket a “post-hoc re-selection of quantile and conversion
   scale,” then correctly label p70/s6 calibration-selected. Per
   `tex/closedloop.tex:1463-1483`, p70/s6 was selected on the calibration
   split; only p90/s6 was selected post hoc after the fold failure (quantile
   changes, scale remains 6). State the two statuses separately.

### D92 delivery guard

The full-row equality itself is now correct. Live read-only tests give
`exact=0`; a negative control changing only one cached `detail`, while
preserving row count and verdict triple, gives bidirectional diff `2`.

5. `provenance/verify_all.sh:77-96` runs both cache checks **before** the
   intentionally mutating `main.py` settle passes at `:146-179`. A newly
   ingested artifact can therefore stale caches after A3 and still end
   `DELIVERY-READY`. Repeat or move the row-count and full-content checks
   after the final database-writing pass.
6. `provenance/SCHEMA_GUIDE.md:1019-1028` remains a dated 2026-07-20
   four-row/old-count table but now annotates five-cache D92 status. Either
   preserve it as explicitly historical without the D92 annotation, or
   replace it with the current five-row snapshot.
7. `v_mv_stale` remains cardinality-only. If the separate full-content gate
   remains the design, narrow `verify_all.sh:85` and the SQL view comment
   from “all evidence caches fresh” to cardinality freshness. Also update
   the stale three-field comment at `verify_all.sh:88-90` to the five fields
   the query actually compares.

### Defense duplicates

8. Qualify the failing reactive subject as the floorless/matched-rating
   trailing arm at `defense/defense-qa.tex:103-113,1657-1658,1674-1676,
   2124-2126`; standing floors pass. At `:2105-2108`, say every **tested
   evaluation-passing floor in the reported sweep**, not every reactive
   configuration.
9. `:114-118` should say one additional **onset** miss. The pure forecast
   fails two whole folds: F6 is the genuine onset miss; F2 is incomplete
   archive coverage (`tex/closedloop.tex:918-947`).
10. Scope “every episode” at `:1804-1811` to every declared evaluation
    episode/window; the daily-fold audit is finer and has F2/F6 failures.
11. Attach the one-minute scope to the approximately two-point,
    twelve-step WAPE degradation at `:376-377,876-877,1533-1537`
    (`tex/predictors.tex:242-247,272-275`).

These are narrow edits. No new experiment is requested, and the current
artifact values remain consistent.
