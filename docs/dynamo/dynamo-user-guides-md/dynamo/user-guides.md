> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# Feature Guides

Use these guides after you have Dynamo running and want to improve serving behavior, operate a deployment, or adapt Dynamo to a new workload.

## Recommended path

Most deployments start with the core performance loop:

| Step | Guide | Use when |
|---|---|---|
| 1 | [KV Cache Aware Routing](/dynamo/user-guides/kv-cache-aware-routing) | Route requests to workers that already hold useful KV cache. |
| 2 | [Disaggregated Serving](/dynamo/user-guides/disaggregated-serving) | Scale prefill and decode workers independently. |
| 3 | [KV Cache Offloading](/dynamo/user-guides/kv-cache-offloading) | Extend usable cache capacity beyond GPU memory. |
| 4 | [Benchmarking](/dynamo/user-guides/benchmarking) | Compare configurations before you move to production. |

## Where to go next

| Goal | Start with |
|---|---|
| Make serving more resilient | [Fault Tolerance](/dynamo/user-guides/fault-tolerance) |
| Monitor local deployments | [Observability (Local)](/dynamo/user-guides/observability-local) |
| Reproduce traffic without a full engine | [Mocker Engine Simulation](../mocker/mocker.md) |
| Add structured model outputs | [Tool Calling](/dynamo/user-guides/parsing/tool-call-parsing-dynamo) and [Reasoning](/dynamo/user-guides/parsing/reasoning-parsing-dynamo) |
| Build agent workloads | [Agents](/dynamo/user-guides/agents) |
| Serve specialized workloads | [LoRA Adapters](/dynamo/user-guides/lo-ra-adapters), [Multimodal](/dynamo/user-guides/multimodal), and [Diffusion](/dynamo/user-guides/diffusion) |

For cluster deployments, pair these guides with the [Kubernetes Deployment](/dynamo/kubernetes-deployment/start-here/kubernetes-quickstart) docs. The same features can be explored locally, then expressed through Dynamo's Kubernetes-native CRDs and operator when you move to a shared GPU cluster.