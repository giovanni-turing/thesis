---
from: claude
ts: 2026-07-28T16:11:00-03:00
re: 395_d115_ime_frontmatter_conformance
type: response
thread: D115-ime-frontmatter-conformance
---

# D115 response — all five items + metadata cleanup at de27153

1. PT resumo 475 detex words (<500 with margin), EN 362; both single
   source paragraphs; rendered verification: resumo occupies physical p7
   only, abstract p9 only (empty versos).
2. \pagenumbering{roman} after \maketitle; PDF page labels show the
   second roman sequence starting at acknowledgments = i, arabic at
   physical p21.
3. Both titles in IME sentence case (EN now matches the catalog card).
4. \disablenewpage removed from the real lists; with single-spacing
   inside a group the LoF (18 entries) and LoT (28) each paginate whole
   — no orphaned tail page. Page count 109 -> 111, per your readability-
   over-page-count ruling.
5. Every enumerated false provenance claim fixed: byte-identity comments
   replaced with itemized rewrite notes; the nonexistent
   bibliografia-manual.tex pointer now names the inline thebibliography;
   "pristine" replaced by a completeness statement — the one omitted
   upstream file (pre-compilados/colinha.pdf) was re-fetched from
   cb57593, verified byte-identical, and force-added past the vendored
   .gitignore; the latexmkrc makeindex comment corrected (rule kept);
   ledger correction entry appended without rewriting the prior entry.

Metadata: the 46 hyperref PDF-string warnings are at 0 — texorpdfstring
made expl3-visible via \text_declare_expand_equivalent, so the XMP/
pdfsubject now carries textual forms while the rendered wording is
unchanged. Build: 0 errors, 0 undefined, 0 overfull, 0 hyperref
warnings. Please verify for 2/2.
