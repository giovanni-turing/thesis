# Headline cascade — corrected-number spec (B5 resolution)

**Decision (user):** report ONLY the AIC-consistent number; retire 0.27–0.31×.
**Root cause:** burst5's C=16 was an endpoint-divergence artifact; honest AIC
deployable static = **C=8** (burst5 is p99-knee-limited at 8, stable at every
C≥8: negative backlog slope, constant tiled backlog, week-scale C=8 feasible at
p99 644 ms). Silicon denominator is larger (burst2's real ~2× knee) → silicon a
future-work note, not the headline.

## Number map (apply everywhere, verified)
| Quantity | OLD | NEW |
|---|---|---|
| Deployable static fleet | C=16 | **C=8** |
| Static worker-seconds (5.60-day span) | 7.74M | **3.87M** |
| Static aggregate encoder p99 | 565 ms | **644 ms** (week C=8 run) |
| Headline ratio (ρ15, L30–L300) | 0.27–0.31× | **0.55–0.61×** (0.546 / 0.614) |
| ρ-frontier ρ10→ρ25 | 0.44× → 0.18× | **0.88× → 0.36×** |
| ρ∈{10,15} per-episode-clean band | 0.44–0.31× | **0.88–0.58×** |
| "prices 0.27–0.44× static" | 0.27–0.44× | **0.55–0.88×** |
| burst5 C* (tab:base-grid) | 16 (21.6 GPU-h) | **8 (10.8 GPU-h)** |
| Overprovisioning of calm day | 8×/2× | **4×/2×** (C=8 vs C=2) |
| "encoder requirement swings 2→16" | 2→16 | **2→8** |
| burst5 "divergence-limited (16 workers)" (aic) | — | **p99-knee-limited at 8; the divergence flag that forced 16 is an endpoint artifact (backlog slope ~0, tiled backlog constant)** |

## Sites (grep-verified)
- 0.27–0.31× (11): tese:59, tese:97(resumo 0,55–0,61), related:348, conclusion:65,
  intro:261, intro:477, closedloop:337, :366, :440, :443, :461.
- frontier: closedloop:136 (0.27–0.44→0.55–0.88), :357 (0.44→0.88), :358 (0.18→0.36),
  :365 (0.44–0.31→0.88–0.58).
- C=16 / 7.74M / 565 / deployable static: baselines (tab:base-grid burst5 row, the
  three-structural-facts para, my B1 note), tab:cl-aggregate (static row), closedloop
  headline+silicon para, aiconfigurator burst5 para.
- 8×/2×: wherever "overprovision" appears (baselines, intro, conclusion, abstract).
- e2e p99 (B6, separate decision): report ~1295 ms true ingress→first-token where
  twopool:203 says "end-to-end tails reported directly"; ~2× marginals, r=0.52
  correlated tails, within the ~2 s union budget.

## Framing note to carry
The corrected story: forecast-driven per-pool provisioning costs **~0.55–0.61×** an
honestly-sized static fleet (C=8) on the covered week — still ~2× cheaper than
static, on the bursts that defeat reactive control — with a ρ-frontier from 0.88×
(ρ10) to 0.36× (ρ25). The previously-reported 0.27–0.31× rested on a C=16 denominator
produced by an endpoint-divergence artifact. On measured silicon the deployable fleet
is larger (bound by burst2's genuine batching knee, not burst5), so a fully
silicon-costed loop would land between these; that is future work.
