# Phase 3 preflight — rtx_5090 / vllm / encoder_attention

## Registry route
- op `encoder_attention` -> `collector.vllm.collect_attn_encoder`
  (get_encoder_attention_test_cases / run_encoder_attention_torch),
  perf file ENCODER_ATTENTION. Single module, no VersionRoute list.

## Version compatibility
- Module `__compat__ = "vllm>=0.21.0"`.
- framework_manifest.yaml still pins vllm 0.19.0 (stale relative to this module).
- Local image qwen3-vl-embed has vllm 0.20.0 -> INCOMPATIBLE, rejected.
- DECISION: collect under vllm 0.22.0 (matches decoder-side h100_sxm+vllm 0.22.0
  support-matrix tuple chosen for the thesis; keeps one backend version end to end).

## Kernel dispatch on SM 120
- Collector delegates to vLLM's `get_vit_attn_backend(head_size, dtype)` — the same
  selector MMEncoderAttention uses. Whatever backend vLLM picks on RTX 5090
  (FLASH_ATTN / TRITON_ATTN / TORCH_SDPA) is what gets measured -> measured kernel
  == production kernel by construction. FlashInfer path raises NotImplementedError.
- bf16 only (fp8 ViT FMHA via FLASHINFER explicitly deferred upstream).

## Remaining preflight checks (inside container, before burning GPU-hours)
- [ ] record importlib.metadata.version("vllm") inside container
- [ ] run get_vit_attn_backend on the 5090, record which backend SM 120 selects
- [ ] smoke: python collector/collect.py --backend vllm --ops encoder_attention --smoke

## Container preflight results (2026-07-05)
- image vllm/vllm-openai:v0.22.0 -> vllm 0.22.0, torch 2.11.0+cu130
- GPU visible: NVIDIA GeForce RTX 5090, CC (12,0)
- get_vit_attn_backend(head_size=72, bf16) -> **FLASH_ATTN** (also for head_size=64)
  -> SM 120 uses vLLM's FlashAttention ViT path in 0.22.0, NOT the Triton fallback
  (older sglang collector docstring's SM dispatch is outdated for vllm 0.22).
