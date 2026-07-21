export const meta = {
  name: 'thesis-reduction-deep-verify',
  description: 'Multi-POV adversarial verification of the reduced thesis: diverse lenses find real problems, refute stage keeps only confirmed',
  phases: [
    { title: 'Lens sweep', detail: 'diverse independent readers hunt distinct failure classes' },
    { title: 'Refute', detail: 'adversarial skeptic tries to kill each candidate finding' },
    { title: 'Synthesize', detail: 'dedup + rank confirmed problems into a fix list' },
  ],
}

// The 13 changed tex files (repo-relative). HEAD (3647cf3) is the pre-reduction baseline.
const FILES = (Array.isArray(args) ? args : (typeof args === 'string' && args.trim().startsWith('[') ? JSON.parse(args) : [
  'tex/aiconfigurator.tex','tex/apendice.tex','tex/apendice_ecosystem.tex','tex/baselines.tex',
  'tex/closedloop.tex','tex/conclusion.tex','tex/intro.tex','tex/predictors.tex','tex/related.tex',
  'tex/tese.tex','tex/trace-eda.tex','tex/twopool.tex','tex/validation.tex']))
const name = f => f.replace('tex/','').replace('.tex','')

const FINDINGS_SCHEMA = { type:'object', additionalProperties:false, required:['findings'],
  properties:{ findings:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['file','locus','category','severity','problem','evidence'],
    properties:{
      file:{type:'string'},
      locus:{type:'string',description:'line number or section/label where the problem is'},
      category:{type:'string',description:'e.g. lost-definition, dangling-reference, orphaned-header, non-sequitur, overclaim-introduced, dropped-qualifier, number-mismatch, prose-table-mismatch, undefined-acronym, broken-latex, choppy-prose'},
      severity:{type:'string',enum:['high','medium','low']},
      problem:{type:'string',description:'what is actually wrong now, concretely'},
      evidence:{type:'string',description:'quoted current text and/or the deleted hunk that caused it'},
      suggested_fix:{type:'string'} } } } } }

const VERDICT_SCHEMA = { type:'object', additionalProperties:false,
  required:['file','locus','is_real_problem','reasoning'],
  properties:{ file:{type:'string'}, locus:{type:'string'}, category:{type:'string'},
    is_real_problem:{type:'boolean',description:'true only if this is a genuine defect a committee reader would flag, not a nitpick or a false alarm'},
    confirmed_severity:{type:'string',enum:['high','medium','low']},
    reasoning:{type:'string',description:'why real or why refuted, having READ the actual current file'},
    fix:{type:'string',description:'the minimal concrete edit if real'} } }

phase('Lens sweep')

