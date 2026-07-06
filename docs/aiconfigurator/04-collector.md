# Collector (`collector/`) — perf-database production

**⚠ Guarded zone.** `AGENTS.md` requires reading
`.agents/skills/aic-collector-op-development/SKILL.md` before touching `collector/cases/**`,
`case_generator.py`, `model_cases.py`, `collect.py`, `registry_types.py`,
`framework_manifest.yaml`, `*/registry.py`, `*/collect_*.py`, `wideep/**`.

## Purpose

Offline kernel-microbenchmark harness producing the perf tables the SDK queries. Runs on a GPU
node per `(system, backend, framework_version)` with locked clocks (`nvidia-smi -pm 1`, `-ac`).
Users normally consume shipped data. Output → `src/aiconfigurator/systems/data/<system>/
<backend>/<version>/*_perf.parquet` (comm under `<system>/nccl/<ver>/`). Sparse-tolerant.
Full trtllm pass ≈ 30 GPU-hours.

## collect.py (orchestrator)

- **Model-centric v2 mode** (any of `--model-path`, `--model-architecture`, `--model-cases`,
  `--model-cases-full`): `build_collection_case_plan(...)` → per-op plan; sets
  `COLLECTOR_MODEL_PATH` env for legacy getters. `--plan-only` prints the plan JSON and exits.
  `--gpu b200_sxm` resolves SM from the system YAML; `--sm` overrides.
- **Direct registry mode** (no model flags): every registered op with default cases.
- Dispatch `collect_{trtllm,vllm,sglang}` → backend `REGISTRY` (+ WideEP registry appended only
  when a requested op is a WideEP op) → `version_resolver.build_collections()` → `collect_ops()`
  (validates each module's `__compat__` against runtime version; filters cases through
  `filter_test_cases_with_report`; `--shuffle` seed 42; `--limit`).
- **Resume**: `ResumeCheckpoint` per (backend, module) under `--checkpoint-dir`, tracking
  done/failed/expected_failed ("done" = attempted). `--resume` skips; `--resume-retry-failed`
  re-queues. `expected_failed` = matches an SM `known_exceptions` record.
- Other flags: `--smoke` (4 random cases/op), `--measure_power` (NVML → power columns),
  `--profile`, `--keep-csv` (skip parquet finalize). Finalization converts only files touched
  by this run (mtime snapshot) CSV→parquet.

## Case planning (model_cases.py) + expansion (case_generator.py)

Three YAML layers merge into a `CollectionCasePlan` (per-op `OpCasePlan` with
include/exclude/expected_failures `CaseSelector`s + drop):
1. `cases/base_ops/<op>.yaml` — reusable sweep policy (token_counts, TP/EP, distributions).
   `include_base: true` activates only the universal set (dense attention + GEMM).
2. `cases/models/<architecture>_cases.yaml` — model dims; selectors narrow base recipes
   (or add, in `--model-cases-full` mode); `framework_specific_base_ops`,
   artifact-keyed `model_specific_base_ops`.
3. `cases/sm_exceptions/sm<ver>_exceptions.yaml` — per-SM known failures/drops.

`case_generator.py` (2102 lines) expands merged YAML → concrete per-framework cases. Design
contract: **independent workload axes stay lists; correlated structural axes stay in one
profile** (attention: heads/kv-heads/head_dim/window/TP; MoE: experts/topk/hidden/inter/TP/EP/
quant) — avoids accidental Cartesian products. GEMM shorthand: `token_counts`=M,
`input_feature_sizes`=K, `output_feature_sizes`=N. MoE quant modes carry
`min_sm`/`requires_runtime_feature`/`allowed_model_paths` gates (fp8_block min_sm 90,
nvfp4/mxfp4 min_sm 100).

## Registries

`registry_types.py`: `PerfFile` enum (canonical filenames), `OpEntry(op, get_func, run_func,
perf_filename, module | versions: [VersionRoute(min_version, module)])`. Per-backend
`{trtllm,vllm,sglang}/registry.py` + `wideep/{sglang,trtllm}/registry.py`.
`version_resolver.py`: `resolve_module` picks first route with min_version ≤ runtime;
`__compat__` strings (`"trtllm>=1.1.0"`) validated at run time; dev wheels `0.0.0.dev*` → route
to newest. Versioned forks named `collect_<op>_v1.py`/`_v2.py` (real range in `__compat__`).

**Collect script shape** (`<backend>/collect_<op>.py`): `__compat__` → `get_<op>_test_cases()`
→ `run_<op>(*case, perf_filename, device)`: build module (framework quant API), dry run, time
inside `benchmark_with_power(...)`, label `kernel_source` (e.g. `deepgemm` vs `torch_flow`),
`helper.log_perf(item_list=[...])`. Standalone `__main__` supported.

`framework_manifest.yaml`: current collector versions + runtime images per backend
(sglang 0.5.10, trtllm 1.3.0rc10, vllm 0.19.0); `wideep:` block overrides images only.

## THE THREE IDENTITIES contract (the skill's core)

1. **Recipe identity** — why the YAML requested the work.
2. **Benchmark-invocation identity** — every value changing the executed kernel/model/quant/setup.
3. **Persisted physical key** — the exact columns consumers query.

Rules: dedup only when invocation identity AND persisted key both match (documented canonical
representative for equivalent forms). **A persisted-key collision across distinct invocations is
a bug — fail population, never silent first-wins.** Quant labels must be truthful (W4A16 ≠ W4A8;
NVFP4/MXFP4/FP8/INT4 not interchangeable; never restore coverage with a different kernel under
the same label). `model_aliases` collapse only shape-only synthetic ops; `model_paths` expand
when the checkpoint changes behavior. **Consumer-contract gate: never modify
SDK/Rust/EngineSpec/Dynamo-Planner to make a generated case useful.** Don't prune coverage
because the synthetic collector can't run it — record the gap. Report counts as
kept/added/removed/deduplicated/skipped separately; final orphan audit.

## network/ (comm collection)

`collect_comm.sh` (intra-node): trtllm custom allreduce + NCCL all_reduce/all_gather/all2all/
reduce_scatter → `nccl_perf.txt`, `custom_allreduce_perf.txt` (land under
`systems/data/<system>/nccl/<ver>/`). `network/slurm/` = multi-node (allreduce, trtllm
alltoall, 1–16 node scripts). Needs `NCCL_TEST_BIN_PATH`.

## aic-auto-collect skill (long-run workflow)

One draft PR = one unit of work (`data/<system>-<backend>-<version>` branch, push ~hourly).
Phases: bring-up inside the target runtime container (record real `importlib.metadata.version`)
→ system YAML + `SupportedSystems` registration → **preflight** (check registry routes +
`__compat__`/SM gates against exact framework source BEFORE burning GPU-hours) → op order
`gemm → moe → attention/MLA → module-level → comm` → progressive per-op loop
(`--smoke → --limit 20 → --limit 100 → full --resume`) → failure classification
(collector_bug/unsupported_config/framework_bug/resource/transient; fix via VersionRoute +
`__compat__`, SM pre-filters; never synthesize rows) → perf-file quality gates → verify AIC
consumption (`get_database`, CLI runs, `tools/sanity_check/create_charts.py`) → support
matrix/docs → PR checklist. DCO sign-off on commits.

## Output format

`helper.log_perf()` appends CSV under a lock file (NFS caveat: use /tmp then copy). Base
columns: `framework, version, device, op_name, kernel_source`, then op-specific keys
(gemm: `gemm_dtype, m, n, k, latency`), then `power, power_limit` if measured. Finalized to
`*_perf.parquet` via pyarrow.
