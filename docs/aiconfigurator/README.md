# AIConfigurator — Agent Navigation Docs

Deep architecture reference for `/home/gio/tese/ai-dynamo/aiconfigurator` (upstream mirror on
`main`, v0.10.0). Produced 2026-07-05 by whole-tree exploration. Complements the repo's own
`AGENTS.md`, `.claude/rules/`, `.agents/skills/`, and `docs/`.

## Documents

| Doc | Covers |
| --- | --- |
| [01-sdk-perf-model.md](01-sdk-perf-model.md) | `sdk/` — perf_database + interpolation, models (op graphs), operations (cost primitives), backends (scheduling/memory), memory.py, task_v2/config |
| [02-search-cli.md](02-search-cli.md) | `sdk/sweep.py`, `picking.py`, `pareto_analysis.py`, `cli/` — modes, flags, exp YAML, reports, api.py |
| [03-generator.md](03-generator.md) | `generator/` — flow/IR, Jinja-vs-typed-builder policy, config sources of truth, rule DSL, guard rails, deployment targets |
| [04-collector.md](04-collector.md) | `collector/` — orchestrator, case planning, registries, three-identities contract, output format |
| [05-rust-core.md](05-rust-core.md) | `rust/aiconfigurator-core` — EngineSpec wire, Engine runtime, operators, FPM, PyO3 surface, parity tests, Dynamo pin |
| [06-spica-systems-dev.md](06-spica-systems-dev.md) | `src/spica/` (thorough sweep), webapp, systems catalog, model_configs, tests, CI, tools |

## The big picture

AIConfigurator finds deployment configs for **disaggregated LLM serving**: given model + GPU count
+ GPU type, it decides #prefill/#decode workers and parallelism (TP/PP/DP/EP) to maximize
throughput under TTFT/TPOT SLAs, then **emits ready-to-deploy artifacts** for Dynamo or llm-d.

```
                       systems/data/<gpu>/<backend>/<ver>/*.parquet   ← collector/ (offline, GPU node)
                                        │
   HF config ──> sdk/models (op graphs) ─┤
                                        ▼
        sdk/perf_database (interp) → sdk/operations → sdk/backends (scheduling+memory)
                                        │        └── rust/aiconfigurator-core (GIL-free hot loop)
                                        ▼
              sdk/sweep.py  (sweep_agg / sweep_disagg + rate matching, SLA filter)
                                        ▼
              picking.py (best under SLA) / pareto_analysis (frontier for plots)
                                        ▼
              generator/  →  k8s DGD (typed builder) + cli_args/run.sh/engine yaml (Jinja)
```

Pipeline stages an agent will touch: **CLI/api → task_v2.Task → sweep → picking →
module_bridge → generator → artifacts**. The alternative to the analytical sweep is **spica**
(`--thorough-sweep`): replay-based search that actually simulates deployments through Dynamo's
mocker/planner bridge and scores measured goodput.

## Key facts an agent should know up front

1. **Two parallel search stacks coexist.** New: `task_v2.Task → sweep.py → picking.py`
   (CLI/api path). Legacy: `pareto_analysis.agg_pareto/disagg_pareto → InferenceSession`
   (**still used by the webapp**). Parity locked by `tests/unit/sdk/sweep/`. Sweep output is the
   *SLA-feasible candidate set*, NOT a Pareto frontier (frontier is plotting-only).
2. **Guarded edit zones.** Generator work requires reading `.claude/rules/generator-development.md`
   + `generator/*` first (inline `# Guard:` comments beat guard_rails.md). Collector op/case work
   requires `.agents/skills/aic-collector-op-development/SKILL.md` (three-identities contract).
3. **"Python builds, Rust executes."** Python `compile_engine` walks the model once → JSON
   EngineSpec → bincode → Rust `Engine` executes per-step latency GIL-free. Enabled via
   `AICONFIGURATOR_ENGINE_STEP_BACKEND=rust`; parity enforced < 1% rtol
   (`rust/aiconfigurator-core/parity_tests/`). Dynamo pins this crate by git rev
   (`aic-forward-pass` feature).
4. **Cross-backend parity is the top bug pattern** (e.g. PR #579: MoE-TP rule missing from
   SGLang) — when editing one backend's rule/template/mapping, check the other two.
5. **The IR is a v2 seam, not live.** `pipeline.py` builds `DeploymentIR` but artifacts still
   render from the legacy params dict. Don't assume the IR drives output.
6. **Perf data is git-LFS parquet** under `src/aiconfigurator/systems/data/`; `git lfs pull`
   required; Rust errors explicitly on unresolved LFS pointers. Lazy per-op loading — the
   database opens zero files at init.
7. **spica is a separate top-level package** (`src/spica/`, own console script, `[spica]` extra,
   Python 3.10–3.12 only due to Vizier/JAX).
8. Dedicated skills: `aic-auto-collect` (long GPU collection runs), `aic-collector-op-development`
   (both vendored at workspace `.claude/skills/` and in-repo `.agents/skills/`).

## Cross-project links

- **Dynamo** consumes AIC three ways: `dynamo._internal.aic` (AicSession per-step predictors +
  `estimate_num_gpu_blocks` for mocker KV capacity), the Rust `aiconfigurator-core` git pin
  (`aic-forward-pass`, GIL-free mocker/planner perf model), and the profiler
  (`dynamo.profiler` rapid mode = AIC simulation; generator emits `DynamoGraphDeployment` CRDs).
- **Paper**: arxiv 2601.06288. Interactive map: ai-dynamo.github.io/aiconfigurator/universe/.
