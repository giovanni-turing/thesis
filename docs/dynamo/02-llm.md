# `lib/llm` (dynamo-llm) — LLM Serving Core

Module map in `src/lib.rs`. Default feature `block-manager` (pulls nixl-sys, cudarc). Other
features: `mm-routing` (multimodal KV routing), `cuda`, `nccl`, `testing-*`. Depends on sibling
crates: `dynamo-runtime`, `dynamo-kv-router` (re-exported), `dynamo-protocols`, `dynamo-parsers`,
`dynamo-renderer` (Jinja), `dynamo-tokenizers`, `dynamo-tokens`, `dynamo-memory`, `dynamo-mocker`.

Core abstraction (from runtime): pipeline of `Operator`s wired with `.link()`; requests
`SingleIn<T>`, responses `ManyOut<Annotated<T>>`; `AsyncEngine::generate` is the fundamental call.

## HTTP frontend — `src/http/service/`

- **`service_v2.rs`** — `HttpService` via builder. `HttpServiceConfig`: `port` (8787), TLS,
  per-endpoint enable flags, `FrontendApiConfig`, RL discovery (`/v1/rl/workers`). Shared
  `Arc<State>`: `Metrics`, `ModelManager`, `Discovery`, `ServiceObserver`, `StateFlags`
  (per-`EndpointType` runtime toggles). Graceful shutdown: `ServiceStage {Ready, Draining,
  Stopping}` + `InflightPermit` RAII held for the full SSE stream
  (`DYN_HTTP_GRACEFUL_SHUTDOWN_TIMEOUT_SECS`). Two routers: system (metrics/models/health) and
  inference (chat/cmpl/embeddings/responses/anthropic/realtime/...). Route paths overridable via
  `DYN_HTTP_SVC_*_PATH`.
- **`openai.rs`** (~6k lines) — handlers for `/v1/completions`, `/v1/chat/completions`,
  `/v1/embeddings`, `/v1/models`, `/v1/responses` (OpenAI Responses API), images/videos/audios.
  Handler flow: parse (with lossy-UTF8 recovery) → `check_ready` + `check_model_serving_ready`
  (503) → nvext header routing overrides → request-id from trace context → connection monitor
  (disconnect → cancel) → `state.manager().get_chat_completions_engine_with_parsing(model)` →
  `engine.generate(request)`. **Always streamed internally**; non-streaming folds via
  `from_annotated_stream`. Error mapping: QueueRejection/ResourceExhausted→529, unavailable→503,
  InvalidArgument→400, Cancelled→499. Body limit `DYN_HTTP_BODY_LIMIT_MB` (45 MB).
- Others: `anthropic.rs` (`/v1/messages`), `realtime.rs` (`/v1/realtime` WebSocket),
  `disconnect.rs` (`ConnectionHandle`, `monitor_for_disconnects`), `metrics.rs`,
  `busy_threshold.rs` (admin API), `health.rs`, `error.rs`.

## Preprocessor — `src/preprocessor.rs` + `preprocessor/`

**`OpenAIPreprocessor`** — an `Operator` (forward: Chat/CompletionRequest →
`PreprocessedRequest`; backward: `Annotated<BackendOutput>` → response). Holds
`OAIPromptFormatter` (minijinja via dynamo_renderer), `Tokenizer`, `ModelInfo`,
`kv_cache_block_size`, tool-call parser, media loader. Key methods: `preprocess_request`,
`apply_template`, `tokenize`.

- Templates come from the MDC: `prompt_formatter_from_mdc` reads `HfTokenizerConfigJson` and
  overlays `HfChatTemplateJinja`/`HfChatTemplateJson`; DeepSeek gets a native fallback.
- Flow: template → prompt string → `tokenizer.encode` → `PreprocessedRequest {token_ids,
  stop_conditions, sampling_options, output_options}`. Annotations `formatted_prompt`, `token_ids`.
- Reasoning/tool parsing from `dynamo_parsers`; `preprocessor/{tool_choice,structural_tag}.rs`.
- Media (`preprocessor/media/`): `MediaLoader`, image/video decoders (media-ffmpeg), RDMA
  fetch, SSRF-aware fetcher; `lightseek_mm.rs` (mm-routing) counts image tokens for MM routing.
  Edge cases documented in `PREPROCESSOR_CASES.md`.

## Protocols — `src/protocols/`

- `common/preprocessor.rs` — **`PreprocessedRequest`** (token_ids, stop/sampling/output options,
  `multi_modal_data`, `routing: RoutingHints`, LoRA), `PreprocessedEmbeddingRequest`,
  `BootstrapInfo`, `PrefillResult`.
- `common/llm_backend.rs` — **`LLMEngineOutput`** (raw engine: token_ids, logprobs, finish_reason,
  disaggregated_params) vs **`BackendOutput`** (post-detokenization: + text/tokens/stop_reason).
- `openai/` — `Nv*` newtype wrappers around OpenAI types per endpoint family; `delta.rs`
  incremental generators, `aggregator.rs` stream folding, `nvext.rs` sidecars.
  `AnnotatedDelta<R>`, `DeltaGeneratorExt`, `ParsingOptions`.
