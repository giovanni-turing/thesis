---
from: reviewer
ts: 2026-07-28T05:48:14-03:00
re: 156_deck_content_parity_note
type: verification
---

# Deck content-parity note — independently verified

Commit `36c9212` changes exactly the three stale onset representations in both
deck mirrors: visible text, canvas marker coordinate, and canvas label now use
6.5 minutes. The authoritative producer artifact
`analysis/trace_eda/i_burst_anatomy_stats.json` independently reports 18
merged episodes, onset p50 6.5 minutes, and minimum 1 minute.

The current `defense/reveal/index.html` and generated
`defense/deck_single.html` contain no “no trace history,” “memoryless,” “dense
sweep of 69,” or “69 batch sizes” occurrence. The silicon tile states
attention agreement as approximately 3% and the composed vLLM result as 12.8%
over $N\le64$. Rebuilding the single-file deck embeds five animations and
reproduces the committed file byte-for-byte; both deck paths remain
diff/whitespace-clean.

The factual parity notice is verified. This verification does not inspect or
adjudicate the separate visual-review mailbox.
