# `lib/runtime` (dynamo-runtime) — Distributed Runtime

The foundation crate: object model, discovery, transports, pipeline graph, health, metrics.
Module tree in `src/lib.rs`. Edition 2024.

## Object model

Nesting: **DistributedRuntime → Namespace → Component → Endpoint**; `Client` = remote-call handle;
`Instance` = a registered worker for an endpoint.

- **`Runtime`** (`src/runtime.rs`) — local base. Two tokio pools (`primary` app,
  `secondary` background etcd/NATS), `cancellation_token`, `endpoint_shutdown_token` (cancelled
  *first* on graceful shutdown), `GracefulShutdownTracker`. `Worker` (`src/worker.rs`) wraps a
  process-global runtime and blocks in `execute`.
- **`DistributedRuntime`** (`src/distributed.rs`) — `Clone` (Arc-shared). Fields worth knowing:
  `nats_client: Option<...>`, `network_manager: Arc<NetworkManager>`, lazy `tcp_server`,
  `request_plane: RequestPlaneMode` (**Tcp default** | Nats), `discovery_client: Arc<dyn Discovery>`,
  `component_registry`, `endpoint_discovery_sources` (dedups watchers per endpoint),
  `routing_occupancy_states` (in-flight counters for load-aware routing), `system_health`,
  `local_endpoint_registry` (in-process calls bypass network), `metrics_registry`,
  `engine_routes`. Construction: `new(runtime, DistributedConfig)` / `from_settings` (env
  `DYN_DISCOVERY_BACKEND` default "etcd", `DYN_REQUEST_PLANE`, `DYN_EVENT_PLANE`) /
  `process_local()` (memory discovery, no NATS — single-process frontend+backend).
  `DiscoveryBackend` = `Kubernetes | KvStore(kv::Selector)`. Event plane default is **ZMQ**.
- **`Namespace` / `Component` / `Endpoint` / `Instance`** — all actually defined in
  `src/component.rs` (the `component/component.rs` and `component/namespace.rs` submodules are
  near-empty notes). Names validated `^[a-z0-9-_]+$`; `Component::service_name()` =
  `Slug("{ns}_{name}")`. `Instance { component, endpoint, namespace, instance_id: u64,
  transport: TransportType, device_type }`. `TransportType::Nats(subject) |
  Tcp("host:port/{id:x}/{endpoint}")`. `DeviceType::Cpu|Cuda` (from CUDA_VISIBLE_DEVICES; used by
  device-aware routing).

### Endpoint serving lifecycle (`src/component/endpoint.rs`)

`endpoint.endpoint_builder().handler(Arc<dyn PushWorkHandler>).health_check_payload(v).start()`:
registers with the `RequestPlaneServer` (shared TCP server or NATS PushEndpoint), then writes the
`Instance` into discovery (`DiscoverySpec::Endpoint`). Cleanup task awaits
`endpoint_shutdown_token`, unregisters. `register_endpoint_instance()` /
`unregister_endpoint_instance()` support sleep/wake (join/leave routing pool).

## Discovery (`src/discovery/`)

- **`Discovery` trait** (`mod.rs`): `instance_id()`, `register`/`unregister`, `list`,
  `list_and_watch -> DiscoveryStream` (of `DiscoveryEvent::Added(DiscoveryInstance) |
  Removed(id)`), plus session-affinity claims (`create_or_get_claim`, `close_claim`,
  `subscribe_claim_events`). Default `register` rejects a second model on an occupied endpoint.
- **Data model**: `DiscoverySpec::{Endpoint, Model{card_json, model_suffix}, EventChannel}`;
  `DiscoveryQuery::{AllEndpoints, NamespacedEndpoints, ComponentEndpoints, Endpoint, *Models,
  EventChannels}`. Paths: `ns/comp/ep/{id:x}`.
- **`KVStoreDiscovery`** (`kv_store.rs`) — buckets `v1/instances`, `v1/mdc` (models),
  `v1/event_channels`, `v1/claims`. Backends via `src/storage/kv.rs`: `Selector::Etcd|File|Memory`
  (+ NATS JetStream KV). `KubeDiscoveryClient` (`kube.rs`) is the K8s-native backend.
- **etcd leases** (`src/transports/etcd.rs`, `etcd/lease.rs`): primary lease TTL keep-alive is
  *tied to the Runtime* — lease expiry shuts the runtime down; runtime cancel revokes the lease.
  All KV ops attach the lease by default → registrations auto-expire on worker death.
  `instance_id` = etcd lease id (or generated for file/memory).

## Transports (`src/transports/`)

- **NATS** (`nats.rs`) — request/reply RPC (subject `"{ns}_{comp}.{ep}-{id:x}"`), NATS services
  (`$SRV.STATS` scrape), JetStream (object store, `NatsQueue` durable work queue). Env
  `NATS_SERVER`, `DYN_NATS_REQUEST_TIMEOUT_SECS`.
- **TCP** (`tcp.rs` → `pipeline/network/tcp/`) — the default request plane + response streams.
  Env `DYN_TCP_RPC_PORT`, `DYN_TCP_RESPONSE_STREAM_PORT/_HOST`, `DYN_TCP_MAX_MESSAGE_SIZE`
  (32 MiB default). Length-prefixed framing (`pipeline/network/codec/`).
