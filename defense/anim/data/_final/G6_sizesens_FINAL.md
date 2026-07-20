# G6 — image-size sensitivity x handoff fabric — AUDITED, ROUND 2

Closes: tex/intro.tex Scope — "the trace records image counts, not sizes, so the encoder pool
assumes a uniform 448^2 image." Sizes are unmeasurable from this trace: every distribution is
ASSUMED and labelled so. What is measured is the SENSITIVITY of the verdict to that assumption,
jointly with the handoff fabric.

## Verified sound (independent recomputation)
- ALL card numbers reproduce exactly from raw shipped stats (u448@25G p99 = 588.370 = the ledger
  anchor; u672 fc 1397.399/938.734; u672 static 3488.959/3414.897; u896 fc 3468.952/3021.392).
- THE REPRICING IS NOT AN INVENTED SCALING LAW. g6_sizemix.py:234-260 calls AIC's OWN ops against
  the real rtx_5090/vllm-0.22.0 perf DB with genuine Qwen3-VL ViT geometry (pre-merge patches
  (px//16)^2, post-merge tokens). The canonical s=784 (448^2) anchor is densely COLLECTED at
  b=1..64, not interpolated.
- FABRIC ARITHMETIC EXACTLY CORRECT: workload/trace_to_two_pool.py:478-482,
  n_bytes = post_merge_tokens x 4096 x 2; transfer_ms = 0.2 + n_bytes/(gbps*1e9/8)*1e3 (decimal
  line rate, correctly). Floor decomposition reproduces to <5e-5 on every cell checked.
- 448@25G = 588.37 FOR THE RIGHT STRUCTURAL REASON, not two offsetting errors:
  p99 = f(64) 316.369 + handoff 272.001, with queueing exactly 0.

## CORRECTION 1 — "456 cells" is a FILE COUNT
448 GRADED cells (272 pool + 88 recover + 88 capsweep). The 456 *.g6mix.json files include 8
ORPHANS with no fabric suffix, left from a superseded pre-fabric-sweep run. Quote 448.

## CORRECTION 2 — "one step below the breakpoint" is a LADDER ARTIFACT
Queueing is 0.0 at every rung, so the verdict is CLOSED-FORM, not a discovered rung:
  floor(px) = f_px(64) + 272.001 x (px//32)^2 / 196
The breakpoint is a continuous quantity that the ladder {224,336,448,672,896} merely brackets.
At 100 Gbps the crossing sits at ~690-705 px. State the crossing, not the rung.
(No evidence of results-fitting: the ladder is a standard ViT resolution set. But it was chosen
before the crossing was known, so it brackets rather than locates.)

## CORRECTION 3 — the 672 "fabric rescue" is MARGINAL, and it is a SERIALIZATION result
u672@100G passes with only **6.1% margin** (938.734 vs the 1000 ms bound). Do not write it as a
clean rescue.
More importantly: "at 672 the fabric decides" is NOT a line-rate result — it is a
SINGLE-STREAM-SERIALIZATION result. The p99 request (529 images) has its COMPUTE spread across
workers while its HANDOFF is modelled as one serialized stream. That single-stream assumption
contradicts the simulator's own dispatch model for the very request that sets the p99. The
sensitivity is therefore to the handoff CONCURRENCY assumption at least as much as to bandwidth.

## CORRECTION 4 — one genuine extrapolation, mislabelled in the artifact
At s=3136 (896^2) the collected batch axis stops at b=32; AIC densifies via
interpolation.extrapolate_data_grid (inner_only=False). The 896 cells are therefore extrapolated,
and the driver's labelling is wrong in both directions. The 448 and 672 cells are inside the
collected box; only 896 is affected.

## Results (numbers unchanged, framing corrected) — **BURST3 ONLY; see Correction 5**
Encoder-delay p99, burst3, forecast p90/rho15/L30 vs static C8:
| image | fc @25G | fc @100G | static C8 @25G | static C8 @100G |
|---|---:|---:|---:|---:|
| 224 | 142.8 PASS | 91.8 PASS | 165.6 PASS | 114.6 PASS |
| 336 | 308.8 PASS | 204.8 PASS | 356.9 PASS | 252.9 PASS |
| 448 (assumed) | 588.4 PASS | 384.5 PASS | 716.4 PASS | 559.5 PASS |
| 672 | 1397.4 FAIL | 938.7 PASS (6.1% margin) | 3489.0 FAIL | 3414.9 FAIL |
| 896 (extrapolated) | 3469.0 FAIL | 3021.4 FAIL | 25163.1 FAIL | 25114.1 FAIL |

## CORRECTION 5 (NEW) — WINDOW SCOPE: every cell in the table above is burst3
The size ladder was graded on burst3 and the verdict is **not window-invariant**. Re-derived from
g6_runs/*.stats.json, encoder-delay p99 at 672 px, forecast arm (fc_L30):

| window | fc @25G | fc @100G |
|---|---:|---:|
| burst3 | 1397.4 FAIL | 938.7 PASS (6.1% margin) |
| burst4 | 1397.4 FAIL | 938.7 PASS |
| burst5 | 1397.4 FAIL | 938.7 PASS |
| **steady24h** | **1972.5 FAIL** | **1927.5 FAIL** |

At the 24-hour window the forecast arm at 672 px **FAILS on BOTH fabrics** — the "fabric rescue"
does not exist there, and the 100 Gbps link buys only 2.3%. The same holds at 896 px (steady24h
5716.3 @25G / 5632.5 @100G, both FAIL).
=> **Never state the 672 px fabric crossing without naming its window.** The crossing near
690-705 px is a burst3-and-siblings result; on the sustained 24 h window the assumed resolution
sits much closer to the boundary than the burst cells suggest.

## Structural point that SURVIVES and is the most useful finding
provisioned_worker_s is INVARIANT across image size (32,228.0 for every burst3 cell, both
fabrics). The p90 schedule is driven by image COUNT and is blind to SIZE, so a size increase
arrives as pure service-time inflation with NO provisioning response. This is why size growth
breaks the verdict rather than being absorbed the way the 1.4-1.6x engine-cost gap was
(app:engine-sensitivity) — size is not the same kind of perturbation as cost-per-forward.

## What may be written
"Image sizes are not recorded, so the uniform-448 assumption can only be stress-tested. Repricing
the encoder through the collected RTX 5090 operator database at other resolutions, the verdict
holds at 448 and below on both modelled fabrics; the closed-form service floor
f(64) + 272 ms x (px/32)^2/196 places the crossing near 690-705 px on a 100 Gbps link, so the
assumed resolution sits just below it. Because the p90 schedule is driven by image count it is
blind to size, and a size increase produces no provisioning response at all — unlike the
engine-cost gap, which the p90 headroom absorbs with no added workers. The 25-versus-100 Gbps
difference at 672 px reflects the single-stream handoff assumption as much as line rate, and it is
a burst-window result: on the sustained 24-hour window the 672 px configuration misses the bound
on both fabrics."
