---
from: reviewer
ts: 2026-07-28T17:57:00-03:00
re: 196_d119_reserved_wording
type: response
thread: D119-doi-publication
---

# D119 round 2 — availability wording fixed; concept-DOI wording remains premature

The present-tense publication defect is fixed.  The appendix now accurately
says the archive is “prepared for deposit” under a reserved DOI and that
registration is pending (`tex/apendice.tex:346-358`).
`REPRODUCIBILITY.md:78-85` is likewise explicit that the record is still being
archived and does not yet resolve.  Fresh checks still return 404 from DOI.org,
Zenodo, and DataCite, so retaining that pending-status language is necessary.

One in-scope residual remains at `REPRODUCIBILITY.md:86-87`: “new versions
under the same concept DOI” can be read as identifying the displayed reserved
DOI as the concept DOI.  Zenodo assigns distinct identifiers at first
publication: a DOI for the specific version and a concept DOI grouping all
versions.  The public metadata needed to distinguish them does not yet exist.

Use wording that does not pre-assign their identity, e.g. “Corrections after
examination will appear as new versions grouped under the Zenodo concept DOI
assigned at publication.”  Once the record is public, report both exact fields
from Zenodo metadata (`doi` and `conceptdoi`) and keep the dissertation link on
the intended immutable version.  D119 otherwise passes.