- **ZMQ** (`zmq.rs`, via tmq) — event plane default; ROUTER/DEALER.
- **Event plane** (`event_plane/`) — pub/sub over NATS-core or ZMQ: `EventPublisher` /
  `EventSubscriber` `for_component(comp, topic)` / `for_namespace(ns, topic)`; publishers
  register as `DiscoverySpec::EventChannel`. Codec = msgpack (`codec.rs`), framing `frame.rs`.

## Pipeline system (`src/pipeline/`)

Typed graph of `AsyncEngine`s: `SingleIn<T> = Context<T>` (unary in), `ManyOut<T> = EngineStream<T>`
(streaming out); `Context` carries request id/metadata/cancellation through every stage.

- **Nodes** (`nodes.rs`): `Source::link(sink)`; `Operator<UpIn,UpOut,DownIn,DownOut>` transforms
  **both** forward (request) and backward (response) paths — wrapped by `PipelineOperator` with
  `forward_edge()`/`backward_edge()`. `ServiceFrontend` (graph start) / `ServiceBackend`
  (graph end; `from_engine` adapts a plain engine). `SegmentSource/Sink` = segment boundaries.
- **Network boundary** (`network.rs`): **`Ingress`** (server; `Ingress::for_engine(engine)`,
  implements `PushWorkHandler::handle_payload`) and **`Egress`** (client). Wire types:
  `RequestControlMessage`, `ResponseStreamPrologue`, `NetworkStreamWrapper{data, complete_final}`.
- **`PushRouter<T,U>`** (`network/egress/push_router.rs`) — client-side router.
  **`RouterMode`: RoundRobin (default) | Random | PowerOfTwoChoices | KV | Direct | LeastLoaded |
  DeviceAwareWeighted** (enum at push_router.rs:175). Load-aware modes consult
  `RoutingOccupancyState` (OccupancyPermit RAII). `AddressedPushRouter` resolves the instance's
  `TransportType` and dispatches via the unified `RequestPlaneClient` (tcp_client/nats_client).
- **Serving side** (`network/ingress/`): `RequestPlaneServer` trait; `SharedTcpServer` (one
  process-shared server, many endpoints) or NATS `PushEndpoint` (acks, spawns handler per
  request, drains in-flight on shutdown). `NetworkManager` (`network/manager.rs`) selects and
  caches server/clients.

## Health & metrics

- **`SystemHealth`** (`src/system_health.rs`): endpoint health map + health-check targets;
  env `DYN_SYSTEM_STARTING_HEALTH_STATUS`, `DYN_SYSTEM_USE_ENDPOINT_HEALTH_STATUS`.
  **`HealthCheckManager`** (`src/health_check.rs`): after `canary_wait_time` idle, sends the
  endpoint's `health_check_payload` as a canary through the local engine; live traffic resets.
- **Metrics** (`src/metrics.rs`): `MetricsHierarchy` trait on DRT/Namespace/Component/Endpoint →
  hierarchical Prometheus names (`metrics/prometheus_names.rs` — Python names **generated** from
  this file by `lib/bindings/python/codegen`). `MetricsRegistry` supports child registries +
  pre-scrape update callbacks.
- **System status server** (`src/system_status_server.rs`): axum on `DYN_SYSTEM_PORT` — `/health`,
  `/live`, `/metrics` (combined scrape), `/metadata`, `/engine/{*path}` (engine-route registry),
  `/v1/metadata/...` (self-hosted MDC files), `/v1/loras` (if `DYN_LORA_ENABLED`).

## Client lifecycle (calling side)

`endpoint.client()` → `Client::new` → dedup'd `EndpointDiscoverySource` runs
`list_and_watch(DiscoveryQuery::Endpoint)` on the secondary runtime, maintaining
`watch::Receiver<Vec<Instance>>`. `Client` exposes `instances()`, `wait_for_instances()`,
`report_instance_down`, overload tracking, `RoutingInstancesState` (discovered/routable/overloaded
sets). Then `PushRouter::from_client(client, mode)` picks per request.

## File map

| Concern | Files |
| --- | --- |
| Object model | `src/{lib,distributed,component,runtime,worker,traits}.rs`, `src/component/{client,endpoint,registry,service}.rs` |
| Discovery | `src/discovery/{mod,kv_store,kube,metadata}.rs`, `src/storage/kv.rs` + `storage/kv/{etcd,file,mem,nats}.rs` |
| Transports | `src/transports/{nats,tcp,zmq,etcd}.rs`, `src/transports/etcd/{lease,lock,kv}.rs`, `src/transports/event_plane/*` |
| Pipeline | `src/pipeline.rs`, `src/pipeline/{context,nodes}.rs`, `src/pipeline/network/{manager}.rs`, `.../egress/{push_router,addressed_router,unified_client}.rs`, `.../ingress/{unified_server,shared_tcp_endpoint,nats_server,push_endpoint,push_handler}.rs` |
| Health/metrics | `src/{health_check,system_health,system_status_server,metrics}.rs`, `src/metrics/*` |
