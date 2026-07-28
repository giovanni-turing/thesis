---
from: reviewer
ts: 2026-07-28T17:52:00-03:00
re: 195_doi_archived_notice
type: finding
thread: D119-doi-publication
---

# D119 — the asserted archived DOI is not public or registered

This merits a numbered round.  The new manuscript sentence makes a present,
externally falsifiable claim that the archive “is deposited” at
`10.5281/zenodo.21654632` (`tex/apendice.tex:350-355`), and
`REPRODUCIBILITY.md:76-85` repeats that the repository, bundle, and database
dump “are archived” there.

At 2026-07-28 17:50–17:51 -03, all three independent public resolution paths
failed:

```text
curl -ILsS https://doi.org/10.5281/zenodo.21654632
=> HTTP/2 404

curl -sS -D - https://zenodo.org/records/21654632
=> HTTP/1.1 404 NOT FOUND

curl -sS -D - https://api.datacite.org/dois/10.5281/zenodo.21654632
=> HTTP/2 404
=> {"errors":[{"status":"404","title":"The resource you are looking for doesn't exist."}]}
```

Zenodo's public record API likewise returns 404:

```text
curl -fsSL https://zenodo.org/api/records/21654632
=> curl: (22) The requested URL returned error: 404
```

The local deposit kit does contain a bundle and compressed dump, and
`git bundle verify release/zenodo/thesis-full-history.bundle` reports a
complete history.  All ten git-commit tokens cited in the dissertation are
ancestors of the bundle's recorded HEAD `16070c9`.  Those local facts do not
establish public deposition, however, and the inaccessible record prevents
verification of the uploaded file list, remote checksums, creator/ORCID
metadata, or version-versus-concept DOI.

Please either publish/finish registering the record or correct the identifier.
Once the public DOI resolves, provide the record/file manifest (including the
concept DOI reported by Zenodo).  I will then compare the deposited hashes
against `release/zenodo/SHA256SUMS` and adjudicate the archive wording and
pagination.  Until then, the present-tense manuscript and reproducibility
claims cannot stand.
