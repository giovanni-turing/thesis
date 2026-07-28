---
from: reviewer
ts: 2026-07-28T03:34:28-03:00
re: new
type: finding
thread: D79-provenance-rebuild-manifest-navigation-drift
---

## D79 — provenance documentation drift blocks faithful reconstruction/navigation

No scientific result changes. Four documentation defects remain against the
live read-only store and tracked schema.

### 1. The manifest legend falsely equates a missing run prefix with file-only

`tex/apendice.tex:113-116` says `---` means file-only, and
`supplementary/manifest_full.md:62-64` strengthens this to “not ingested into
the store.” But rows marked with dashes at
`tex/apendice.tex:159-168,286-295` /
`supplementary/manifest_full.md:102-107` are present in non-run-keyed collector
projections:

```text
collector_kernel_ledger:
  phaseB/.../kernel_ledger_N1.json   22 rows
  phaseB/.../kernel_ledger_N64.json  22 rows
collector_cold_start_trial:
  phaseD_cold_start/trials.jsonl      3 rows
collector_encoder_fn, phaseE physical anchor:
  536 rows across 17 source files
```

Safe repair: define the dash as “no `current_runs` spine prefix; may be
file-only or ingested in a non-run-keyed projection.” Where space permits,
label these rows `collector_* (no run_id)`.

### 2. Published rebuild instructions and README snapshot are stale

`supplementary/SUPPLEMENTARY.md:68-73` advertises migrations `01`--`35`, while
tracked numbered migrations extend through
`41_conv_relation_gate.sql`. `provenance/README.md:72-81` applies only
`01_schema.sql`, the loaders, then 02/04/03, omitting migrations 05--41. The
correct concise recipe already exists at `tex/apendice.tex:93-95`: apply every
`provenance/schema/*.sql` in numeric order, then run the loaders.

The README's live-state claims are also stale:

```text
README                          live read-only store
91 tables                       210 ordinary + 4 partitioned tables
10 views                        59 views + 5 materialized views
1,961 source files              5,051 distinct ingest_log paths
71 drift rows, max 0.39%        185 rows, max |drift| 1.2375%
no grid summary table           grid_run_summary=1, grid_window=7
```

All 185 drift rows have matching row counts. Also,
`provenance/README.md:50-52` says every projection/raw row carries a
`run_id`; current collector and other keyless projections contradict this,
as `provenance/SCHEMA_GUIDE.md:1279-1286` already explains.

Safe repair: use the numeric migration loop from the appendix; update and date
the catalog snapshot; narrow the lineage universal to run-keyed projections;
update the grid-table status.

### 3. S6.8 points readers to nonexistent `source_ref` fields

`supplementary/SUPPLEMENTARY.md:260-270` names `source_ref` fields in
`frontier_summary.json` and `source_ref` values in schema
`{22,23,25,26,33}*.sql`. `rg source_ref` over those files returns zero.

The JSON actually uses `gate_and_frozen_parameters.*.source[]`; historical
manuscript paths appear in schema 22, 23, and 33, not 25/26.

Safe repair: say “source arrays and embedded source-path literals/comments”
and narrow the schema list to 22, 23, and 33.

### 4. The expanded manifest says nine EDA figures; there are six

`supplementary/manifest_full.md:77` calls
`fig:eda-ctx-vs-img` through `fig:eda-multires` “nine figures.”
`tex/trace-eda.tex` has six figure environments/labels at current lines
81/90, 160/168, 171/182, 223/230, 260/267, and 320/329.

Change `nine` to `six`.
