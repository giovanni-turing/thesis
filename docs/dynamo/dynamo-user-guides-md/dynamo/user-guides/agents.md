> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# Agents

Dynamo provides a small set of request extensions and trace utilities for
serving agentic workloads. The harness remains responsible for the semantic
agent trajectory. Dynamo receives lightweight metadata and uses it for serving
telemetry, routing hints, and backend-specific cache behavior.

## Core Concepts

| Concept | Purpose |
|---------|---------|
| [Agent Tracing](/dynamo/user-guides/agents/agent-tracing) | Passive `session_id`/`trajectory_id` metadata plus Dynamo-owned request timing, token, cache, worker-placement, and harness tool-event traces. |
| [Agent Hints](/dynamo/user-guides/agents/agent-hints) | Optional per-request hints such as priority, expected output length, and speculative prefill. |
| [Priority Scheduling](/dynamo/user-guides/agents/priority-scheduling) | Request priority semantics across the router queue, backend engines, and cache policy. |
| [Use Pi-Mono with Dynamo](/dynamo/user-guides/agents/use-pi-mono-with-dynamo) | End-to-end quickstart that drives the Pi coding agent through Dynamo with agent context and tool tracing turned on. |
| [ThunderAgent Program Scheduler](/dynamo/user-guides/agents/thunder-agent-program-scheduler) | Experimental program-level scheduler with tool-boundary pause/resume on top of KV-aware routing: the 5s scheduler tick, the utilization-driven control loop and its knobs, and scheduler observability. |
| [Tool Calling](/dynamo/user-guides/parsing/tool-call-parsing-dynamo) | Supported tool-call parsers and parser names, plus engine-fallback configurations. |
| [Reasoning](/dynamo/user-guides/parsing/reasoning-parsing-dynamo) | Supported reasoning parsers for chain-of-thought models, plus engine-fallback configurations. |

## Backend-Specific Guides

Agent features are exposed through common request metadata, but backend support
varies by runtime.

| Backend Guide | Contents |
|---------------|----------|
| [SGLang for Agentic Workloads](/dynamo/backends/sg-lang/agentic-workloads) | Priority scheduling, priority-based radix eviction, speculative prefill, and streaming session control for subagent KV isolation. |

## Request Surface

Agent-facing request metadata lives under `nvext` on OpenAI-compatible request
bodies:

```json
{
    "nvext": {
        "agent_context": {
            "session_type_id": "deep_research",
            "session_id": "research-run-42",
            "trajectory_id": "research-run-42:researcher"
        },
        "agent_hints": {
            "priority": 5,
            "osl": 1024
        }
    }
}
```

Use `agent_context` when you want traceability across LLM calls, tool calls, and
external trajectory files. Use `agent_hints` only when the harness has
serving-relevant intent that Dynamo can act on.