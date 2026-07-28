---
from: reviewer
ts: 2026-07-28T05:19:00-03:00
re: new
type: finding
thread: V10-qa-unwanted-space-before-punctuation
---

## NIT: Unwanted space before punctuation in Section 10 cram layer card

Rendered evidence:
- Inspection of rendered text on Page 49 of `defense/defense-qa.pdf`:
  - Section 10 ("Cram layer: rapid-fire numbers"), bullet 3:
    `• Upstream status: encoder dataset + system file are a draft PR (ai-dynamo/aiconfigurator #1312), not merged ; data is commit-pinned...`
  - Rendered output shows an unspaced gap before the semicolon: `merged ;`.

Defect analysis:
A stray space before the semicolon (`merged ;`) in `defense/defense-qa.tex` line 2501 creates a typographical flaw in the rendered quick-facts list on Page 49.

Proposed fix:
Remove the space before the semicolon in `defense/defense-qa.tex` line 2501 (`merged;`).
