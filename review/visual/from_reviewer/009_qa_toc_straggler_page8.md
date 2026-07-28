---
from: reviewer
ts: 2026-07-28T05:18:00-03:00
re: new
type: finding
thread: V09-qa-toc-straggler-page8
---

## MINOR: Two-line straggler TOC overflow on Page 8 before Section 2 heading

Rendered evidence:
- Page layout analysis of `defense/defense-qa.pdf` (pages 7--8):
  - Page 7 bottom ends section 8's TOC entries at item "A question I genuinely cannot answer. . . . 53".
  - Page 8 top opens with exactly two straggler TOC lines:
    1. `An examiner challenges a specific number and I cannot reconstruct it live. . . . . . . . 53`
    2. `The hostile examiner. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 53`
  - Immediately below line 2, Section 2 ("2 Opening: the thesis in one breath") begins on the same page.

Defect analysis:
The TOC / spine navigator (pages 3--8) fills pages 3--7 almost completely, spilling its final two question entries onto Page 8. This leaves a 2-line straggler TOC fragment at the top of Page 8 right above the major Section 2 heading, breaking the visual flow and section separation.

Proposed fix:
Adjust vertical spacing or line height in the TOC / spine navigator on pages 3--7 slightly (e.g. `\addtolength{\itemsep}{-0.5pt}` or `\enlargethispage{1baselineskip}` on page 7) to pull the last two entries onto Page 7, allowing Section 2 to start cleanly at the top of Page 8.
