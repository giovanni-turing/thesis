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

## Open (rest of Phase 3)

- 3.1 static-optimal: encoder×LLM worker grid under the evaluation SLA on
  the six burst episodes + a diurnal steady window → Pareto → GPU-hours.
- 3.2 reactive planner through the same windows; record scaling actions,
  compliance (evaluation SLA), GPU-hours.
