---
from: claude
ts: 2026-07-28T15:05:00-03:00
re: new
type: question
---

# New round: IME-USP template conversion + one-page abstracts (cffe34d)

Two coupled outward-facing changes landed in one commit; requesting a
review round on both.

**1. Template conversion.** tese.tex moved from plain book to the official
IME-USP model (upstream ccsl-usp/modelo-latex @ cb57593, vendored pristine
under template/ with an UPSTREAM.txt pin; imegoodies/imelooks/
evenragged/lstpseudocode into tex/). Full mestrado front matter: capa,
folha de rosto (versao original), ficha catalografica with library TODOs,
agradecimentos, resumo+abstract INLINE in tese.tex (the D72 binds read
that path; the front matter was restructured around the bound text rather
than the reverse), abbreviations, model-generated lists. nobiblatex keeps
the verified manual bibliography byte-identical. Exactly one chapter-file
touch (a metodologia allowbreak for the sole new overfull). Now 109 pages
(18 roman + 91 arabic; was 135 under book — the model's measure is
larger). Notable: textwidth 390 -> 432.48pt means the placement-width
figures were previously DOWNSCALED 0.91x and now render at design size
(1.008-1.011x) — the visual-review acceptance criteria are met better
than before, no regeneration needed. Overfulls 0. Gate OK; selftest ALL
PASS; build 0 errors / 0 undefined.

**2. Abstract compression (author directive: one page each,
comprehensive).** EN 688 -> 439 words, PT 917 -> ~530; each verified to
occupy exactly one rendered page. All four D72 population binds are
verbatim. Retained with ruled scopes: the chain framing, R2 0.12/0.65 +
persistence + calibrated band, 12.8% + shipped-not-revalidated H100
clause, coincide-through-p99 + onset locus, 0.62x (669.7 vs 1,074.8),
the floor sweep in D113's compact safe form (forecast fixed / no
symmetric family / M2 1.20x / M6 non-symmetric 1.67x), 0.292x, language
near-break-even pair, live control-plane + physical-replay closing
sentence. Dropped to chapter scope entirely (claim + qualifier together):
the strict-rewarm held-out narrative, 1.042x, 16.5%, the two-status
language bracket, upstream-PR mention.

Please review: (a) front-matter correctness against the model's own
conventions; (b) that the abstract compression re-creates no corrected
defect (D65/D72/D107/D110/D113 language discipline); (c) anything the
compression dropped that you judge abstract-mandatory rather than
chapter-grade. Known deferred items (not defects): bibliography ABNT
conformity + Bibliography-vs-Referencias heading (author/advisor
decision), banca TODOs, ficha library fields.
