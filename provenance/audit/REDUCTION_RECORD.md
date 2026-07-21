# Thesis length reduction + multi-POV adversarial verification (2026-07-20)

Goal (user): surface the shining points — the thesis was dense, hard to read, and long —
without losing any result or honesty caveat. Provenance DB + Appendix manifest already back
every number, so number-enumeration in the body is offloadable.

## Outcome

| | before | after |
| --- | ---: | ---: |
| Pages | 149 | **137** (−12 pp) |
| Body words | 38,373 | **30,532** (−20.4%) |
| closedloop | 9,394 | 7,314 (−22%) |
| Build | clean | clean, 0 undefined refs, 0 orphan refs |
| `verify_all.sh` | ready | **DELIVERY-READY** (30 pass / 0 fail) |

Baseline for all diffs: commit `3647cf3` (pre-reduction).

## Method

1. **Diagnosis** (`thesis-reduction-analysis` workflow, 12 per-chapter readers + synthesis):
   density is redundancy + number-dumping, not padding. Each headline restated 3–5× within
   and across chapters; closedloop (23% of the thesis) re-priced the three chapters before it.

2. **Pass 1 — conservative** (`thesis-reduce-apply`, all 13 chapters, edit→adversarial-verify→fix):
   −12%. Every must-survive finding + honesty caveat preserved (invariant: a lost finding is
   worse than missing target). Two cross-file dangling refs (deleted tables still `\ref`-ed from
   the appendix) caught and repaired by the fix stage.

3. **Pass 2 — assertive prose** (`thesis-reduce-apply-p2`, 10 under-cut chapters):
   reached −20.4%. **closedloop ledger tables locked** (`tab:cl-ledger-enc/llm/joint`,
   `tab:cl-aggregate`) — they are the load-bearing per-metric evidence (per-pool + joint
   improvements across p50/p90/p99, infraction intensity, GPU-h, cold-start), so only prose was
   cut. The per-burst *ledger* stayed; the prose re-narrating each burst is what was removed.

4. **Deep verification** (`deep_verify.js`, 6 adversarial lenses + refute + synthesis):
   forensic-diff, hostile seam-reader (per chapter); honesty-adversary, number/DB-consistency,
   table↔prose, acronym/ref (cross-cutting). **87 candidates → 16 confirmed → 14 after dedup**
   (73 refuted as nitpicks). All 14 fixed, adjudicated against HEAD + the provenance DB, applied
   with exact-match assertions. See `deep_verify_findings.json`.

### The 14 fixed defects (all reduction-induced)

- **HIGH** `validation.tex` — introduced overclaim: a cut deleted an honest qualifier, leaving
  "all three metrics agree within single-digit percent" while `tab:val-anchor` shows the forecast
  ITL differs +1.8 ms / 18%. Restored to table-faithful wording.
- **MEDIUM** `closedloop.tex` ×3 — restored the deleted "expanding-context span" definition
  (999,599 req / 6.998 days; without it "seven 24-hour folds" can't reconcile with the 5.60-day
  headline); onset descriptor flipped against its own figure (burst3 is the *fast* onset);
  `589 ms` floor typo → `588` (10 cells) vs 12 other sites + DB.
- **LOW** ×10 — dangling/circular appendix pointers, undefined acronyms (KVBM, ARIMA),
  a comma-splice, a subject-verb slip, a mistargeted `\ref` (physics → `sec:cl-matrix`).

## Preserved (not cut)

Every result, model, headline, and honesty caveat; the closedloop ledger evidence; the Appendix
reproduction manifest + env tables (the offload target); the Portuguese Resumo (USP-required).

## Artifacts

- `reduction_briefings.json`, `reduction_briefings_p2.json` — per-chapter cut plans
  (must-survive findings, cut list, ownership map, table-lock).
- `deep_verify.js` — the 6-lens adversarial verification harness.
- `deep_verify_findings.json` — the 14 confirmed defects with fixes.
