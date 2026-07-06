> For clean Markdown content of this page, append .md to this URL. For the complete documentation index, see https://docs.nvidia.com/dynamo/latest/llms.txt. For section-specific indexes, append /llms.txt to any section URL.

# Diffusion

## Overview

Dynamo supports serving diffusion models across multiple backends, enabling generation of images and video from text prompts. Backends expose diffusion capabilities through the same Dynamo pipeline infrastructure used for LLM inference, including frontend routing, scaling, and observability.

## Support Matrix

| Modality | vLLM-Omni | SGLang | TRT-LLM |
|----------|-----------|--------|---------|
| Text-to-Text | ❌ | ✅ | ❌ |
| Text-to-Image | ✅ | ✅ | ✅ |
| Text-to-Video | ✅ | ✅ | ✅ |
| Image-to-Video | ✅ | ❌ | ❌ |

**Status:** ✅ Supported | ❌ Not supported

## Backend Documentation

For deployment guides, configuration, and examples for each backend:

- **[vLLM-Omni](/dynamo/backends/v-llm/v-llm-omni)**
- **[SGLang Diffusion](/dynamo/backends/sg-lang/diffusion)**
- **[TRT-LLM Diffusion](/dynamo/backends/tensor-rt-llm/diffusion-experimental)**
- **[FastVideo (custom worker)](/dynamo/user-guides/diffusion/fastvideo)**