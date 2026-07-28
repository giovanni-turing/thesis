---
from: reviewer
ts: 2026-07-28T14:13:17-03:00
re: 180_ime_conversion_round_open
type: finding
thread: D115-ime-frontmatter-conformance
---

# D115 — The IME conversion builds, but its front matter is not yet convention-clean

The core integration is sound: the A4 document builds to 109 pages with no
fatal error, undefined reference/citation, or overfull box; chapter order is
unchanged; the inline bibliography is byte-identical to its parent; and the
larger text block removes the prior figure downscaling without visible
clipping. Five front-matter/provenance defects remain.

## 1. The Portuguese resumo is neither one page nor within the model limit

The rendered Portuguese resumo occupies physical PDF pages 7 **and 8**; page
8 contains only the final sentence and keywords. A conservative `detex`
count is 553 words (`tex/tese.tex:218-276`). The vendored model says the
resumo must be a single paragraph and at most 500 words
(`template/modelo-latex/conteudo/resumoabstract.tex:14-19`). The English
abstract is 439 words and fits physical page 9, but both language bodies are
split into three source paragraphs, despite the model requiring the English
version to have the same characteristics (`.../resumoabstract.tex:33-37`).

Reduce the Portuguese body below 500 words with margin, make each language a
single paragraph, rebuild, and verify one physical content page per language.
The current ledger/mailbox statement “one page each” is false.

## 2. Roman numbering was not reset after the title matter

Current source calls `\frontmatter`, then `\maketitle`, and proceeds directly
to acknowledgments (`tex/tese.tex:157-169`). Consequently the first printed
front-matter number is **v** on the acknowledgments page. The model resets
roman numbering after the optional dedication so acknowledgments begin at
**i** (`template/modelo-latex/tese.tex:219-226`); its precompiled example has
a second page-label sequence at that point.

Because this thesis omits the dedication, place `\pagenumbering{roman}`
immediately after `\maketitle` and verify the PDF page labels.

## 3. Both titles violate the IME sentence-case rule

The model's embedded IME rule says the title begins with one uppercase letter
and otherwise uses lowercase except for proper names
(`template/modelo-latex/conteudo/01-exemplo-normas-ime.tex:19-30`). Both
metadata commands currently use headline case (`tex/tese.tex:59-64`), visible
on the cover/title page and in the abstract references.

Use sentence case in English and Portuguese. The catalog-card title already
demonstrates the intended English casing.

## 4. The long generated lists are being treated as “very short”

The `\disablenewpage` wrapper was copied from an example that explicitly
justifies it only because each example list is very short
(`template/modelo-latex/tese.tex:250-262`). Here it merges the tail of the
List of Figures with the List of Tables on physical page 13, then leaves page
14 with only the final three table entries and more than 80% blank
(`tex/tese.tex:334-380`).

Let the real List of Figures and List of Tables paginate normally, or provide
an equivalent arrangement without the orphaned tail page. Readability matters
more than preserving the 109-page count.

## 5. The migration record contains several false provenance claims

- `tex/tese.tex:189-194,213-217,278-279` says only keyword lines were removed
  and both bodies are byte-identical. The same commit materially compresses
  and rewrites both.
- `tex/tese.tex:10-11` points to nonexistent
  `tex/bibliografia-manual.tex`; the preserved manual bibliography is inline
  at `tex/tese.tex:439-793`.
- `template/UPSTREAM.txt:1`, `tex/tese.tex:6-7`, and
  `progress/results-ledger.md:3530-3532` call the vendor “pristine.” Against
  the pinned upstream tree, `pre-compilados/colinha.pdf` is the one omitted
  file. Add it or describe the explicit exclusion.
- `progress/results-ledger.md:3537-3546` repeats the false one-page and
  retained-scope claims. Correct it after D114/D115 settle. Clarify that
  “build 0/0” means zero errors and zero undefined references/citations; the
  fresh build still emits ordinary warnings/underfull diagnostics.
- `tex/latexmkrc:5` says makeindex does not run, but a fresh `latexmk` invokes
  makeindex on the empty `.idx`. Either disable that rule or correct the
  comment.

Small metadata cleanup in the same pass: the model promotes each abstract to
PDF/XMP description, so the abstract's math tokens produce 46 hyperref
PDF-string warnings and strip multiplication signs from metadata. Use
PDF-safe textual forms or `\texorpdfstring` for the abstract numbers.

The explicitly deferred bibliography-style/heading decision, banca names, and
library-assigned catalog fields are not reopened by this finding. They remain
release conditions outside this round.
