---
from: reviewer
ts: 2026-07-28T17:58:20-03:00
re: new
type: finding
thread: D123-catalog-title
---

# D123 — author-approved title change did not reach the catalog card

The new title is consistently used on the cover, title page, XMP metadata,
license, and defense decks, but the inline catalog card still carries the old
English title.

- Canonical title: “Forecast-informed vision-pool provisioning for
  modality-disaggregated **model** serving” (`tex/tese.tex:93-98`).
- Catalog card: “... modality-disaggregated **multimodal** serving”
  (`tex/tese.tex:154-159`).
- The nearby source comment now falsely says the catalog card has exactly the
  canonical spelling (`tex/tese.tex:88-92`).

A fresh 113-page PDF reproduces the mismatch on its front-matter catalog page,
and the currently prepared `release/zenodo/tese.pdf` already contains it.
Update the known title field in the inline card to the author-approved title
and correct the comment.  The explicitly library-assigned page-count and
CDD/CDU TODOs can remain pending; they are a separate deposit-stage step.
