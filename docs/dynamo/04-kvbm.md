# KVBM — KV Block Manager (tiered KV cache)

Tiers: **G1** GPU HBM → **G2** pinned host DRAM → **G3** NVMe/SSD → **G4** object store (S3).
Tier markers in `kvbm-engine/src/lib.rs`; `LogicalLayoutHandle{G1..G4}` in `kvbm-common`.

## ⚠ Two implementations coexist

- **v1 (production, Python-facing)**: `lib/llm/src/block_manager/` (crate dynamo-llm). The PyO3
  bindings `lib/bindings/kvbm/` depend **only** on dynamo-llm + dynamo-runtime — this is what
  plugs into vLLM/TRT-LLM today.
- **v2 (rewrite)**: `lib/kvbm-{engine,logical,physical,consolidator,common,config,kernels}`.
  Internally complete (see `kvbm-logical/docs/advancements.md` for v1-vs-v2) but consumed only by
  `lib/mocker` so far; `kvbm-consolidator` also reachable via kv-router e2e tests.

Sections below describe **v2** unless noted. `SequenceHash = PositionalLineageHash` (128-bit,
dynamo-tokens) is the universal dedup key across registry, consolidator, and router projection.

## kvbm-engine — leader/worker split

Docs embedded: `docs/{architecture,leader,worker,offload,session,worker-group}.md`; crate
`CLAUDE.md`. `KvbmRuntime`/`Builder` bundles tokio + Velo messenger + NIXL agent + EventManager
(`from_env_leader`/`from_env_worker`).

- **Leader** (`src/leader/`) — owns metadata + placement, never touches data. `Leader` trait
  (`find_matches_with_options`); `InstanceLeader` holds `BlockRegistry`, `BlockManager<G2>`,
  optional `<G3>`, workers, `ParallelWorkers`, session maps, remote leaders, optional
  `ObjectBlockOps` (G4). Sessions (`leader/session/`): Initiator/Responder/ServerSession,
  state **Searching → Holding → Staging → Ready → Complete**; RAII `BlockHolder`.
  `leader/velo/` = RPC for remote leaders.
- **Worker** (`src/worker/`) — owns buffers + transfers. Traits `WorkerTransfers`
  (execute_local_transfer / execute_remote_{onboard,offload} / connect_remote) and
  `Worker: WorkerTransfers + ObjectBlockOps` (+ per-tier `LayoutHandle`s, export/import_metadata).
  `PhysicalWorker` (alias DirectWorker) owns a `kvbm_physical::TransferManager`;
  `CoordinatedWorker` wraps any Worker with leader coordination; `SpmdParallelWorkers`
  broadcasts ops to all ranks.
- Also: `collectives/` (NCCL; MLA pattern = only rank 0 holds G2/G3), `object/` (S3 +
  `ObjectLockManager` via conditional PUT), `pubsub/` (NATS + stub).

## kvbm-logical — lifecycle, pools, registry, eviction

Type-state RAII lifecycle (each transition consumes a guard; drop returns slot to correct pool):

```
MutableBlock (Reset) → CompleteBlock (Staged) → ImmutableBlock (Registered) → WeakBlock
```

- **Pools** (`pools/`): single-mutex `BlockStore<T>` = Reset (free FIFO) + Active + Inactive
  (evictable). Sync core, parking_lot, identity hash (`SeqHashMap`).
- **Inactive eviction backends** (`pools/inactive/backends/`): HashMap, LRU, MultiLru (4-tier
  frequency-aware), Lineage (parent-chain aware), FIFO.
- **Registry** (`registry/`): `BlockRegistry` — `SequenceHash → BlockRegistrationHandle` in a
  `PositionalRadixTree<Weak<...>>` (auto-cleaning); optional `FrequencyTracker` + EventsManager;
  typed attachments.
- **TinyLFU** (`tinylfu.rs`): Count-Min Sketch (4 hashes) + `FixedDecayPolicy`; feeds the
  offload `PresenceAndLFUFilter`.
- **Sequences** (`sequence/`, `integrations/`): `BlockSequence`, `SchedulableSequence`,
  `SequenceDelegate` — the scheduler-facing decode/apply API.
- **Events** (`events/`): `EventsManager` broadcast of `KvCacheEvent` — what the consolidator taps.

## kvbm-physical — layouts, transfer engine

- **Layouts** (`layout/`): trait `Layout` maps `(block, layer, outer) → MemoryRegion`.
  `FullyContiguousLayout` | `LayerSeparateLayout`; `PhysicalLayout` = layout + `StorageKind` +
  NIXL metadata; serializable (`LayoutDescriptor`) for cross-node reconstruction.
  `KvBlockLayout` enum (`layout/kv_block_layout.rs`) encodes dim permutations: `UniversalTP`
  `[nh,nl,no,nt,hd]`, `UniversalPP`, `OperationalHND`, `OperationalNHD` (vLLM common), Custom.
- **TransferManager** (`manager/`): registers layouts → `LayoutHandle(worker_id, layout_id)`,
  `export_metadata`/`import_metadata` (NIXL agent metadata + SerializedLayout),
  `execute_transfer(src, blocks, dst, blocks, opts)`. G4 offload paths still `todo!()` here.
