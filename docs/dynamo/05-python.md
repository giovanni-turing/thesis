# Python Layer — bindings + components

Two trees: PyO3 extension `lib/bindings/python/` (wheel **ai-dynamo-runtime**, import
`dynamo._core`) and pure-Python `components/src/dynamo/` (wheel **ai-dynamo**, run as
`python -m dynamo.<x>`).

## PyO3 bindings (`lib/bindings/python/`)

- Build: maturin (`module-name = "dynamo._core"`); `Cargo.toml` is an **empty [workspace]** —
  deliberately outside the root workspace (pyo3 extension-module constraint); dependency pins
  duplicated from root and must stay in lockstep. Dev loop: `cd lib/bindings/python && maturin
  develop --uv` after any Rust change.
- Cargo features gate surface: `kv-indexer`, `slot-tracker`, `select-service`, `mm-routing`,
  **`aic-forward-pass`** (pulls `aiconfigurator-core` git pin — pure-Rust AIC latency engine),
  `mocker-kvbm-offload`, `media-ffmpeg`.
- Glue in `rust/`: `lib.rs` (pymodule root), `rust/llm/{entrypoint,kv,engine_perf,aic_callback,
  preprocessor,model_card,local_model,replay,fpm,lora}.rs`, `http.rs`, `kserve_grpc.rs`,
  `context.rs`, `planner.rs` (VirtualConnectorCoordinator), `parsers.rs`.
- **Exposed types** (authoritative stub: `src/dynamo/_core.pyi`): `DistributedRuntime`
  (`.endpoint("ns.comp.ep")` — **no Component pyclass**; `.register_engine_route`,
  `.set_health_status`), `Endpoint` (`.serve_endpoint(handler, health_check_payload=...)`,
  `.client(router_mode)`), `Client` (generate/random/round_robin/direct), `RouterMode`,
  `ModelType`/`ModelInput`/`WorkerType` (Prefill/Decode/Encode/Aggregated + DNF `needs`),
  `EntrypointArgs`/`EngineConfig`/`EngineType` (Echo/Dynamic/Mocker), `RouterConfig`,
  `KvRouterConfig`, `KvRouter`, `KvEventPublisher`, `WorkerMetricsPublisher`, `FpmDirectPublisher`
  /`FpmEventRelay`/`FpmEventSubscriber`, `HttpService`, `KserveGrpcService`, AIC classes
  (`AicPerfConfig`, `RustEnginePerfModel`...), planner classes. Functions: `register_model`,
  `fetch_model`, `make_engine`, `run_input`, `compute_block_hash_for_seq_py`, ...
- `src/dynamo/runtime/__init__.py` — `@dynamo_worker()` decorator (builds DRT from env, injects).
- **`src/dynamo/_internal/aic.py`** — AIConfigurator bridge: `AicSession`
  (predict_prefill/predict_decode via compiled Rust EngineHandle;
  `DYNAMO_AIC_DISABLE_COMPILED_ENGINE` forces Python fallback), `create_session` (called from
  Rust), `estimate_num_gpu_blocks` (per-backend memory-fraction semantics; result is per-rank).
  `DEFAULT_BACKEND_VERSIONS = {vllm 0.19.0, sglang 0.5.10, trtllm 1.3.0rc10}` (AIC v0.9.0 DB).
- `codegen/` — `gen-python-prometheus-names` parses `lib/runtime/src/metrics/prometheus_names.rs`
  → generates `src/dynamo/prometheus_names.py`. Run manually after editing Rust metric names.

## Components (`components/src/dynamo/`)

Pattern: `python -m dynamo.<x>` → `__main__.py` → `main()` → `uvloop.run(worker())`. Addressing
by `ns.component.endpoint`; model advertisement via `register_model(model_input, model_type,
endpoint, model_path, worker_type=..., needs=[[...]], ...)` → MDC into discovery → frontend
auto-discovers. Shared CLI framework in `common/configuration/` (ArgGroup, `RouterConfigBase`,
`KvRouterConfigBase`, `AicPerfConfigBase`, `DynamoRuntimeConfig`).

### frontend/

`main.py`: pops `DYN_SYSTEM_PORT`, parses `FrontendConfig`, builds DRT, maps `--router-mode` →
RouterMode (+ `KvRouterConfig` for kv), assembles `EntrypointArgs(EngineType.Dynamic, ...)`,
`make_engine` (constructs the Rust HttpService), `run_input(runtime, "http"|"grpc"|"text",
engine)`. `--dyn-chat-processor {dynamo,vllm,sglang}` swaps in Python processors
(`vllm_processor.py` — coerces CpuPlatform on GPU-less hosts, tokenizer only;
`sglang_processor.py` — preprocess worker pool). `prepost.py` = engine-agnostic pre/post
(`StreamingPostProcessor`: tool calls, reasoning, finish remap). Key flags: `--http-port`,
`--kv-cache-block-size`, `--namespace[-prefix]`, `--migration-limit`, TLS pair, `--serve-indexer`
xor `--use-remote-indexer`, `--enable-anthropic-api`, AIC triple for
`router-prefill-load-model=aic`.

