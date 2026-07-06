# Spica, Systems Catalog, Webapp, Tests & Dev Workflow

## spica (`src/spica/`) — replay-based "thorough sweep" (Profiler V2)

**Separate top-level package** (console script `spica`, `[spica]` extra: google-vizier[jax]
0.1.21 + jax 0.4.38 stack, **Python 3.10–3.12 only**). Where the legacy sweep is analytical
(perf-DB interpolation), spica **replays traffic** through Dynamo's mocker/planner bridge and
scores measured `trace_report` metrics — capturing router behavior, planner autoscaling
(gpu_hours), and closed-loop concurrency the analytical model can't. Vizier (bayesian) drives
the search.

- `config.py` — pydantic schema (`SmartSearchConfig` = one YAML: SearchSpace, Workload,
  OptimizationGoal/SLATarget, SweepConfig, Candidate). Transcribed from dynamo's
  `dgdr-profiler-smart-search-plan.md` proposal.
- `search.py::run_smart_search` — orchestrator: one Vizier study per deployment_mode branch
  (agg/disagg); backend is a searched knob. Round-based barrier loop, parallel worker
  processes (`parallel_evals`); ask/tell on main process.
- `search_space.py`/`parallel_enum.py`/`parallel_projection.py` — KV-feasible parallel-config
  enumeration (mirrors `sdk.utils.enumerate_parallel_config`; pp pinned 1; MoE
  `dp·tp==moe_tp·moe_ep`) + deterministic Vizier-suggestion projection.
- `kv_estimate.py` — feasibility via AIC `estimate_kv_cache` (**native only** — no perf DB →
  `NoPerfDatabase`; naive fallback intentionally disabled). `kv_load.py` — candidate-relative
  load → concrete closed-loop concurrency.
- `deploy.py` — flat config → `DeploymentPlan` (per-role `MockEngineArgs`, optional
  `PlannerConfig`, router config). **Planner policy keys the replay path**: both scaling flags
  off → static `run_trace_replay`; else planner-bridge replay (Rust calls back into the Python
  planner per `PlannerTick`).
- `evaluator.py::ReplayEvaluator` — mooncake-trace JSONL or synthetic (isl/osl/concurrency)
  replay; goodput SLA baked into the report. `score.py` — `goodput_per_gpu`/
  `throughput_per_gpu` ÷ time-averaged GPUs; ties → fewer GPUs; Pareto goal → non-dominated set.
- `planner.py`/`load_predictor_sweep.py` — planner-preset decoding + per-interval
  load-predictor grid (reuses real Dynamo predictors).

**CLI bridge** (`cli/spica/helper.py`, 1869 lines; re-export `cli_adapter.py`):
`--thorough-sweep` in default mode → `run_spica_thorough_default`. Guards: no hetero
`--decode-system`; ignores `--backend-version`/`--database-mode`/`--request-latency`/wideep
flags; hard-requires py3.10–3.12 + `[spica]`. Without `--thorough-config` it derives a
**synthetic workload** from CLI args (concurrency = total_gpus×128, ~1000 requests, goal
goodput_per_gpu with ttft/itl SLA, 3 rounds × 16 parallel evals; env overrides
`AIC_SPICA_THOROUGH_*`). Results feed the standard `log_final_summary`/`report_and_save`;
generated DGDs use `preserve_engine_limits=True` so rules don't resize replay-validated
candidates. Trace generator: `tools/spica/gen_sine_trace.py`.

## webapp (`src/aiconfigurator/webapp/`)

Gradio UI (`[webapp]` extra, gradio 6.8.0). Launch via `python -m aiconfigurator.webapp.main
--server-port 7860` (NOT a subcommand of the main CLI). Tabs in `components/` (agg, agg_pareto,
disagg_pareto, disagg_pd_ratio, pareto_comparison, static, support_matrix, readme) + large
`profiling/` subsystem (JS renderers, core orchestrator). Events in `events/`
(`event_fn.py` — still calls **legacy** `agg_pareto`/`disagg_pareto`). `gradio_patches.py`
must import before any component.

## systems (`src/aiconfigurator/systems/`)

