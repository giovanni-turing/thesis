---
from: reviewer
ts: 2026-07-28T15:26:00-03:00
re: new
type: finding
thread: D116-stale-tracking-provenance
---

# D116 — Three stale provenance statements remain after the tracking fix

The rendered thesis, D114 gate repair, corrected `UPSTREAM.txt`, and title
routing all pass. This new finding is confined to two comments and one ledger
count at `eb3249a`; no manuscript prose, layout, metadata, experiment, or data
rerun is involved.

## 1. The thesis header still says the restored PDF is hidden from Git

`tex/tese.tex:8-11` says `colinha.pdf` is present but the vendored
`.gitignore` “hides it from git, so it must be force-added to be tracked.”
That describes the pre-fix event as if it were current state. At `eb3249a`,

```
git ls-tree -r eb3249a -- \
  template/modelo-latex/pre-compilados/colinha.pdf
```

returns tracked blob `ad9351e8b18151a95075b007a958482ba04dba81`.
An ignore rule does not hide an already tracked file. State historically that
the ignored pattern caused the file to be skipped during the initial
vendoring, after which it was restored with `git add -f`; it is now tracked.

## 2. The ledger repeats the same stale current-state claim

`progress/results-ledger.md:3591-3593` says the file is “hidden from git ...
so it is now force-added.” Apply the same historical/current distinction:
initially skipped because the vendoring/add step honored the upstream ignore
pattern; subsequently force-added and now tracked.

## 3. The cumulative probe count is 19, not 17

Exact `len(PROBES)` counts are:

```
cffe34d   33
de27153   50
eb3249a   52
```

Thus the first D114/D115 repair added 17 mutation probes, and the residual
hardening at `eb3249a` added two more: **19 current round additions** relative
to the pre-round base. `progress/results-ledger.md:3620-3622` should say
“17 initial + 2 residual-hardening probes (19 total),” or equivalent. For the
same precision, the current full self-test comprises 52 mutation probes plus
three harness checks (live, relocated-clean, perturbed artifact), all passing.

This is a provenance-only patch. The independently rebuilt 111-page PDF,
live metric gate, full self-test, abstract pagination, page labels, lists, and
metadata remain clean.
