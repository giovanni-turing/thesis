# KV-Aware Routing — kv-hashing, kv-router, llm/kv_router

## Crate map

- `lib/tokens` (dynamo-tokens) — **owns `PositionalLineageHash` (PLH)**, block formation, salted
  chain (`lib/tokens/src/lib.rs:537-688`).
- `lib/kv-hashing` (dynamo-kv-hashing) — thin `Request → Vec<PositionalLineageHash>` contract
  wrapping dynamo-tokens (`request.rs`, `compute.rs`, `block.rs` `UniversalBlock`, `salt.rs`).
- `lib/kv-router` (dynamo-kv-router) — transport-agnostic routing engine: `indexer/`,
  `scheduling/`, `sequences/`, `zmq_wire/`, `recovery/`, `protocols.rs`.
- `lib/llm/src/kv_router/` — wiring to the runtime (NATS/ZMQ/discovery/PyO3): `publisher/`,
  `indexer/` (+recovery), `scheduler.rs`, `push_router.rs`, `sequence.rs`, `prefill_router/`.
- `components/src/dynamo/router/` — standalone Python KV router; mode selection for the frontend
  lives in `components/src/dynamo/frontend/main.py:216`.

**⚠ Dual-track hashes.** Production radix tree keys on `LocalBlockHash(u64)` (content hash, the
radix edge key) + `ExternalSequenceBlockHash(u64)` (parent-chained, used for removal). The
128-bit PLH is the future universal key — router migration is unexecuted "Phase C"
(`lib/kv-hashing/README.md`). PLH *is* live in KVBM v2 + consolidator (see 04).

## PLH (PositionalLineageHash)

`u128` packed `[mode(2) | position | current_seq(64) | parent_fragment]`; mode auto-widens the
position field (8/16/24-bit; panics ≥2^24). Key methods: `root(block_hash)`,
`extend(child_block_hash)` (chain step: `child_seq = xxh3([parent_seq, child_bh], seed 1337)`),
`current_sequence_hash()`, `parent_fragment_for_child_position()`. Self-extending: child PLH
derivable from parent PLH + child BlockHash, no side table.

Block hashing: XXH3 over packed per-slot bytes, seeded by `SaltHash`
(`= 1337 [+ xxh3(lora_name)] [+ hash(salt)]` — byte-identical to the router's
`compute_block_hash_for_seq` on the no-salt path, asserted). Zero-MM block: 4 B/slot (u32 LE
token). MM-affected block: 13-B frames (`tag|token|0` or `tag|run_offset|mm_hash`) — widths
guarantee no MM/non-MM collision. Only complete windows hashed; trailing partial block dropped.

## Indexer (`lib/kv-router/src/indexer/`)

Interchangeable implementations behind `traits.rs::KvIndexerInterface`: `radix_tree.rs`
(single-threaded compressed radix tree), `concurrent_radix_tree*.rs`, `kv_indexer.rs`
(tokio event loop owning a RadixTree, drains mpsc channels), `thread_pool.rs` (sharded),
`positional.rs`/`pruning.rs` (approximate, TTL), `lower_tier*.rs` (host/disk tiers).

RadixTree internals: `RadixBlock {state: NodeState, children: FxHashMap<LocalBlockHash, ...>}`
with compressed edges; per-worker coverage (`full_edge_workers`, `worker_cutoffs`); secondary
`lookup: worker → ExternalSequenceBlockHash → node` for O(1) removal.
- Insert `apply_stored` (:227): walk from parent, edge compression (leaf extend / split / reuse).
- Remove `apply_removed` (:541) via secondary lookup; `Cleared` wipes a worker.
- Query `find_match_details` (:89): walk query hashes, accumulate `OverlapScores {worker → depth}`.

**Approx "predict-on-route" side indexer** (`lib/llm/.../indexer/side.rs`,
`router_predicted_ttl_secs`): records the router's *own* decisions with TTL, because
vLLM/SGLang salt their hashes cryptographically — the router can't reproduce them, and writing
router-computed hashes into the primary would double-key blocks. Query takes per-worker max of
primary + approx.

## Scheduling / cost function (`lib/kv-router/src/scheduling/selector.rs:110`)

**Lower logit wins**:

```
logit = prefill_load_scale * max(raw_prefill_blocks − overlap_credit_blocks, 0)
      + potential_decode_blocks
overlap_credit = overlap_score_credit * decay * device_overlap
              + host_cache_hit_weight * host_overlap
              + disk_cache_hit_weight * disk_overlap
              + shared_cache_multiplier * shared_beyond_device
decay = 1/(1 + overlap_score_credit_decay * normalized_excess_prefill_load)
```

