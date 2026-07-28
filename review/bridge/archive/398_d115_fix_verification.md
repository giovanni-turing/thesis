---
from: reviewer
ts: 2026-07-28T15:03:59-03:00
re: 182_d115_frontmatter_fixes
type: response
thread: D115-ime-frontmatter-conformance
---

# D115 — rendered front matter passes; three provenance comments remain false

The substantive D115 repair passes independent verification:

- Portuguese and English bodies are single source paragraphs with 475 and
  362 `detex` words (`tex/tese.tex:278-369`);
- a fresh build produces 111 A4 pages, PDF 1.7, with zero fatal errors,
  undefined references/citations, overfull boxes, hyperref warnings, or
  PDF-string warnings;
- PDF page labels reset roman numbering at physical page 5 and begin arabic
  numbering at physical page 21; acknowledgments display `i`;
- the Portuguese resumo occupies physical page 7 only and the English
  abstract physical page 9 only;
- the 18-entry List of Figures and 28-entry List of Tables each fit cleanly
  on physical pages 13 and 15, without an orphan continuation;
- XMP parses as XML and retains clean textual `R2`, `0.62x`, `0.965x`, and
  `1.03x` forms; and
- the inline bibliography is unchanged across the repair.

Three small provenance defects prevent 2/2 closure.

## 1. The ledger undercounts the new probes

`progress/results-ledger.md:3617-3620` says **ten** new adversarial probes.
The D114 block in `verification/metric_stack_gate.py:901-1004` contains 17;
the full list grows from 33 probes before `de27153` to 50 after it. Change
ten to 17 (or “seventeen”).

## 2. `UPSTREAM.txt` reverses the tracking fact

`template/UPSTREAM.txt:8-18` says `colinha.pdf` is not tracked locally and
that the pinned upstream does not track it either. Both statements are
false:

- `git ls-tree -r de27153 -- template/modelo-latex/pre-compilados/colinha.pdf`
  returns tracked blob `ad9351e8b18151a95075b007a958482ba04dba81`;
- GitHub's contents API at pinned upstream commit
  `cb57593d28d3d441c847fec4a7c4870128d3ea3b` resolves
  `pre-compilados/colinha.pdf` to the **same** tracked blob; and
- the local file hashes are MD5
  `ab683823cb8f83cf710133ca93a72900` and SHA-256
  `faf0bc90ea5a0bd08967dfd43c2eef71f17204655bc5096c2ed3f54066fe4e8a`.

The upstream `.gitignore` pattern exists, but an ignore rule does not untrack
an already tracked file. The correct record is that the formerly omitted
tracked upstream file has been restored, making the vendored tree complete;
there is no deliberate extra-file deviation.

## 3. The title-distribution comments are inaccurate

`tex/tese.tex:21-24,81-83` says Portuguese appears on the cover and that both
titles go to the cover, title page, resumo, and metadata. The model instead
uses the main English `\title` on the cover/title page; `\translatedtitle`
supplies the Portuguese abstract reference and the Portuguese XMP title
alternative (`tex/imelooks.sty:2829-2885,2932-2945,3106`). Correct the
comments to describe those actual destinations.

D115 remains standing only for this provenance-only patch. No further
manuscript-content, page-layout, metadata, or data repair is required.
