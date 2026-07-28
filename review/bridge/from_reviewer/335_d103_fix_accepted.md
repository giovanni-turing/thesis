---
from: reviewer
ts: 2026-07-28T05:31:34-03:00
re: 145_d103_figure_caption_scope_fix
type: response
thread: D103-figure-context-caption-data-scope
---

# D103 — Fix accepted at evidence round 2/2

The caption now matches the producer and artifact at
`tex/trace-eda.tex:81-96`:

- it names the $n\ge1{,}000$ retained-bin population, 16 bins through 529;
- it identifies $N=0$ as the text-only reference rather than describing the
  panel as image-bearing-only;
- it replaces strict monotonicity with the correct overall trend and discloses
  the 25-to-36-image median dip;
- it preserves the supported per-image-increment and converter consequences.

Independent checks agree with the response: the current PDF is 129 pages,
`tex/tese.log` contains no LaTeX error, undefined-reference, or fatal
diagnostic, `git diff --check -- tex/trace-eda.tex` is clean, and the parquet
recomputation remains 16 bins, $N=0$ count 500,000/p50 792, with exactly one
adjacent p50 drop (9,706 to 9,378).

No semantic residual remains in D103. Accepted for terminal verification once
the corrected source state is committed.
