# Dynamo — Agent Navigation Docs

Deep architecture reference for `/home/gio/tese/ai-dynamo/dynamo` (NVIDIA Dynamo, upstream mirror on
`main`). Produced 2026-07-05 by whole-tree exploration; paths are repo-relative unless absolute.
These complement (do not replace) the repo's own `CLAUDE.md`, `.ai/*.md`, and `docs/design-docs/`.

## Documents

| Doc | Covers |
| --- | --- |
| [01-runtime.md](01-runtime.md) | `lib/runtime` — DistributedRuntime, Namespace/Component/Endpoint, discovery (etcd/file/K8s), request plane (TCP/NATS), event plane (ZMQ/NATS), pipeline system, health/metrics |
| [02-llm.md](02-llm.md) | `lib/llm` — HTTP frontend (OpenAI-compatible), preprocessor/templating, protocols, entrypoints, Backend/detokenization, migration, model cards + discovery, gRPC/KServe |
| [03-kv-routing.md](03-kv-routing.md) | `lib/kv-router`, `lib/kv-hashing`, `lib/tokens`, `lib/llm/src/kv_router` — PLH hashing, radix indexer, cost function, KV events, replica sync, recovery |
| [04-kvbm.md](04-kvbm.md) | `lib/kvbm-*`, `lib/memory`, `lib/gpu_memory_service`, `lib/bindings/kvbm` — tiered KV cache G1→G4, leader/worker, offload, NIXL transfers, vLLM connector |
| [05-python.md](05-python.md) | `lib/bindings/python` (PyO3) + `components/src/dynamo/` — frontend, engine backends (vllm/sglang/trtllm), planner, profiler, mocker, routers, common |
| [06-dev-workflow.md](06-dev-workflow.md) | tests/, examples/, deploy/ (operator/CRDs/Helm/GAIE), recipes/, container/, benchmarks/, `.ai/` rules, CI, docs/fern |

## The big picture

Dynamo is a datacenter-scale LLM inference **orchestration layer** above engines (vLLM, SGLang,
TRT-LLM). Rust performance core (`lib/`, Cargo workspace), Python launchers/integrations
(`components/src/dynamo/`, run as `python -m dynamo.<x>`), bridged by PyO3
(`lib/bindings/python`, built with `maturin develop --uv` — rerun after any Rust change).

```
client ──HTTP──> Frontend (lib/llm http + OpenAIPreprocessor: template→tokenize)
                    │  PreprocessedRequest (token_ids)
                    ▼
                 Router (RouterMode: RoundRobin default | KV | Random | LeastLoaded | ...)
                    │  KV mode: block-hash → radix indexer lookup → cost function → pick worker
                    ▼
        ┌─ prefill worker ──KV cache over NIXL/RDMA──> decode worker ─┐
        │        (disaggregated; engines publish KV events + metrics)  │
        └──────────────── streamed tokens back ────────────────────────┘
                    │
                 Backend operator (detokenize, stop conditions) → SSE to client
```

**Data planes** (all selectable by env/flags): discovery = etcd | file | memory | Kubernetes
(`DYN_DISCOVERY_BACKEND`, default etcd); request plane = **TCP (default)** | NATS
(`DYN_REQUEST_PLANE`); event plane (KV events, FPM) = **ZMQ (default)** | NATS (`DYN_EVENT_PLANE`).

## Key facts an agent should know up front

1. **Two KVBM implementations coexist.** v1 lives in `lib/llm/src/block_manager/` and is what the
   Python bindings (`lib/bindings/kvbm`) actually use in production. The `lib/kvbm-*` crates are a
   ground-up v2 rewrite, internally complete but only consumed by `lib/mocker` so far. See 04.
2. **Dual-hash reality in the router.** The production radix tree keys on `LocalBlockHash(u64)`
   content hashes + parent-chained `ExternalSequenceBlockHash(u64)`. The 128-bit
   `PositionalLineageHash` (PLH, defined in `lib/tokens`, wrapped by `lib/kv-hashing`) is the
   *future* universal key — router migration is an unexecuted "Phase C". See 03.
3. **`lib/bindings/python` is a deliberately separate Cargo workspace** (pyo3 extension-module
   constraint); its dependency pins must stay in lockstep with the root workspace manually.
4. **Addressing is `namespace.component.endpoint`** (or `dyn://…`). Python has no `Component`
   class — `DistributedRuntime.endpoint("ns.comp.ep")` does it all. Registration writes
   lease-scoped instances into `v1/instances/{ns}/{comp}/{ep}/{lease_id:x}`.
5. **Model cards (MDC)** are published to the KV store under `v1/mdc`; the frontend's
   `ModelWatcher` discovers them and registers engines in `ModelManager` — that is how an HTTP
   `model` field maps to workers.
6. **Never run bare `pytest`** — venv-aware invocation with markers; CI runs on 24 GB L4s, use
   small models (Qwen3-0.6B). Read `.ai/pytest-guidelines.md` + `tests/README.md`. See 06.
7. Authoritative in-repo docs: `docs/design-docs/` (architecture.md, disagg-serving.md,
   router-design.md, kvbm-design.md, planner-design.md, distributed-runtime.md,
   discovery-plane.md, request-plane.md, event-plane.md).

## Cross-project links

- **NIXL** (`/home/gio/tese/ai-dynamo/nixl`) — `nixl-sys` (=1.0.1) wrapped by `lib/memory`;
  KV transfer for disagg + KVBM tiers + GDS.
- **AIConfigurator** — `dynamo._internal.aic` (bindings) bridges to `aiconfigurator.sdk`; the
  Rust perf model (`aic-forward-pass` feature, `aiconfigurator-core` git pin) powers mocker
  timing, planner SLA mode, and profiler rapid mode.
- **Grove** — operator integration via `deploy/operator/internal/dynamo/grove.go`
  (PodCliqueSets for multi-node); Helm `global.grove.install/enabled`.
- **AIPerf** — load generator used by `recipes/*/perf.yaml`, fault-tolerance tests, and
  `benchmarks/frontend` sweeps.