// ---- LENS A: forensic-diff (per chapter) — adversarially classify every DELETION ----
const forensic = FILES.map(f => () => agent(
`FORENSIC DELETION AUDIT of one reduced thesis chapter. Baseline HEAD (commit 3647cf3) is the PRE-reduction text. Run: git -C /home/gio/tese diff HEAD -- ${f}
Read EVERY deleted hunk (lines starting '-'). For each deletion decide, adversarially: was something RELEVANT lost? Flag a finding when a deletion removed any of:
- a DEFINITION or first-use expansion of a term/acronym still used later,
- a QUALIFIER that made a claim honest (simulated/mocked/calibrated/anchor/offered-work/single-trace/assumption/oracle/break-even/costs-more),
- the ANTECEDENT that a surviving sentence still points at ("as shown above", "the N cells", "these three", "the former"),
- a SCOPE LIMIT or caveat with no surviving trace,
- a load-bearing NUMBER not present elsewhere / not in the provenance manifest,
- a logical CONNECTIVE whose removal makes the surrounding prose a non-sequitur.
Do NOT flag routine enumeration/hedge/throat-clearing removals — those are intended. Only REAL losses. Quote the deleted text and the current surrounding text. Return structured findings (empty if the reduction was clean). Your text IS the data.`,
  { label:`forensic:${name(f)}`, phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' }))

// ---- LENS B: broken-seam reader (per chapter) — read CURRENT text as a hostile examiner ----
const seams = FILES.map(f => () => agent(
`HOSTILE CLOSE-READ of the CURRENT (reduced) chapter /home/gio/tese/${f}. You are a skeptical thesis-committee member who did NOT see the edits. Read it start to finish and find where aggressive cutting BROKE the text:
- dangling references: "as shown above/below", "the previous section", "these N", "the former/latter", "earlier we", pointing at content that no longer exists or no longer says that;
- orphaned \\paragraph{...} or \\subsection headers with little/no content, or two headers with nothing between;
- non-sequiturs: a sentence that no longer follows from the one before it because a bridge was cut;
- sentences that lost their subject/object/verb, doubled words, dangling clauses, broken enumerations ("First,... " with no "Second");
- an acronym USED here but whose expansion may have been cut (note it for the global acronym check);
- LaTeX that reads broken (stray braces, empty environments, "Section~\\ref{}" with no number).
Flag only genuine reader-facing defects. Quote the offending current text with its line number. Return structured findings. Your text IS the data.`,
  { label:`seam:${name(f)}`, phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' }))

// ---- LENS C: methodological-honesty adversary (cross-cutting) ----
const honesty = () => agent(
`METHODOLOGICAL-HONESTY ADVERSARY over the whole reduced thesis. The single worst failure mode is a cut that STRENGTHENED a claim beyond its evidence. Ground truth of the methodology: LANGUAGE pool = Dynamo discrete-event SIMULATION on calibrated H100 AIC timing (NOT real H100); ENCODER cost = REAL RTX 5090 silicon, physically validated, upstreamed to AIC; the live anchor = real Dynamo control plane with MOCKED engines (validates the control loop, NOT silicon); forecasts = offline archive; single 7-day Azure trace; per-burst every arm costs MORE than static (saving is 0.62x on the encoder worker-time denominator only); 588ms floor is an analytic single-stream/embedding-only assumption.
Method: run 'git -C /home/gio/tese diff HEAD -- tex/' and scan DELETED lines ('-') containing any of: simulat, mock, calibrat, anchor, silicon, real GPU, H100, offered-work, single, trace, assumption, oracle, break-even, costs more, floor, not, only, approximate. For each, open the CURRENT file at that spot and check whether the honest qualifier SURVIVES nearby. If a claim now reads stronger/unqualified where the qualifier was removed, that is a HIGH finding. Also re-read the abstract/Resumo (tex/tese.tex) and conclusion for any newly-bald claim.
Return structured findings; empty if honesty is fully preserved. Your text IS the data.`,
  { label:'honesty-adversary', phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' })

// ---- LENS D: number / DB consistency + internal contradiction (cross-cutting) ----
const numbers = () => agent(
`NUMBER-CONSISTENCY ADVERSARY over the reduced thesis. Two jobs:
(1) Internal contradiction: grep the CURRENT tex/*.tex for the key headline quantities and confirm each is stated CONSISTENTLY everywhere it appears (a cut must not have left the same quantity with two different values): 0.62x encoder cost, 0.96x language, R^2=0.12, Jaccard 0.02, 588 ms floor, 651 ms TTFT tail, 1240 ms composed p99, 12.8% vLLM fidelity, 21.9% naive-sum error on burst3, 16079 burst3 reactive encoder p99, 749601 aggregate requests, 5.60-day span, 87.7 ms 235B ITL. Report any site where a value disagrees with the others.
(2) DB cross-check: the provenance DB is Postgres schema 'provenance' at localhost:5433 (also via the technonous MCP postgres_query). Spot-check 5-8 of the above against the DB current_* views/tables where feasible. Report any prose number that contradicts the DB.
Use Bash grep across /home/gio/tese/tex and the MCP/psql for the DB. Return structured findings (category number-mismatch or db-mismatch); empty if consistent. Your text IS the data.`,
  { label:'number-consistency', phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' })

// ---- LENS E: table<->prose consistency, table-lock integrity (closedloop + table-heavy) ----
const tableProse = () => agent(
`TABLE<->PROSE CONSISTENCY ADVERSARY. Prose was cut while tables were kept; find prose that now points at table content that changed or vanished, and confirm the closedloop table-lock held.
(1) closedloop table-lock: run 'git -C /home/gio/tese diff HEAD -- tex/closedloop.tex' and CONFIRM the tabular bodies of tab:cl-ledger-enc, tab:cl-ledger-llm, tab:cl-ledger-joint, tab:cl-aggregate are UNCHANGED (only prose around them changed). If any numeric table cell/row/column/caption was altered, that is a HIGH finding.
(2) Across tex/closedloop.tex, tex/twopool.tex, tex/baselines.tex, tex/predictors.tex, tex/aiconfigurator.tex, tex/trace-eda.tex: for each surviving "Table~\\ref{...} shows/reports X" sentence, open the referenced table and confirm it still contains X (the row/column/value the prose claims). Flag prose that references a deleted row/column or a value no longer in the table.
Return structured findings; empty if consistent. Your text IS the data.`,
  { label:'table-prose', phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' })

// ---- LENS F: acronym + cross-ref semantic validity (cross-cutting) ----
const acronyms = () => agent(
`ACRONYM + CROSS-REF SEMANTIC ADVERSARY over the reduced thesis (tex/*.tex, root tex/tese.tex has a List of Abbreviations).
(1) Acronyms: build the set of acronyms USED in the body (e.g. TTFT, ITL, TPOT, WAPE, MAE, ACF, LRD, SOL, GEMM, ViT, TSFM, HPA, KV, ISL/OSL, CV^2, EWMA, AIC, DES). For each, confirm it is still EXPANDED at least once (List of Abbreviations OR first use). A cut may have removed a first-use expansion — flag any acronym used but never expanded.
(2) Cross-ref semantics: for a sample of surviving \\ref/\\autoref to sections/tables/figures across chapters, confirm the target label still exists (mechanical) AND the target is still the thing the prose implies. Flag semantically-stale references (e.g. "see Section~\\ref{X} for the N-cell sweep" where that content was cut).
Use Bash grep. Return structured findings; empty if clean. Your text IS the data.`,
  { label:'acronym-ref', phase:'Lens sweep', schema:FINDINGS_SCHEMA, effort:'high' })

const lensResults = await parallel([...forensic, ...seams, honesty, numbers, tableProse, acronyms])
const candidates = lensResults.filter(Boolean).flatMap(r => r.findings || [])
log(`lens sweep: ${candidates.length} candidate findings from ${lensResults.filter(Boolean).length} lenses`)

phase('Refute')

// Adversarial refute: an independent skeptic tries to KILL each candidate by reading the actual file.
const judged = await parallel(candidates.map(c => () => agent(
`ADVERSARIAL REFUTATION. Another agent flagged a possible defect in the reduced thesis. Your DEFAULT is that it is a FALSE ALARM; only confirm if you can prove it real by reading the actual file.
Claimed defect:
  file: ${c.file}
  locus: ${c.locus}
  category: ${c.category}
  severity(claimed): ${c.severity}
  problem: ${c.problem}
  evidence: ${c.evidence}
Open /home/gio/tese/${c.file} at that locus (and git -C /home/gio/tese diff HEAD -- ${c.file} if the claim is about a deletion). Decide: is this a GENUINE reader-facing defect (lost meaning, broken reference, introduced overclaim, wrong/contradictory number, undefined acronym, broken LaTeX) or is it fine (the meaning survives elsewhere, the cut was intended and clean, the reference still resolves)? If real, give the minimal concrete fix. Be strict: nitpicks and stylistic preferences are NOT real problems. Your text IS the data.`,
  { label:`refute:${name(c.file)}:${(c.category||'').slice(0,12)}`, phase:'Refute', schema:VERDICT_SCHEMA, effort:'high' })
))

const confirmed = judged.filter(Boolean).filter(v => v.is_real_problem)
log(`refute: ${confirmed.length}/${candidates.length} confirmed as real problems`)

phase('Synthesize')

const SYNTH_SCHEMA = { type:'object', additionalProperties:false,
  required:['summary','confirmed_problems','clean_verdict'],
  properties:{
    summary:{type:'string',description:'overall: is the reduced thesis sound? how many real problems, of what kinds?'},
    confirmed_problems:{type:'array',items:{type:'object',additionalProperties:false,
      required:['file','locus','severity','problem','fix'],
      properties:{ file:{type:'string'}, locus:{type:'string'}, severity:{type:'string'},
        category:{type:'string'}, problem:{type:'string'}, fix:{type:'string'} } }},
    clean_verdict:{type:'boolean',description:'true if NO high/medium confirmed problems remain (thesis is sound)'} } }

const synth = await agent(
`Synthesize the deep-verification result for the reduced thesis. Below are the CONFIRMED real problems (already survived adversarial refutation). Dedup (same file+locus), rank by severity (high first), and produce a clean fix list. State plainly whether the reduced thesis is sound.
CONFIRMED PROBLEMS (JSON):
${JSON.stringify(confirmed, null, 1)}
Return ONLY the structured object.`,
  { label:'synthesize', phase:'Synthesize', schema:SYNTH_SCHEMA, effort:'high' })

return { candidate_count: candidates.length, confirmed_count: confirmed.length, synthesis: synth, confirmed }