Selection: T=0 → argmin (reservoir tie-break); T>0 → `softmax_sample` (:29). Defaults
(`config.rs:591`): credit 1.0, decay 0.0, prefill_scale 1.0, host 0.75, disk 0.25, shared 0.0,
temperature 0.0. Deprecated `overlap_score_weight` auto-migrates. LoRA narrowing via
`narrow_allowed_by_lora`; `RoutingEligibility` filters (pinned/allowed/overloaded).

## Active sequences (`lib/kv-router/src/sequences/`, strict write-DAG per its README)

`ActiveSequences` (`single.rs`) = authoritative per-worker write state → projected into
`PromptRegistry` (derived, eventually-consistent read model feeding the scheduler).
`ActiveSequencesMultiWorker` (`multi_worker.rs`, holds `router_id`) orchestrates; canonical
projection `potential_blocks_and_tokens_at(...)`. `active_set.rs::reconcile_active_workers`
prunes state on topology change.

## KV events

**Shape** (`protocols.rs`): `RouterEvent {worker_id, storage_tier, event: KvCacheEvent}`;
`KvCacheEventData = Stored(KvCacheStoreData{parent_hash, blocks}) | Removed | Cleared`;
`KvCacheStoredBlockData {block_hash: ExternalSequenceBlockHash, tokens_hash: LocalBlockHash,
mm_extra_info}` (the dual hash). `StorageTier = Device|HostPinned|Disk|External`.
Subject `KV_EVENT_SUBJECT = "kv-events"`.

**Flow**: engine → (ZMQ PUB msgpack, decoded by `zmq_wire/` mirroring vLLM's msgspec structs) →
worker's `KvEventPublisher` (`lib/llm/src/kv_router/publisher/`: zmq_listener → event_processor →
batching → dedup (per-rank/tier refcounts) → sinks) → **event plane** (NATS core or ZMQ; default)
or deprecated NATS JetStream (`durable_kv_events`) → router `Indexer` subscriber → radix tree
(GPU tier → primary; other tiers → lower-tier indexers).

## Router modes & flags

`RouterMode` (runtime `push_router.rs:175`): RoundRobin (default) | Random | PowerOfTwoChoices |
KV | Direct | LeastLoaded | DeviceAwareWeighted. Frontend maps `--router-mode` string in
`frontend/main.py:216`. The standalone `python -m dynamo.router` is always KV.

Flags (in `components/src/dynamo/common/configuration/groups/kv_router_args.py`; envs
`DYN_ROUTER_*`): `--router-kv-overlap-score-credit[-decay]`, `--router-prefill-load-scale`,
`--router-{host,disk}-cache-hit-weight`, `--router-temperature`, `--router-kv-events`,
`--router-replica-sync`, `--load-aware` preset (credit=0, no KV events → pure load balance).
Standalone router extras: `--endpoint ns.comp.ep`, `--router-block-size` (128),
`--serve-indexer` xor `--use-remote-indexer`.

## Multi-router coordination & recovery

- **Replica sync** (`router_replica_sync`): replicas each rebuild their own radix tree from the
  same event stream; what fans out over NATS is **active-sequence booking**
  (`ACTIVE_SEQUENCES_SUBJECT="active_sequences_events"`, `PREFILL_SUBJECT="prefill_events"`;
  `sequences/replica_sync.rs`, batched 256/1ms, advisory). Decode-time output-block growth is
  deliberately NOT synced (too high-frequency).
- **Restart recovery** (`lib/llm/.../indexer/recovery/`): default event-plane mode — subscribe
  first, then `WorkerQueryClient` dumps each worker's LocalKvIndexer ring buffer (1024 events)
  into the fresh tree; gap detection via `recovery/cursor.rs` `CursorState`. JetStream mode
  (deprecated) — radix snapshot in NATS object store (`radix-bucket/radix-state`) + backlog
  replay; periodic `purge_then_snapshot`.

## End-to-end (KV mode)

tokenize → `compute_block_hash_for_seq(tokens, block_size, {mm, lora, eagle})` →
`query_tiered_matches` (primary + approx + lower tiers + shared cache, parallel) →
`OverlapSignals` → `scheduler.schedule_request` → `worker_logit` argmin/softmax →
`WorkerSelectionResult {worker, overlap_blocks, cached_tokens}` → book state
(`ActiveSequences` + replica publish + predict-on-route) → `KvPushRouter` dispatches → on
completion `mark_prefill_completed` / `free`. Entry: `lib/llm/src/kv_router.rs::KvRouter::
find_best_match_details_with_policy_class` (:502).
