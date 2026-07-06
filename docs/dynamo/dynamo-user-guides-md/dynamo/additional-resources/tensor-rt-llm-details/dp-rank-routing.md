> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# DP Rank Routing (Attention Data Parallelism)

For general TensorRT-LLM features and configuration, see the [Reference Guide](/dynamo/backends/tensor-rt-llm/reference-guide).

---

TensorRT-LLM supports [attention data parallelism](https://lmsys.org/blog/2024-12-04-sglang-v0-4/#data-parallelism-attention-for-deepseek-models) (attention DP) for models like DeepSeek. When enabled, multiple attention DP ranks run within a single worker, each with its own KV cache. Dynamo can route requests to specific DP ranks based on KV cache state.

### Dynamo vs TRT-LLM Internal Routing

- **Dynamo DP Rank Routing**: The router selects the optimal DP rank based on KV cache overlap and instructs TRT-LLM to use that rank with strict routing (`attention_dp_relax=False`). Use this with `--router-mode kv` for cache-aware routing.
- **TRT-LLM Internal Routing**: TRT-LLM's scheduler assigns DP ranks internally. Use this with `--router-mode round-robin` or `random` when KV-aware routing isn't needed.

### Enabling DP Rank Routing

```bash
# Worker with attention DP
# (TP=2 acts as the "world size", in effect creating 2 attention DP ranks)
CUDA_VISIBLE_DEVICES=0,1 python3 -m dynamo.trtllm \
  --model-path <MODEL_PATH> \
  --tensor-parallel-size 2 \
  --enable-attention-dp \
  --publish-events-and-metrics

# Frontend with KV routing
python3 -m dynamo.frontend --router-mode kv
```

The `--enable-attention-dp` flag sets `attention_dp_size = tensor_parallel_size` and configures Dynamo to publish KV events per DP rank. The router automatically creates routing targets for each `(worker_id, dp_rank)` combination.

<Note>
Attention DP requires TRT-LLM's PyTorch backend. AutoDeploy does not support attention DP.
</Note>