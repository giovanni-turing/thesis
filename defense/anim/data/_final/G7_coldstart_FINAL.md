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
Encoder = readiness-billed. Language = order-billed. Previously undocumented. Any composed
two-pool cost total MIXES the two conventions and must state which is which. This is a genuine
finding and belongs in the cost section.

## a2_cost_accounting.csv had NO producer script
It existed with readers but no generator anywhere in the repo — its warmup_ws was unreproducible
until this pass. The rule was reverse-engineered (sum over up-steps of delta x clipped
[t_ready-L, t_ready]) and all 40 rows are now regenerated and cross-checked.

## The burst5-L165 flip is RETRACTED — but replaced by BETTER evidence
Two previously unreported, SLA-FEASIBLE encoder cost-order flips at L=165:
  burst1     1.1444 -> 0.9698
  steady24h  1.1392 -> 0.9172
plus burst4-L165 nearly flipping (1.1411 -> 1.0116, both arms feasible, reactive p99 904.7 ms).
The original single-window claim was weaker than the truth: the effect is SYSTEMATIC across
windows at the cold-pool lead, not a one-window artifact.

## Not writeable
The language-pool surcharge and every figure derived from it. churn_share_of_bill is partly
tautological (a monotone function of up-step count) and is L=60-specific — at L=120/300 startup
equals the lead by construction, so it scales mechanically and the arm ordering is not preserved.
