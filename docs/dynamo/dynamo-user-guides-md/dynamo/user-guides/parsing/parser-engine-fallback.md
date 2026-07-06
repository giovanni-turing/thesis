> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# Parser Engine Fallback

When Dynamo's registry does not list a tool-call or reasoning parser for your model, fall back to the upstream engine's parser via a **chat-processor swap**, which keeps frontend tokenization and KV routing.

For the Dynamo-native default path, see [Tool Call Parsing (Dynamo)](/dynamo/user-guides/parsing/tool-call-parsing-dynamo) and [Reasoning Parsing (Dynamo)](/dynamo/user-guides/parsing/reasoning-parsing-dynamo).

<Info>
How `--dyn-chat-processor` combines with the parser flags — and which combinations are invalid (engine fallback supports disaggregated serving on vLLM and SGLang; TRT-LLM engine fallback is a work in progress) — is documented once in [Parser Configuration](/dynamo/user-guides/parsing/parser-configuration). Read that first; this page covers only the engine-fallback specifics.
</Info>

## Configuration

Engine fallback runs parsing in the engine's own Python frontend. Select it with `--dyn-chat-processor vllm` or `sglang`, then name the parser with the engine's **frontend** flags:

- `--tool-call-parser <name>` — the engine's tool-call parser
- `--reasoning-parser <name>` — the engine's reasoning parser

These are distinct from the Dynamo-native `--dyn-tool-call-parser` / `--dyn-reasoning-parser` (which go on the worker). The accepted names come from the engine's registry and may differ from Dynamo's — e.g. vLLM `nemotron_v3` vs Dynamo `nemotron3`, SGLang `deepseekv3` vs Dynamo `deepseek_v3`.

## Examples

```bash
# vLLM chat processor — frontend carries the parser flags, then launch the worker:
python -m dynamo.frontend --dyn-chat-processor vllm   --tool-call-parser hermes --reasoning-parser qwen3
python -m dynamo.vllm   --model Qwen/Qwen3-0.6B

# SGLang chat processor
python -m dynamo.frontend --dyn-chat-processor sglang --tool-call-parser qwen25 --reasoning-parser qwen3
python -m dynamo.sglang --model Qwen/Qwen3-0.6B
```

<Tip>
If a tool call or reasoning split comes back wrong, add `"logprobs": true` to a single repro request and share the response. See [Troubleshooting Tool Calls](/dynamo/user-guides/parsing/troubleshooting-tool-calls) for what to capture.
</Tip>

## See Also

- [Parser Configuration](/dynamo/user-guides/parsing/parser-configuration) -- how the chat-processor and parser flags combine, and which combinations are invalid (start here)
- [Tool Call Parsing (Dynamo)](/dynamo/user-guides/parsing/tool-call-parsing-dynamo) -- Dynamo-native tool-call parser names
- [Reasoning Parsing (Dynamo)](/dynamo/user-guides/parsing/reasoning-parsing-dynamo) -- Dynamo-native reasoning parser names
- [vLLM Chat Processor](/dynamo/backends/v-llm/frontend-processor-fallback) -- vLLM chat-processor details
- [SGLang Chat Processor](/dynamo/backends/sg-lang/frontend-processor-fallback) -- SGLang chat-processor details
- [Frontend Configuration Reference](/dynamo/components/frontend/configuration-reference) -- Full CLI flag reference