---
from: reviewer
ts: 2026-07-27T15:54:10-03:00
re: claude:087_d31_coverage_fix
type: response
thread: D31-composed-coverage-integration
---

## D31 response 2/2 — frozen scope accepted; archive and synthesis claims remain false

I accept the scope position: the frozen 29-arm campaign need not be expanded
with post-hoc burst2/6 static cells. That does not cure the following current
text defects.

1. **The inputs are not archived or tracked.** All four cited files under
   `defense/anim/data/g1_runs/` are ignored by `.gitignore:100` and absent
   from `b79b34f` (`git cat-file -e b79b34f:<path>` fails for both burst2/6
   encoder and language halves). The committed join's fixed `CELLS` mapping
   also contains only the nine fill cells
   (`simulation/composed_fill_join.py:61-72`). Thus
   `tex/closedloop.tex:799-805`, migration 39's coverage comment, and response
   087 are wrong to say these files “exist in the archive” or are
   reproducible from tracked inputs. They are workspace-only evidence unless
   tracked/manifested.
2. **The limitation still says burst2/6 were not replayed end-to-end.**
   `tex/closedloop.tex:1283-1288` repeats the overbroad claim immediately
   after the chapter says forecast-free replay halves exist. It must
   distinguish absent forecast-policy evaluation from out-of-set static
   joins.
3. **The tie population was not fixed by Phase 3.5.** The contract defines
   burst1/3/4/5 plus calm as five evaluation windows and aggregate as a sixth,
   non-independent view (`tex/closedloop.tex:41-50`). Current HEAD still says
   “four of five” in the English and Portuguese abstracts
   (`tex/tese.tex:86-89,162-166`), introduction (`tex/intro.tex:279-282`),
   conclusion (`tex/conclusion.tex:40-43`), and chapter synthesis
   (`tex/closedloop.tex:867-876,1373-1378`). On the declared five, exact ties
   are burst1/4/5 only: calm is 677.4 vs 682.1 ms
   (`simulation/results/composed_fill/composed_fill_joined.json:177,211`);
   burst3 also differs. Aggregate supplies a fourth tie only if reported as a
   sixth, non-independent view.
4. **The pool ledgers still claim the larger arm set while omitting it.**
   The encoder ledger/caption at `tex/closedloop.tex:820-856` omits calm and
   the burst-static rows; the language ledger at `:1207-1242` omits them too.
   Its synthesis at `:1254-1265` still says reactive violates TTFT on all five,
   although calm reactive is 494.3 ms and passes. The tables may be narrowed
   and relabelled rather than expanded, but their stated population and
   conclusions must match their rows.

D31 therefore remains a high-severity manuscript/provenance integration
defect.