- `anthropic/` (types + stream converter), `tensor.rs` (KServe), `codec.rs`.

## Entrypoints — `src/entrypoint/`

- **`EngineConfig`** enum: `Dynamic` (remote engines via discovery; holds `LocalModel`) |
  `InProcessText` (`StreamingEngine`, does own tokenization) | `InProcessTokens`
  (`ExecutionContext` wrapped with pre/post processors). `RouterConfig {router_mode,
  kv_router_config, load_threshold_config, session_affinity_ttl_secs}`.
- **`Input`** enum: `Http | Stdin | Text | Endpoint("dyn://…") | Grpc`. `run_input(drt, input,
  engine_config)` dispatches to `entrypoint/input/{http,grpc,text,endpoint}.rs`.
- **`input/common.rs` is the pipeline-wiring core**: `build_preprocessed_routing` selects the
  router (`SessionAffinityPushRouter` | `LoraFilteredRouter` | `KvPushRouter`); waits for
  `DYN_ROUTER_MIN_INITIAL_WORKERS`; `build_pipeline` links
  `ServiceFrontend → OpenAIPreprocessor → Backend.forward → engine → Backend.backward →
  Preprocessor.backward → frontend` (+ Migration + PrefillRouter in the full path). BYO processor
  path (`--dyn-chat-processor vllm|sglang`) skips the Rust preprocessor.
- `input/http.rs` — for `Dynamic`, spawns `run_watcher` (ModelWatcher) to register discovered
  models onto `ModelManager`.

## Backend, engines, migration

- **`src/backend.rs`** — `Backend`, the final detokenization operator. `ExecutionContext =
  ServerStreamingEngine<PreprocessedRequest, Annotated<LLMEngineOutput>>`. Per-choice `Decoder`
  (n>1 via HashMap), incremental detokenize, `StopTrigger` → FinishReason/StopReason.
- **`src/engines.rs`** — `StreamingEngine` / `EmbeddingEngine` traits, `EngineDispatcher`,
  `ValidateEngine`, `EchoEngine` (ingress testing, `DYN_TOKEN_ECHO_DELAY_MS`).
- **`src/migration.rs`** — `Migration` operator: on stream disconnect, recreates the downstream
  stream and replays from last token (bounded by `migration_limit` / `migration_max_seq_len`) —
  transparent worker-fault tolerance mid-generation.

## Model management & discovery

- **`local_model.rs`** — `LocalModel`/`LocalModelBuilder`: local view of a model
  (MDC + resolved path + all serving config). `LocalModel::fetch` pulls from HF hub.
- **`model_card.rs`** — **`ModelDeploymentCard` (MDC)**: `ModelInfoType::HfConfigJson`,
  `TokenizerKind::{HfTokenizerJson, TikTokenModel}`, `PromptFormatterArtifact::{...}`; artifacts
  wrap `CheckedFile` (checksummed local/remote). `mdcsum()` content hash = engine key.
  Published to KV store at `ROOT_PATH = "v1/mdc"`.
- **`model_type.rs`** — bitflags `ModelType` (Chat|Completions|Embedding|Tensor|Prefill|...);
  `EndpointType` enum per HTTP surface.
- **`src/discovery/`** — **`ModelManager`** (central registry HTTP queries: engines per
  capability, readiness, MDC store, `kv_chooser_for` builds the per-model KvRouter, LoRA
  machinery) + **`ModelWatcher`** (`watcher.rs` — watches `DiscoveryQuery::AllModels`,
  registers/deregisters worker cards, distinguishes decode vs prefill workers, activates the
  prefill router). **This is how routes map to models**: worker publishes MDC+ModelType →
  watcher registers engine under display name → HTTP resolves `request.model`.
  `worker_monitor.rs` — `KvWorkerMonitor` (ActiveLoad subscription → overload detection).

## gRPC — `src/grpc/service/`

`kserve.rs` — KServe v2 gRPC (`KserveService`, wraps an inner HttpService for shared state):
`ModelInfer` (streaming), `ModelReady` (reflects decode+prefill completeness), `ModelMetadata`.
`openai.rs` — OpenAI-over-gRPC completions. `tensor.rs` — raw-tensor conversion.

## Cross-cutting

`audit/`, `request_trace/` (record/replay), `telemetry/`, `session_affinity/`
(`SessionAffinityPushRouter`), `lora/` (routing min-cost-flow + HRW, cache, controller),
`request_template.rs`, `namespace.rs` (`NamespaceFilter`), `frontend_config.rs`,
`common/checked_file.rs`. Bin `src/bin/generate_frontend_openapi.rs`.

## Navigation entry points

- Add HTTP endpoint → `http/service/openai.rs` (router + handler) + `service_v2.rs`
  `get_endpoints_router` + `EndpointType`/`StateFlags`.
- Change routing behavior → `entrypoint/input/common.rs` (`preprocessed_backend_engine`) +
  `kv_router/push_router.rs`.
- Prompt/tokenization → `preprocessor.rs` + `preprocessor/prompt.rs` + `model_card.rs`.
- Model registration/discovery → `discovery/watcher.rs` + `discovery/model_manager.rs`.
