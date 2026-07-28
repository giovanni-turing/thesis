---
from: reviewer
ts: 2026-07-28T12:27:57-03:00
re: new
type: finding
thread: D112-crib-physical-replay-scope
---

# D112 — The replay crib pair reopens answer-boundary and scope defects

The evidence values are broadly faithful, but the spoken-answer form is not
yet safe in four places.

## 1. The insertion splits the preceding answer

The new pair begins at `defense/defense-qa.tex:1682`, before the preceding
“simulation admissible as science” answer reaches its existing conclusion.
In parent `f0affe0^`, the “positive case is ... counterfactual” paragraph and
its comparison-class `\Concede` immediately followed the clean-worktree
sentence. They now appear at `defense/defense-qa.tex:1714-1723`, after the new
follow-up `\A`, so TeX presents them as part of “what does the replay not
prove?” rather than as the conclusion/concession of the prior question.

Move the entire new Q/A pair after that `\Concede` block and before “The live
validation — how strong is it really?” This restores both answers' intended
ownership and makes the replay follow-up shorter.

## 2. “Yes” implies controller-in-loop hardware

The question asks whether the controllers themselves touched hardware and the
answer opens “Yes” (`defense/defense-qa.tex:1682-1684`). What ran on the GPU
was each arm's frozen batch dispatch, followed by frozen-composition retiming;
the controllers did not actuate or receive hardware feedback in a closed loop.
The later caveat cannot undo the oral first-impression.

Lead instead with the exact distinction:

> Their frozen dispatches did; the controllers themselves did not run
> closed-loop against hardware.

Then describe the physical replay.

## 3. The D110 scope sentence has returned

At `defense/defense-qa.tex:1691-1695`, “three facts hold across every service
representation” again introduces a third fact that applies only under
canonical vLLM. This is the same scope construction corrected in D110.

Use the ruled split:

> Across the service representations, static is lowest-p99 and the controller
> arms are near-tied ... . Under canonical vLLM, every arm passes ...

Retain the separate HF-eager engine-conditional sentence and the explicit
non-equivalence clause.

## 4. Eighteen probes are not a universal proof

“An 18-probe ... suite proves corrupted membership, reordered dispatch, or
changed fingerprints fail” (`defense/defense-qa.tex:1700-1702`) overstates a
finite corruption suite, especially because the suite itself distinguishes
live-enforced gates from post-hoc extractor guards.

Say that all 18 named injected corruptions are rejected loudly, or that the
suite demonstrates those tested failure modes are caught. Do not use an
unqualified universal “proves.”

Small precision cleanup in the same pass: report the reactive estimand either
as the verified `22,565.317 ± 0.935 ms` or coherently rounded
`22,565.3 ± 0.9 ms`, rather than a unit-rounded mean beside a decimal SD.

No manuscript or experiment change is required. The crib build itself is
clean: 62 pages, 134 questions, no LaTeX error or undefined reference.
