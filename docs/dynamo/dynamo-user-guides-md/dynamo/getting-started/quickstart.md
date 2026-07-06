> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# Quickstart

<p align="left">
  <a href="./quickstart.zh-CN.mdx" hreflang="zh-CN">
    <img src="/dynamo/_files/dynamo.docs.buildwithfern.com/2546607964ca3bb29badfbef8f4af73dee49dd6709242f791dfa79f7914b8f2e/pages-v1.2.1/assets/img/readme-zh-cn-link.svg" alt="简体中文" height="28" />
  </a>
</p>

## Choose Your Path

You're here. Container fast path.

Full walkthrough — PyPI, configuration.

Kubernetes-native production path.

For contributors against `main`.

Dynamo is backend-agnostic and Kubernetes-native without being Kubernetes-only. Use this container path to try the same frontend/router/worker stack locally; use the Kubernetes path when you want the operator, CRDs, Gateway API integration, autoscaling, scheduling, and cluster lifecycle management.

## Pull a Container

Containers have all dependencies pre-installed. Pick your backend:

```bash
docker run --gpus all --network host --rm -it nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.2.0
```

```bash
docker run --gpus all --network host --rm -it nvcr.io/nvidia/ai-dynamo/tensorrtllm-runtime:1.2.0
```

```bash
docker run --gpus all --network host --rm -it nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.2.0
```

**Hugging Face token required for gated models.** Llama, Kimi, Qwen-VL, and other gated models require `HF_TOKEN` in your environment and accepting the model card's license on huggingface.co. Set `export HF_TOKEN=hf_…` before launching.

For container versions and tags, see [Release Artifacts](/dynamo/resources/release-artifacts#container-images).

## Start the Frontend

In your container, start the OpenAI-compatible frontend on port 8000:

```bash
python3 -m dynamo.frontend --discovery-backend file
```

`--discovery-backend file` avoids needing etcd. To run frontend and worker in the same terminal, background each command with `> logfile.log 2>&1 &`.

## Start a Worker

In another terminal, launch a worker for your backend:

```bash
python3 -m dynamo.sglang --model-path Qwen/Qwen3-0.6B --discovery-backend file
```

```bash
python3 -m dynamo.trtllm --model-path Qwen/Qwen3-0.6B --discovery-backend file
```

```bash
python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B --discovery-backend file \
  --kv-events-config '{"enable_kv_cache_events": false}'
```

## Verify and Test

Check the endpoint is up:

```bash
curl -sf http://localhost:8000/health && echo OK
```

If you see `OK`, send a chat completion:

```bash title="Request"
curl localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B",
       "messages": [{"role": "user", "content": "Hello!"}],
       "max_tokens": 50}'
```

```json title="Response"
{
  "id": "chatcmpl-...",
  "model": "Qwen/Qwen3-0.6B",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello! How can I help you today?"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 9, "completion_tokens": 10, "total_tokens": 19}
}
```

Connection refused? The frontend takes a few seconds to start — retry. For production liveness and readiness probes, see [Health Checks](/dynamo/user-guides/observability-local/health-checks).

## From the Digest

How Dynamo optimizes for agentic workloads at three layers: the frontend API, the router, and KV cache management.

How Dynamo's concurrent global index evolved through six iterations to sustain over 100M ops/sec.

## Dive Deeper

Pick a full install path from the [four options above](#choose-your-path), or explore how Dynamo works under the hood:

How the frontend, router, and workers fit together.

Worker discovery, multi-model routing, OpenAI compat.

How the router places requests for prefix reuse.

Liveness and readiness probes for production deployments.