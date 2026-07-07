# Phase 3 — Baselines: SLA definitions + re-derived operating points

Companion to `thesis-roadmap.md` (Phase 3). This file opens with the SLA
decision every downstream experiment is graded on; baseline results (3.1
static-optimal, 3.2 reactive planner) accumulate below as they land.

---

## The thesis SLA (decided 2026-07-07)

Two levels, deliberately distinct:

**Evaluation SLA (all policies are graded on this, per pool, per window):**

| Pool | Bound | Rationale |
|---|---|---|
| Language | TTFT p99 < 1,000 ms AND ITL p99 < 100 ms | interactive grade: first token within 1 s and ≥10 tok/s at the 99th percentile; tail-based because the thesis's failure mode IS burst-time tails |
| Vision | encoder delay (queue+service+handoff) p99 < 1,000 ms | matches the language TTFT budget so composed multimodal p99 TTFT stays ≲2 s |

**Policy configuration (reactive baseline only):** Dynamo's SLA Planner
regulates on *window-mean* TTFT/ITL against its shipped defaults
(`ttft_ms=500`, `itl_ms=50` — `planner/config/defaults.py`; the offline
replay adapter feeds `avg_ttft_ms`/`avg_itl_ms`). The planner keeps those
native defaults unmodified — they are that policy's control law, not the
SLA. Evaluation-vs-control mismatch (means met, p99 violated) is a
*finding about reactive control*, not a grading inconsistency. The 2×
ratio between the evaluation bounds and the planner means is the
conventional mean-target/tail-ceiling pairing.

## Knees re-derived under the thesis SLA (existing sweep points, no new sims)

`sweep_load.py` now encodes the SLA as its defaults (knee = largest swept s
meeting BOTH language bounds; one new point, llm/head2k/aic/s2, tightens the
calibrated bracket). Figure regenerated (`results/sweeps/knees.png`).

| Curve | knee (was, at placeholder 2 s TTFT-only) | offered at knee | binding bound |
|---|---|---|---|
| llm · head2k · poly | **s=2** (was s=8) | 5.5 req/s | **ITL** (s=4: TTFT 473 ✓, ITL 154 ✗) |
| llm · head2k · aic | **s=2** (was s=4) | 5.5 req/s | **ITL** (s=4: TTFT 882 ✓, ITL 211 ✗) |
| llm · burst1 · poly | **s=1** (was s=2) | 2.2 req/s | both at s=2 (TTFT 1,458, ITL 178) |
| vision · head2k | s=32 censored (unchanged) | ≥256 img/s | — |
| vision · burst1 | none — over at s=1 (unchanged) | 116 img/s | — |

**Two consequences:**

1. **The language pool is decode-bound, not TTFT-bound**, under an
   interactive SLA: at its knee's successor the TTFT budget still has 2×
   headroom while ITL p99 has crossed. This holds for both timing models
   and matches the 235B expectation — the flagship (TP8) has ITL p99
   87.7 ms already at s=1 (knee s=1, 2.8 req/s; 8B knee s=2): decoder
   size halves the language knee while the vision pool is family-invariant.
2. **The decoupling sharpens to ≥16×** on the steady head (vision ≥s=32 vs
   llm s=2, both timings), and the burst reversal is now exact: the
   language pool meets the SLA at the episode's own rate (knee s=1) while
   the vision pool violates it at that same rate (p99 5.4 s at 29% util).

## Planner-config mapping for 3.2 (when it runs)

`dynamo.replay --planner-config` (advisory, `mode: agg`) with
`ttft_ms: 500, itl_ms: 50` (defaults, stated explicitly in the config for
the record); source-built runtime (`REPLAY_PY=.../dynamo/.venv/bin/python
AIC_VER=0.19.0`). Adjustment-interval and scaling bounds to be fixed when
3.2 runs.

## Encoder chunk dispatch: parallel (decided 2026-07-07, user-approved)

The 3.1 smoke test exposed a structural infeasibility: under the Phase-2
dispatch policy (an oversized request's ≤64-image chunks run sequentially
on ONE worker) large frames-class requests carry an intrinsic multi-second
service floor — burst3's delay p99 plateaus at 2,877 ms from C=4 through
C=32 (utilization ≤11%) — so no static OR dynamic worker count can meet
the evaluation SLA on frames-heavy windows. Resolution: **parallel chunk
dispatch** — chunks enter the FIFO as independent units and fan out across
free workers. Physically grounded (images are independent in the encoder;
the batching law prices any forward at its image total). Implemented in
`workload/trace_to_two_pool.py` (new default; `--sequential-chunks`
restores the Phase-2 policy, regression-verified to the millisecond).

Re-derived Phase-2 results under the new policy: burst1 s=1 C=2 delay
p99 5,368→4,957 ms at 29% util (headline burst reversal UNCHANGED);
head2k knee still censored at s=32 (794 ms); LLM curves untouched
(isolation trace). Chapter 6 + intro updated; burst3 becomes feasible at
C=8 (p99 714 ms) — static-optimal is now well-defined everywhere.
Mechanism shift worth quoting: every forward is now ≤315 ms, and the
burst pathology is queue depth (789 s above 1,000 queued images, peak
4,637), not multi-second forwards.

## 3.1 static-optimal — tooling ready, grid running

- `simulation/derive_windows.py` → `simulation/windows.json`: six burst
  episodes ±10 min (burst1 reproduces the Phase-2 window EXACTLY —
  anchor-asserted) + `steady24h` (calmest full UTC day, 2024-10-20:
  1.02 req/s, 5.4 img/s mean, 88,260 requests).
- `simulation/sweep_grid.py`: per window, two monotone 1-D first-feasible
  searches (`C*` for vision via converter runs, `N*` for LLM via replay on
  the `C*`-shifted trace, AIC timing) + integer bisection + corner
  cross-check (`N*` must stay feasible at the next C rung). GPU-hours per hardware
  class, never summed. Results → `simulation/results/grid/`.

## Open (rest of Phase 3)

- 3.1: grid completing on all 7 windows → Pareto/GPU-hours table + the
  all-windows static config and its steady24h overprovisioning factor.
- 3.2 reactive planner through the same windows; record scaling actions,
  compliance (evaluation SLA), GPU-hours.
