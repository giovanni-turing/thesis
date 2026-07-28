---
from: reviewer
ts: 2026-07-28T03:29:17-03:00
re: new
type: finding
thread: D76-postfix-provenance-absolute-and-parenthesis
---

## D76 — two post-fix micro-residuals

### 1. The newly revised defense answer retains the provenance absolute

`defense/defense-qa.tex:1952-1955` says “every number maps to a versioned
script and archived artifact.” D73 correctly changed the introduction to
“nearly every quantitative claim” to match `tex/apendice.tex:12-16`, but the
same absolute remains here.

Safe repair: use the same qualified formulation, or scope it narrowly to the
headline operands discussed by this answer.

### 2. The rank-correlation repair has a surplus parenthesis

`tex/trace-eda.tex:291-294` currently reads:

```text
... (Spearman -0.06), with no monotonic trend in per-bucket median
generation), and at window level ...
```

Remove the closing parenthesis after `generation` (and reflow the line). The
scientific wording is otherwise correct.

No number, experiment, or adjudicated claim is reopened.
