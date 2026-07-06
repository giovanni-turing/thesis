# SDK Performance-Model Core (`src/aiconfigurator/sdk/`)

Layering: `task_v2.Task` (task description) → `models/` (op graphs) → `operations/` (op cost
primitives) → `perf_database` (collected-data queries + interpolation) → `backends/`
(scheduling + memory composition into TTFT/TPOT/throughput). Design docs:
`docs/perf_database/*.md`, `docs/design/hybrid_modeling_design.md`, per-package READMEs.

## perf_database.py

- **Layout**: system YAMLs `systems/<gpu>.yaml` (`gpu:` mem_bw/mem_capacity/*_tc_flops/sm_version,
  `node:` gpus+bandwidths, `misc:` nccl_mem/other_mem) → `SystemSpec` (`system_spec.py`;
  `get_p2p_bandwidth` 3-tier NVLink/NVSwitch/IB). Perf tables
  `systems/data/<gpu>/<backend>/<version>/<op>_perf.parquet` (legacy `.txt` fallback); filenames
  in `common.PerfDataFilename`.
- **Construction**: `get_database(system, backend, version, ...)` → cached `PerfDatabase`.
  **Lazy per-op ownership**: `__init__` opens ZERO files; each op class loads its table on first
  query (`OpClass.load_data(database)`, class-level `_data_cache`). `get_database_view()` =
  lightweight copy with immutable `(mode, transfer_policy)`.
- **Query API**: `query_gemm(m,n,k,quant_mode,mode)`, `query_context/generation_attention(b,s,
  prefix,n,n_kv,kv/fmha quant,window,head_size)`, `query_*_mla[_module]`, `query_moe(num_tokens,
  hidden,inter,topk,experts,moe_tp,moe_ep,quant,distribution,...)`, wideep variants,
  `query_nccl(dtype,num_gpus,op,bytes)`, `query_mem_op(bytes)` (pure analytic), DSA/DSv4/mamba
  module queries. All `@lru_cache(32768)`. Returns `PerformanceResult` (float-like, `.energy`,
  `.source` ∈ silicon/empirical/mixed/sol).
- **Interpolation** (`interpolation.py`): interp_1d/2d/3d (+bilinear/cubic 2d1d);
  `nearest_1d_point_helper(inner_only=True)` raises outside measured range;
  `extrapolate_data_grid` runs once at load. Piecewise top-k-aware interp for DSA/CSA (refuses to
  cross kernel-regime boundaries).
- **Modes** (`common.DatabaseMode`): SILICON (default) | HYBRID | EMPIRICAL | SOL | SOL_FULL.
  Branch per op in `_query_*_table`: SOL/EMPIRICAL early-return analytic; SILICON/HYBRID go via
  `_query_silicon_or_hybrid` (HYBRID falls back to empirical on
  PerfDataNotAvailable/InterpolationDataNotAvailable; SILICON re-raises).
- **Shared layer** (`enable_shared_layer`): priority-ordered fallback across other versions/
  frameworks of the same op, rows filtered by `kernel_source` per
  `systems/op_kernel_source_manifest.yaml` (tiers shared/shared_fallback); first-wins.
  Sentinels in data dirs: `SHARED_LAYER_REUSE.txt`, `INCOMPLETE.txt`.
- **Empirical**: SOL ÷ utilization factor learned from nearest collected data
  (`operations/util_empirical.py`); transfer permissions via `TransferKind`
  (XSHAPE/XQUANT/XPROFILE/XOP) + `transfer_policy` presets off/conservative/balanced/aggressive.
- `supported_quant_mode` = `_LazySupportMatrix` (loads the table on key access).

## models/

- **Registry**: `@register_model("FAMILY")`; `get_model(model_path, model_config, backend)` —
  HF config → `common.ARCHITECTURE_TO_MODEL_FAMILY` → registry class `.create(...)`.
  `model_info` keys: layers, n, n_kv, d, hidden/inter size, vocab, topk, num_experts, extra_params.
- **BaseModel** (`models/base.py`): builds three ordered op lists — `encoder_ops`,
  `context_ops`, `generation_ops`. KV helpers: `get_kvcache_elements_per_token()` (MLA = shared
  latent, unsharded by TP; GQA = n_kv·d·layers·2), `get_kvcache_max_tokens(budget)`. CP support
  via `_cp_attn_comm_ops` (KV all-gather insert); CP saves prefill compute, NOT KV memory.
- **Families**: `gpt.py`, `llama.py` (also Qwen2/3), `moe.py` (+SGLangEPMOE), `deepseek.py`
  (+WideEP trtllm/sglang, KIMIK25), `deepseek_v32.py` (DSA), `deepseek_v4.py` (mHC+CSA/HCA/SWA),
  `nemotron_h.py`/`qwen35.py`/`hybrid_moe.py` (Mamba/GDN hybrids), `nemotron_nas.py` (PUZZLE),
  `gemma4.py`, `qwen3vl.py` (+`vit_ops.py`), `minimax_m3.py`.
- **Op graph example** (llama context): Embedding → add_norm → GEMM(qkv) → ContextAttention →
  GEMM(proj) → add_norm → GEMM(gate_ffn1) → act → GEMM(ffn2) → GEMM(logits) + AllReduce×3 + P2P.
  Each op carries `scale_factor` (≈ num_layers; generation ×`_mtp_scale_factor` for MTP).
  **Op names are contracts**: `context_attention`/`generation_attention`/`logits_gemm` are
  matched literally by backends and the Rust engine.

## operations/

- **Interface** (`base.py`): `Operation(name, scale_factor, seq_split=)`,
  `query(database, **kwargs) -> PerformanceResult`, `get_weights()`. Idempotent classmethod
  `load_data(database)`; `clear_all_op_caches()` / `warm_all_op_data()`.
- **Pattern** (canonical `gemm.py`): nested `get_sol` (e.g. GEMM `max(2mnk/flops,
  bytes/mem_bw)`), `get_empirical` (SOL/util grid), branch on mode, else silicon lookup +
  interp. SOL-clamp corrections applied at load.
- **Modules**: gemm, attention (Context/Generation/Encoder), mla (+ module + bmm + wideep),
  moe (+dispatch, wideep, workload_distribution power_law), dsa, dsv4 (CSA/HCA/mHC/MegaMoE),
  mamba (Mamba2/GDN), communication (NCCL/CustomAllReduce/P2P), embedding+elementwise
  (analytic mem-ops), afd_transfer, overlap (`OverlapOp` = max of two groups; `FallbackOp`),
  util_empirical, vit_ops.

## backends/

`factory.get_backend(name)` → `TRTLLMBackend` / `VLLMBackend` / `SGLANGBackend`, all over
`base_backend.BaseBackend` (shared logic + overridable hooks/constants).

- **`run_static(model, db, runtime_config, mode)`** — sums op queries over context/generation
  ops; generation uses stride quadrature (step 32) and `(nextn+1)` batch scaling; produces
  `InferenceSummary` (TTFT=ctx, TPOT=gen/(osl-1), per-GPU normalization, OOM check).
- **`run_agg(...)`** — in-flight batching simulation: mix steps (3-pass `_get_mix_step_latency`:
  non-attention combined, context-attention scaled, generation-attention) + gen-only steps;
  `find_best_agg_result_under_constraints` sweeps batch under SLA; `_agg_cache` memoizes
  (built once per parallel config — survives the tpot loop, ~80x).
- **`_get_memory_usage(...)`** → {weights/pp, activations (family×tp coefficient tables +
  MoE workspace + MTP scaling), kvcache = batch×bytes_per_seq (NOT /pp), nccl, other} GiB.
- **Per-backend hooks**: trtllm — pipeline-drain `_tpot_mix_steps=max(1,n-3)`, KV-aware OOM
  (`free_gpu_memory_fraction=0.9`, reserved 1.5%/tolerance 2%); vllm — v1 scheduler model
  (`max_num_partial_prefills=1`, dispatch overhead 0.8ms/layer, TTFT queuing factor
  `1+log2(b)/8`≤2, Little's-Law throughput cap); sglang — higher activation coefficients,
  +15% activation / +20% other overhead (Python runtime).

## memory.py — KV capacity (single source of truth; Rust forwards to it)

- `KVCacheEstimator.from_request(...)`: builds model+backend+DB, `non_kv = weights+activations+
  runtime+comm`, then budget: **trtllm `of_free`** = fraction×(capacity−non_kv);
  **vllm/sglang `of_total`** = capacity×fraction−non_kv. Token count via model KV-curve inverse.
- `NaiveKVCacheEstimator` fallback for unbuildable models (HF geometry parse, 0.80 reservation,
  HYBRID vs LINEAR mode); raises rather than guessing.
- **`estimate_num_gpu_blocks(...)`** = floor(kv_tokens/block_size) — what Dynamo's mocker uses.

## task_v2.py / config.py

- `ModelConfig` (tp/pp/attention_dp/cp/moe_tp/moe_ep + 5 quant modes + nextn/moe_backend/wideep;
  `resolve_moe_parallelism()` enforces **tp·dp·cp == moe_tp·moe_ep**), `RuntimeConfig`
  (batch/isl/osl/prefix/SLAs/engine_step_backend), `AFDConfig`. Builders in `config_builders.py`.
- **`Task`** (flat dataclass): mode+workload+SLA, agg worker spec + search-space candidate
  lists (`agg_{num_gpu,tp,pp,dp,moe_tp,moe_ep,cp}_candidates`), independent
  `prefill_*`/`decode_*` disagg specs (hetero-disagg capable), orchestration knobs (worker caps,
  latency corrections 1.1/1.08, rate-match degradations 0.9/0.92, autoscale ttft correction
  1.8). `__post_init__` fully resolves (model family, DB version, quant defaults, candidates);
  `validate()` cross-checks quant vs DB support matrix; `.run()` dispatches to sweep;
  `from_yaml`/`to_yaml`.
- Prediction seam: `predict.predict_agg_worker`/`predict_disagg_worker` over a `Predictor`
  Protocol (`AnalyticPredictor` default).

## The Rust seam (`engine.py`, `rust_engine_step.py`)

- `compile_engine` / `build_engine_spec_json`: walk built model op lists → externally-tagged
  OpSpec dicts → JSON `{schema_version:1, engine, context_ops, generation_ops}` (vision ops
  never emitted) → Rust `engine_spec_bincode_from_json` → bincode bytes → `EngineHandle`
  (`AicEngine.from_spec`). Surface: `run_static`, `predict_prefill/decode_latency`,
  `mixed_step_latency`, `decode_step_latency`. Agg orchestration stays in Python.
- `rust_engine_step.py`: gate `should_use_rust_engine_step`
  (`AICONFIGURATOR_ENGINE_STEP_BACKEND=rust` or RuntimeConfig field); `_ENGINE_HANDLE_CACHE`
  keyed by engine identity (batch/isl/osl NOT in the key — shared handle);
  `_configure_default_data_roots()` exports `AICONFIGURATOR_SYSTEMS_PATH` /
  `AICONFIGURATOR_MODEL_CONFIGS_PATH` for Rust. Also hosts the `RustForwardPassPerfModel`
  facade (Dynamo planner FPM path).
- Dynamo side: `dynamo/lib/bindings/python/src/dynamo/_internal/aic.py` (`AicSession`,
  `create_session`, `estimate_num_gpu_blocks`).
