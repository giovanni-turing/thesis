# Defects found IN THE THESIS TEXT (not in the new measurements)

## 1. tex/twopool.tex:76-77 — the "882 ms" is a WHEEL number, and the surrounding claim is false
tex/twopool.tex:66-72 states the wheel instrumentation artifact inflated "the extreme tail only
(identical p99)". Measured against the source build:
  s=1  306.73 (wheel) vs 307.36 (source)  = +0.2%   <- claim holds here
  s=4  882.08 (wheel) vs 782.68 (source)  = -11.3%  <- claim FAILS here
The 882 ms quoted at :76-77 is therefore a wheel-runtime number sitting in the thesis under a
sentence asserting p99 agreement. Either requote from the source build, or restrict the
"identical p99" claim to s=1.

The real pattern is a function of DISTANCE FROM THE KNEE, not of arm or MoE-ness: 8B-TP1 agrees
to +0.2% at s=1 and -0.3% at s=3 (its first violating point) but diverges to +22.1% TTFT /
-61.1% ITL at s=16. This is a stronger and more useful statement than the arm-specific one.

## 2. simulation/results/sweeps/reports/ is RUNTIME-MIXED
llm_head2k_aic_s3.report.json carries max_ttft 4543.39 ms — identical to the source build — and
was written 2026-07-08 with a different report schema (3057 B), while s=1/2/4/16 were written
2026-07-06..07 with the older schema. The "ledgered wheel sweep" is not a homogeneous set. Any
cross-runtime comparison must exclude s=3 or state the mixture.

## 3. tex/intro.tex:504 and :148 — "offered-work upper bound" is not supportable as stated
See A16_decode_CORRECTED.md. The decode stamp is NOT a pointwise upper bound; at 15 s it
understates 58% of bins. It IS strongly conservative on the bins an observer can actually
identify (arrival-selected busiest 1%: +54.4%, reproducing within 1.2 pp on all three arms).
Reword to the observable-selection statement.