### Engine backends — vllm/, sglang/, trtllm/

All: parse args → Config → init worker(s) → handlers serve `generate` + control routes →
`register_model` with WorkerType + DNF needs; publish via WorkerMetricsPublisher +
KvEventPublisher. `DisaggregationMode = agg|prefill|decode|encode` (common/constants.py).

- **vllm/**: `WorkerFactory` (worker_factory.py); handlers.py (~4k lines) —
  `Decode/Prefill/EmbeddingWorkerHandler` + rich engine routes (sleep/wake, profile,
  pause/resume, RL weight-sync suite, scale_elastic_ep, clear_kv_blocks); publisher wraps vLLM
  StatLoggerBase; **snapshot mode** (CRIU) + **headless mode** (no etcd/NATS); disagg via
  `kv_connector_protocols.py` (Nixl pull / Mooncake push); omni/ (realtime audio), multimodal.
- **sglang/**: `init_*`-per-modality dispatch (init_llm/init_embedding/init_diffusion/
  init_multimodal); async `parse_args`; handlers via mixins (`BaseWorkerHandler(LoraMixin,
  RLMixin, ...)`); publisher receives scheduler metrics over **ZMQ**, leader-only KV publish;
  `_disagg.py` (bootstrap address + prefill warmup — unwarmed prefill fails first request).
- **trtllm/**: `workers/` (llm/image-diffusion/video-diffusion) + `RequestHandlerFactory`
  (Encode/Prefill/Decode/Aggregated handlers); distinctive **ZMQ consolidator** KV-event path
  (Engine→ZmqKvEventPublisher→Consolidator→KvEventPublisher→NATS); `DisaggregatedParamsCodec`
  (opaque_state encode/decode); needs: Prefill→[[Decode]], Decode→[[Prefill]],
  Encode→[[Prefill,Decode],[Aggregated]].

### planner/ + global_planner/ — SLA autoscaling

`PlannerConfig` (pydantic): `mode {disagg,prefill,decode,agg}`, **`optimization_target
{throughput, latency, load, sla}`** (sla = Rust AIC perf model targeting ttft_ms/itl_ms), GPU
budgets, `load_predictor`. Watches: frontend Prometheus traffic metrics + **FPM**
(ForwardPassMetrics over NATS via FpmEventSubscriber); `monitoring/aic_interpolation.py` seeds
regression curves in-process. Decisions: `core/state_machine.py::PlannerScalingState` →
`ScalingDecision{num_prefill, num_decode}`; perf models `core/perf_model/{prefill,decode}.py`
(estimate_next_ttft / binary-search max batch for ITL SLA). Adapters
Prefill/Decode/Agg/DisaggPlanner over `NativePlannerBase`. Connectors: `kubernetes.py`
(update_graph_replicas ±1), `virtual.py` (Rust VirtualConnectorCoordinator for tests),
`global_planner.py`. Plugin pipeline under `plugins/` (gRPC transport, merge strategies).
global_planner: cross-pool GPU budget enforcement (`scale_handler.py::ScaleRequestHandler`,
intent cache, `max_total_gpus` ceiling under `_scale_lock`).

### profiler/

`profile_sla.py::run_profile` on a DGDR spec. **rapid.py** = AIC simulation only (no GPUs) →
pick rank-1 config → generate DGD via AIC generator. **thorough.py** = deploy candidates on real
GPUs (`DynamoDeploymentClient`) + aiperf sweeps → Pareto pick. `interpolation.py` = real-GPU
interpolation curves (thorough mode only). `profile_endpoint.py` = standalone endpoint profiler.
Outputs: DGD YAML, interpolation NPZ, Pareto plots → consumed by planner (`profile_results_dir`).

### mocker/

GPU-free worker simulation: `MockEngineArgs` + AIC latency model (`aic_session.py` re-exports
`_internal.aic`; `_estimate_aic_num_gpu_blocks` derives KV capacity). `launch_workers` staggers N
workers → Rust mocker engine (EngineType.Mocker). Used by router tests + frontend benchmarks.

### Routers

- `router/` — standalone KV router launcher (wraps Rust KvRouter; args from KvRouterArgGroup).
- `global_router/` — routes across worker **pools** (disagg pool namespaces, priority + retry).
- `thunderagent_router/` — agent/session-aware scheduling (program state, pause/resume,
  session pinning).

### common/

`forward_pass_metrics.py` (FPM msgspec schema v1: scheduled/queued prefill+decode token stats,
Welford variance — workers emit, planner consumes), `model_fetch.py` (subprocess fetch for
snapshot mode), `metadata_upload.py` (fsspec), `configuration/` (CLI framework), `backend/`
(reusable worker scaffolding), `config_dump/`, multimodal utils, `snapshot/` (CRIU lifecycle).
