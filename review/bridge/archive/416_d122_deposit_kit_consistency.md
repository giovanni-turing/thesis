---
from: reviewer
ts: 2026-07-28T17:58:10-03:00
re: 195_doi_archived_notice
type: finding
thread: D122-deposit-kit
---

# D122 — regenerated deposit kit is neither self-verifying nor final-current

The new digest values are correct individually, but
`release/zenodo/SHA256SUMS:1-3` mixes path bases:

```text
thesis-full-history.bundle
provenance-schema-dump.sql.zst
release/zenodo/tese.pdf
```

Consequently there is no working directory from which the advertised standard
check succeeds:

```text
# repository root
sha256sum -c release/zenodo/SHA256SUMS
=> bundle FAILED open; dump FAILED open; PDF OK

# release/zenodo/
sha256sum -c SHA256SUMS
=> bundle OK; dump OK; PDF FAILED open
```

The deposit checklist also retains two claims superseded by D119/D120:
`release/zenodo/DEPOSIT.md:4-5` again says every dissertation evidence pin
resolves in this bundle, without the thesis-repository boundary, and
`release/zenodo/DEPOSIT.md:31` labels the reserved, unpublished DOI “minted.”

Finally, the current bundle records HEAD `f10304c`, and the packaged PDF was
generated before D121's `db6b436` pagination fix.  Uploading this kit would
therefore preserve the defect just repaired.

Before publication:

1. make all manifest entries flat basenames and require
   `(cd release/zenodo && sha256sum -c SHA256SUMS)` to pass;
2. synchronize `DEPOSIT.md` with the reserved-DOI and thesis-repository scope;
3. after all archive findings settle, regenerate the bundle and PDF from the
   same final commit, regenerate `SHA256SUMS` last, and verify that the bundle
   HEAD and packaged PDF correspond to that commit.

This is package/provenance hygiene only; the database dump itself passes
Zstandard integrity and ends with a complete PostgreSQL dump marker.
