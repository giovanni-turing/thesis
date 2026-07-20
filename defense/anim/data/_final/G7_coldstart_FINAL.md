# G7 — cold start: my retraction was HALF WRONG. Corrected, and now a real result.

## Language pool: surcharge INVALID (retraction stands)
The mocker integrates the PROVISIONED worker count — active, starting-up and draining alike
(ai-dynamo/dynamo/lib/mocker/src/replay/collector.rs:44-52). Cold start is INSIDE every reported
language GPU-hour. No surcharge may be added. Evidence: the order-time staircase integral
reproduces reported GPU-h on all 52 runs within 1.00%, while a readiness-lagged counterfactual
(using each run's OWN startup time, not a hardcoded 60 s) falls 3.5-38.0% short on reactive arms.

## Encoder pool: the OPPOSITE convention — A2 does NOT share the defect
I wrongly implied the encoder-side A2 accounting was suspect. It is not. Verified two ways:
 (1) code path — the encoder controller applies cold start by DELAYING AVAILABILITY, i.e. it
     bills from READINESS;
 (2) an independent numeric signature — provisioned_ws FALLS with lead while total_from_order_ws
     is exactly INVARIANT. Under order-billing the invariance would sit in provisioned_ws instead.

## NEW RESULT: the two pools use OPPOSITE billing conventions
Encoder = readiness-billed. Language = order-billed. Any composed two-pool cost total MIXES the
two conventions and must state which is which. This is a genuine finding and belongs in the cost
section.

**CORRECTION — "previously undocumented" is FALSE and is struck.** `tex/closedloop.tex:494-501`
already carries the encoder warm-pool vs strict-re-warm distinction and its 0.62x -> 0.59x
consequence. What is actually new here is (i) the **language** convention and (ii) the
**cross-pool contrast**. Claim only those two. Where this card's novelty claim conflicts with the
thesis's own text, resolve in favour of the thesis.

## TWO POINTS THIS CARD UNDERSOLD — state them affirmatively
1. **The order-time overlay OVER-CHARGES the forecast arm.** The real strict-re-warm burst1-L165
   run costs **525,643.5 ws** against the overlay's **559,267.5 ws**. The printed ratios are
   therefore **upper bounds on the forecast arm's cost**, and the L=165 flip holds *a fortiori*
   within the strict convention — the correction can only move it further in the reported
   direction.
2. **The headline 0.62x is UNTOUCHED by this defect.** Its comparator is static C=8, which has no
   up-steps and therefore carries no readiness under-charge at all. The defect cannot propagate to
   it. Say this explicitly: an examiner who is told about a billing-convention defect will
   otherwise assume the headline inherits it.

## a2_cost_accounting.csv had NO producer script
It existed with readers but no generator anywhere in the repo — its warmup_ws was unreproducible
until this pass. The rule was reverse-engineered (sum over up-steps of delta x clipped
[t_ready-L, t_ready]) and all 40 rows are now regenerated and cross-checked.

## The burst5-L165 flip is RETRACTED — replaced by narrower but sounder evidence
Two SLA-FEASIBLE encoder cost-order flips at L=165:
  burst1     1.1444 -> 0.9698
  steady24h  1.1392 -> 0.9172
plus burst4-L165 nearly flipping (1.1411 -> 1.0116, both arms feasible, reactive p99 904.7 ms).

**CORRECTION — "SYSTEMATIC across windows" is struck.** The flips occur in **2 of 5 windows**, and
in **2 of the 3** whose comparator is SLA-feasible, and **only at L=165**. That is a narrow,
lead-specific effect, not a systematic one. Do not upgrade it.

**BLOCKED FROM THE MANUSCRIPT — and only conditionally admissible even as defence material.**
The cost side is a strict-re-warm accounting, but the feasibility that licenses it is read off
**warm-pool** simulations, and **no reactive strict-re-warm run exists anywhere**. This is the
identical defect that retracted burst5. Given that burst4's warm-pool reactive already sits at
904.7 ms and burst5's fails at 3,250 ms, the risk is not hypothetical.
**To unblock:** run the reactive arm under `--strict-rewarm` at L=165 on burst1 and steady24h and
confirm both stay under 1,000 ms. The flag and harness already exist
(verification/scripts/forecast_schedule_issuetime.py). Until then the flip is stated hedged or not
at all.

## Not writeable
The language-pool surcharge and every figure derived from it. churn_share_of_bill is partly
tautological (a monotone function of up-step count) and is L=60-specific — at L=120/300 startup
equals the lead by construction, so it scales mechanically and the arm ordering is not preserved.
