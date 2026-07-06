# Rust Core (`rust/aiconfigurator-core`) — "Python builds, Rust executes"

Crate v0.10.0, edition 2021, `crate-type = ["rlib", "cdylib"]`, PyO3 0.23 abi3-py310. Sole
workspace member of the root `Cargo.toml`. Phase-1 latency estimator: Python `compile_engine`
walks the model **once** → `EngineSpec` → Rust `Engine` executes per-iteration latency
**GIL-free**. Modules: `common/`, `config`, `engine/`, `operators/`, `perf_database/`,
`session`, `fpm/`, `memory`, `py`.

## Two call directions

- **Python → Rust hot path**: `AicEngine` pyclass (SDK sweep via
  `backends/base_backend.py` `estimate_*_with_rust`, gated by `should_use_rust_engine_step`).
- **Rust → Python → Rust embedded**: `build_aic_engine` (plain pub fn, NOT in the pymodule) —
  crosses into Python once for `compile_engine`, then pure Rust. Used by Dynamo mocker/planner.

## engine/

- **`spec.rs` — `EngineSpec { schema_version: 1, engine: EngineConfig, context_ops,
  generation_ops: Vec<Op> }`**. Wire is **JSON→bincode**: `EngineConfig` uses
  `#[serde(flatten)]` which bincode can't serialize, so `to_bincode` JSON-encodes the engine
  field inside a `BincodeWire`. Python builds JSON; `engine_spec_bincode_from_json` re-encodes.
  Vision ops never appear on a compiled spec (decomposed at compile time). An
  exhaustive-match test forces every new `Op` variant into the round-trip suite.
- **`runtime.rs` — `Engine { context_ops, generation_ops, db: Arc<PerfDatabase>, nextn }`**
  (parallel/quant scalars deliberately not stored). Execution mirrors Python
  `run_static`/`_run_static_breakdown`: prefill = one pass over context_ops
  (`effective_isl = isl − prefix`); decode = stride quadrature (`DEFAULT_STATIC_STRIDE=32`),
  batch ×(nextn+1). Methods: `run_static` → `StaticResult{context_ms, generation_ms,
  total_ms}`, `predict_prefill/decode_latency`, `mixed_step_latency` (inline FPM packing:
  prefill chunks, cached-prefix subtraction), `decode_step_latency`,
  `forward_pass_time_ms(&[ForwardPassMetrics])` (max across attention-DP ranks).
  `latency_correction_scale` is post-multiplied on the Python side.
- **`session.rs`** — shared `run_context_ops` / `run_generation_ops_step` /
  `get_mix_step_ops` (3-pass mix composition) so engine-step and FPM paths stay identical.

## operators/

Mirrors `sdk/operations`. **No trait** — a typed enum `Op` with one variant per family and a
single `Op::query(db, &RuntimeContext) -> PerformanceResult` dispatch. Families: gemm,
attention (Context/Generation/Encoder), mla (+module/bmm), moe (+dispatch), communication
(CustomAllReduce/Nccl/P2P), mamba (Mamba2/Gdn), dsa, dsv4, mhc, wideep_mla, wideep_moe,
elementwise, embedding, vision, recursive `OverlapOp` (max of group sums) and `FallbackOp`
(primary, else fallback chain on PerfDatabase/Io error). Name-based special cases:
`"context_attention"`/`"generation_attention"`/`is_logits_gemm()` matched literally.
`PerformanceResult{latency_ms, source: Silicon|Empirical|Sol|Mixed}`.

## fpm/ — Forward-Pass-Metrics model (Dynamo FPM v1 aligned)

`ForwardPassPerfModel`: `Native{engine, corrections}` (native estimate × per-region correction
from `CorrectionBuckets` — local median observed/native ratio) or `Regression` fallback
(`BucketedRegression`, linear per workload kind). `best_available` falls back to regression only
on recoverable errors. `fpm/metrics.rs` = AIC-owned copy of Dynamo's scheduler telemetry
(`ForwardPassMetrics` v1: scheduled/queued prefill+decode token stats) so AIC doesn't depend on
Dynamo crates. Workload kind (Prefill/Decode/Mixed) inferred per iteration. Options: 16 buckets,
min 5 / max 64 observations, bounds max_num_tokens 8192 / max_batch 512 / max_kv 2M.