- **Strategy** (`transfer/strategy.rs`): `select_strategy` by src/dst StorageKind:
  `Memcpy` | `CudaAsync{H2D,D2H,D2D}` | `Nixl{Read,Write}[Flipped]`; `TransferPlan::Direct` or
  `TwoHop{bounce: Pinned}` (work-stealing dual-task pump). Conservative defaults; opt-in
  `TransferCapabilities {allow_gds, allow_gpu_rdma}` unlock direct Disk↔Device / Device→Remote.
  Layout transform-on-transfer currently rejected; kernels in `kvbm-kernels`.

## kvbm-consolidator — cross-source dedup → one router stream

Consumes KV events from multiple sources → publishes one deduplicated kv-router-compatible
stream. Ingress: vLLM/TRT-LLM G1 events over **ZMQ SUB** + in-process KVBM G2/G3 via
EventsManager broadcast. Egress: ZMQ PUB in kv-router u64 wire format. Dedup key =
`SequenceHash` (PLH); `Tracker` maps external string hashes → canonical PLH (recomputed via
`dynamo_kv_hashing`, byte-identical to kvbm-logical registration). Rules: STORE on first source,
REMOVE on last drop. Egress projects PLH u128 → router u64 (`router_block_hash`).

## Config (kvbm-config)

`KvbmConfig` via figment: defaults → `/opt/dynamo/etc/kvbm.toml` → `$KVBM_CONFIG_PATH` →
`KVBM_*` env. Sub-configs: Tokio/Rayon/Messenger (discovery Etcd|Filesystem|P2p), Nixl
(`KVBM_NIXL_BACKENDS`), Cache (Host=G2, Disk=G3, `ParallelismMode{TensorParallel,ReplicatedData}`),
Offload (`TierOffloadConfig{policies: PassAll|Presence|PresenceLfu, min_lfu_count=8}`), Onboard,
Object (S3, G4).

## Offload pipelines (`kvbm-engine/src/offload/`)

Per tier-transition: **PolicyEvaluator → BatchCollector → TransferExecutor** (each cancellable).
`OffloadEngine` holds G1→G2, G2→G3, G2→G4 pipelines; enqueue returns a `TransferHandle`
(wait/cancel); `auto_chain` feeds G1→G2 completions into G2→G3. Policies: `PresenceFilter`,
`PresenceAndLFUFilter`, `ObjectPresenceFilter` (async S3), `ObjectLockPresenceFilter` (G2→G4
locking protocol), composites. `PendingTracker` prevents duplicate in-flight transfers.
Governance rules in `offload/AGENTS.md` (P1–P6).

## lib/memory (dynamo-memory) — NIXL wrapper

`MemoryDescriptor` trait; `StorageKind {System, Pinned, Device(u32), Disk(u64)}`; storages
System/Pinned/Device/Disk(mmap)/External; `ArenaAllocator`, `CudaMemPool`; NUMA-aware placement
(`numa/`). NIXL (`nixl.rs`, wraps `nixl-sys = "=1.0.1"`): `NixlAgent`
(register_memory/get_local_md/load_remote_md), `NixlRegistered<S>` RAII
(deregister-before-free), `RegisteredView` exported in SerializedLayout for remote RDMA.

## gpu_memory_service (GMS) — cross-process GPU memory (pure Python)

Out-of-process GPU memory manager (one server per GPU): decouples memory *ownership* from user
processes → zero-copy weight sharing, weights survive crashes, fast warm-start. Server allocates
via CUDA VMM `cuMemCreate` + exports FDs, **never maps** (no CUDA context). Clients import FDs,
reserve VA, map; VA-stable `unmap_all_vas`/`remap_all_vas` keeps torch pointers valid.
**Socket-as-lock** FSM: `EMPTY → RW → COMMITTED → RO`; crash = socket close = release. Wire:
msgpack + SCM_RIGHTS. Snapshot backends (pinned host / sharded SSD / NIXL-GDS). vLLM/SGLang
integrations via `--load-format gms`; two tags per GPU: `weights` (RO after commit) and
`kv_cache` (RW). Orthogonal to KVBM tiering. `pip install -e lib/gpu_memory_service`.

## vLLM plug-in path

- **PD coordination** (`components/src/dynamo/vllm/kv_connector_protocols.py`):
  `NixlConnectorProtocol` (pull) | `MooncakeConnectorProtocol` (push); `PdConnector` subclasses
  vLLM MultiConnector — exactly one PD-capable sub-connector; KVBM's `DynamoConnector` rides
  along save-only.
- **KVBM connector** (`lib/bindings/kvbm/`, PyO3 `dynamo-kvbm-bindings`, abi3-py310):
  `DynamoConnector(KVConnectorBase_V1)` splits SCHEDULER→`KvConnectorLeader`,
  WORKER→`KvConnectorWorker` (`python/kvbm/vllm_integration/connector/`). Rust side
  `src/block_manager/vllm/connector.rs` (SchedulerOutput, ConnectorMetadata) wires to **v1**
  `dynamo_llm::block_manager` + distributed `KvbmLeader`/`KvbmWorker`. TRT-LLM mirror in
  `trtllm_integration/`. Consolidator mode default `Dedup` (v1's in-tree consolidator).
- Tests: `tests/kvbm_integration/` (vllm integration, consolidator e2e, determinism agg/disagg,
  chunked prefill, cuda graph).
