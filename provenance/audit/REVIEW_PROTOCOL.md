# Verification protocol — amended after the reviewer escapes (2026-07-21)

Two external reviewer rounds found errors that survived four internal
verification passes (DB claim-check, claim-by-claim reverify, 6-lens deep
verify, R3 DB fact-check). Root-cause analysis and the rules that close each
class. These rules are BINDING for every future verification pass on this
manuscript.

## Why each class escaped

| Escape | Class | Why every pass missed it |
|---|---|---|
| 0.96x (true 0.96502 → 0.965/0.97) | **Transcription vs derivation** | All passes verified printed == recorded (ledger also said 0.96x). No pass recomputed the ratio from raw operands. The error was upstream, in the first rounding, and faithfully propagated. The gate then PROTECTED the wrong string. |
| 3,092/3,089 of 3,093 undisclosed | **Population/denominator blindness** | Passes verified the scheduled count (3,093) against the artifact. No pass asked "over WHICH N is this percentile computed?" |
| "billed at forecast-issue time" | **Term conflation** | Actuation vs billing both appear in the chapter; each clause individually 'matches source material'. No pass validated verbs against the defined convention table. |
| RQ4 cost/compliance merge | **Scope attachment** | Each claim true in isolation (compliance: per-episode; saving: week-scale). No pass parsed what a sentence's modifier ATTACHES to. |

## Rules (mechanized where possible)

R-A **Recompute, don't transcribe.** Every derived headline (ratio, %, "N of
    M", multiple) must be recomputed from raw operands at gate time.
    Mechanized: verify_all.sh "derived-value recomputation" section reads the
    raw artifacts / operand pairs and re-rounds; a printed value that is not
    the correct rounding of the recomputation FAILS the gate. Protected
    values now carry (numerator, denominator, precision), never a bare string.

R-B **Every tail names its population.** Any percentile/tail/verdict must
    state N and, where N != scheduled/total, the excluded count and cause.
    Mechanized where counts are in artifacts (live-run counts checked in the
    gate); otherwise a review-pass checklist item.

R-C **Verb-convention table.** Billing verbs: encoder bills FROM READINESS;
    warm-up is billed-from-order, reported separately; schedules are ACTUATED
    at issue time; language pool bills from ORDER. Any sentence pairing a
    cost with a verb must match this table. Gate greps the known-bad
    pairings ("billed at forecast-issue", "billed at issue time").

R-D **Scope-attachment audit.** For every headline sentence: list each
    modifier (cost, span, population, lead) and verify each attaches to a
    clause for which it is separately true. Cannot be fully mechanized —
    MANDATORY explicit lens in every future review pass (an "attachment
    auditor" reading ONLY headline sentences, asking "what does each number
    modify?"). Known-fixed instances are gate-regression-checked.

R-E **Protection = derivation, not string.** A protected value that is later
    shown mis-derived gets AMENDED with operands recorded (ADJUDICATION
    addendum), never defended by its protection. The protection then moves to
    the corrected value + its formula.

## Standing verdict-sentence checklist (apply to abstract, RQ answers,
chapter summaries, thesis quote — the promotion sites)

1. Is every number here the correct rounding of a recomputation? (R-A)
2. Does every tail/percentile name its N? (R-B)
3. Does every cost verb match the convention table? (R-C)
4. Does every modifier attach to a clause it is true of? (R-D)
5. Is every "every/all" population named? (from shortening-report round)