## perf_database/ (Rust) + memory.rs

- `PerfDatabase::load(systems_root, system, backend, version)` — cheap: parse system YAML,
  resolve data_root. **Lazy per-table via OnceLock**; reads **parquet** (`parquet` crate);
  `PerfReader::open` detects unresolved **git-LFS pointers** and says "run `git lfs pull`".
  GEMM query: exact → 1-D interp on m → 3-D bilinear; `fp8_static` normalized to `fp8`.
- `memory.rs::estimate_kv_cache` — **pure forwarder into Python `sdk/memory`** (all math in
  Python); Rust-only for embedded callers (mocker derives `num_gpu_blocks_per_rank`).
  `KvCacheMemoryFraction::{OfTotal, OfFree}` encodes the vLLM/SGLang-vs-TRT-LLM budget split.

## py.rs — PyO3 surface (module `aiconfigurator_core._aiconfigurator_core`)

- `_build_smoke()` (schema version, import check), `engine_spec_bincode_from_json(json) -> bytes`.
- **`AicEngine`**: `from_spec(bytes, systems_path=None)`; `run_static(...)` → (ctx, gen, total);
  `predict_prefill_latency`, `predict_decode_latency`, `mixed_step_latency`,
  `decode_step_latency` — each releases the GIL (`allow_threads`). Inherent GIL-free
  `prefill_latency_ms`/`decode_latency_ms` for Rust callers (the mocker). Send+Sync.
- **`RustForwardPassPerfModel`**: `from_native`/`best_available`/`from_regression`,
  `estimate_forward_pass_time_ms(fpm_json)`, `tune_with_fpms`, `diagnostics`.
- `build_aic_engine` (pub fn, not exported to Python): with_gil → import
  `aiconfigurator.sdk.engine.compile_engine` → bytes → `Engine::from_spec_bytes`. Error policy:
  compile failure → `UnsupportedModel` (fallback-safe); hard errors → `InvalidEngineConfig` (not).

## Parity & tests

- `parity_tests/test_engine_step_parity.py` — **< 1% rtol** (`PARITY_RTOL=0.01`) across
  static_ctx/gen/total, mixed_step, agg, disagg; error cases must fail on both sides. Run:
  `AICONFIGURATOR_RUST_CORE_AUTOBUILD=1 uv run pytest rust/aiconfigurator-core/parity_tests/...`
- `test_compile_engine_parity.py` — op-transfer fidelity (op names/order, single-tag, no
  Vision) + numeric parity + determinism. `benchmark_engine_step.py` (p50/p90/p99 + speedup).
- Rust embed tests need `cargo test --features embed-python`.

## Build & shipping

- Shipped **inside the aiconfigurator wheel via maturin** (root pyproject:
  `manifest-path=rust/aiconfigurator-core/Cargo.toml`, `module-name =
  "aiconfigurator_core._aiconfigurator_core"`, abi3; systems parquet + model_configs bundled).
- Feature discipline: default `[]`; `pyo3/extension-module` ONLY in the wheel build;
  `cargo build/test` links libpython for embedding; embed tests need `embed-python`.
- `src/aiconfigurator_core/__init__.py` re-exports the compiled symbols. The PyPI
  **`aiconfigurator-core` package is payload-free** (setuptools, `packages=[]`, depends on
  `aiconfigurator==0.10.0`) — a resolver alias.

## Dynamo consumption

Git pin in dynamo's root + bindings Cargo.toml:
`aiconfigurator-core = { git = ".../aiconfigurator.git", rev = "ffbab157..." }`, gated behind
the **`aic-forward-pass`** feature (`lib/mocker`, `lib/bindings/python`).
`rust/llm/aic_callback.rs::RustAicCallback{ engine: Arc<AicEngine> }` implements the mocker's
`AicCallback`/`PrefillLoadEstimator` via the GIL-free inherent methods; `build_rust_engine`
calls `build_aic_engine` once at startup — **build failure is a hard error, no Python fallback**.
Without the feature, `--aic-perf-model` errors with a rebuild hint.