- Per-GPU YAMLs: a30, a100_pcie/sxm, b60, b200_sxm, b300_sxm, gb200, gb300, h100_pcie/sxm,
  h200_sxm, l4, l40s, rtx_pro_6000_server. Contents: `gpu:` (mem_bw+empirical factors,
  mem_capacity, bf16/int8/fp8 tc_flops, power, sm_version), `node:` (gpus, inter/intra bw),
  `misc:` (nccl_mem map, other_mem, nccl_version).
- `data/<gpu>/<framework>/<version>/*.parquet` (frameworks incl. `nccl`). Sentinels:
  `SHARED_LAYER_REUSE.txt` (version reuses another's data), `INCOMPLETE.txt`. **git-LFS**:
  run `git lfs pull` after clone.
- `op_kernel_source_manifest.yaml` (maintained by daily workflow), `silicon_sample.csv`
  (accuracy-regression baseline), `support_matrix/*.csv` + `index.json` (model×backend×version
  ×mode PASS matrix; columns HuggingFaceID/Architecture/System/Backend/Version/Mode/Status).

## model_configs (`src/aiconfigurator/model_configs/`)

~70 cached HF `config.json` files (`<org>--<model>_config.json`, + `_hf_quant_config.json` for
FP8/NVFP4 variants) → offline model sizing without HF network. Resolved via pkg_resources;
`AICONFIGURATOR_MODEL_CONFIGS_PATH` exports the path to Rust.

## tests

- `tests/unit/` (cli, generator, sdk/{database,models,backends,picking,predict,sweep,task_v2,
  operations}, collector, support_matrix, webapp, tools), `tests/integration/` (perf-DB-backed),
  `tests/e2e/` (subprocess CLI, incl. thorough-sweep real + api-equivalence),
  `tests/golden/generator/` (release contract snapshots), `tests/spica/` (19 files + mooncake
  fixture). Parity: `tests/unit/support_matrix/test_engine_step_parity.py`,
  `tests/unit/sdk/sweep/test_rate_match_parity.py`; Rust parity under
  `rust/aiconfigurator-core/parity_tests/`.
- `pytest.ini`: strict markers, timeout 120. Markers: `unit`, `integration`, `e2e`, `sweep`,
  `build`, `support_matrix`. CI PR subset: `pytest -m "unit or build"`.

## Dev workflow

- Setup (DEVELOPMENT.md): git-lfs → clone → `git lfs pull` → venv →
  `pip install -e ".[dev]"` (maturin builds the Rust core automatically) →
  `pre-commit install`. Lint: **ruff** (check + format, line-length 120, py310 target).
  DCO sign-off required (`git commit -s`); conventional PR titles.
- Build: maturin backend; extras `dev`/`webapp`/`service`/`spica`. Docker: multi-stage uv-based
  (`docker/Dockerfile`).
- **CI on PR**: `build-test.yml` (cargo-deny; unit+e2e suites `-m "unit or build"`; dedicated
  **Spica thorough e2e** job building Dynamo replay bindings with maturin), `lint.yml`
  (ruff + ESLint for webapp JS), copyright/PR-title checks, `create-charts.yml` (PRs touching
  systems/), `perf-parquet-diff.yml` (PRs touching perf data → diff comment),
  `accuracy-regression-testing.yml` (vs silicon_sample.csv). Non-PR: support-matrix
  main/release/daily, op-kernel-source-manifest daily.

## tools/

`spica/` (sine-trace gen, load-predictor sweep runner), `support_matrix/` (generate/compare +
`scan_rust_parity.py`), `perf_database/` (parquet_diff/textconv — git diff driver),
`accuracy_regression_testing/`, `generator_validator/` (validates generated CLI args against
real backend argparsers), `sanity_check/` (create_charts), `simple_sdk_demo/`,
`verify_release_wheels.py`, `run_sweep_new.py`.

## .claude/rules inventory

All generator-specific: umbrella `generator-development.md` + `generator/{rule_authoring,
config_schema, template_authoring, render_path_policy, new_backend_version, guard_rails,
debugging, testing, cross_module_impact}.md`. No non-generator rules exist.
