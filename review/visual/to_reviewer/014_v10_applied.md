---
from: claude
ts: 2026-07-28T06:11:00-03:00
re: 010_qa_unwanted_space_before_punctuation
type: response
thread: V10-qa-unwanted-space-before-punctuation
---

# V10 applied — italic-correction gap before the semicolon suppressed

Root cause was not a stray source space: the source read
`\emph{not merged};` and the visible gap is the italic correction `\emph`
inserts before any punctuation not in `\nocorrlist` (default covers only
period and comma, not semicolons). Fix: `\emph{not merged\nocorr};`.
Rebuilt and re-extracted: the line now renders "not merged; data is
commit-pinned...". Note the locus had shifted to source line 2965 after the
QA reinforcement pass; your line 2501 referenced the pre-growth file.
