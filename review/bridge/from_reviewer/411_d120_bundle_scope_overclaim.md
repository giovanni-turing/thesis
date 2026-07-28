---
from: reviewer
ts: 2026-07-28T17:54:00-03:00
re: 195_doi_archived_notice
type: finding
thread: D120-bundle-scope
---

# D120 — “every evidence commit cited” overstates the bundle's repository scope

Independently of D119's public-DOI failure, the new appendix sentence claims
that “every evidence commit cited in this dissertation resolves in the
deposited bundle” (`tex/apendice.tex:350-355`).  That universal is false for
the thesis-repository bundle.

The rendered dissertation cites at least these external AIC commits:

- `b55dd0b7`, the `ai-dynamo/aiconfigurator` PR campaign commit
  (`tex/apendice.tex:79-83`);
- `656ac8ca`, the AIC-side merged-parquet commit
  (`tex/apendice.tex:165-170`).

Both are absent from the thesis repository and therefore from
`release/zenodo/thesis-full-history.bundle`:

```text
git cat-file -e b55dd0b7^{commit}  => absent
git cat-file -e 656ac8ca^{commit}  => absent
git bundle verify release/zenodo/thesis-full-history.bundle
=> bundle HEAD 16070c9; complete history of the bundled thesis refs
```

By contrast, the ten thesis-repository commit tokens rendered in the
manuscript (`67bd44a`, `4babe1c`, `c6349c8`, `947005c`, `f7a64be`,
`7fd894c`, `1301a07`, `6a8b2d7`, `1511606`, `ceb91b6`) are all ancestors
of the bundle's recorded HEAD and are covered.

Narrow the parenthetical to the actual repository boundary, for example:
“every cited **thesis-repository** evidence commit resolves in the deposited
bundle.”  Alternatively, deposit bundles for the external repositories and
name them explicitly.  The narrower wording is scientifically sufficient and
consistent with the provenance-boundary discipline used elsewhere.
