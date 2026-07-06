# RTX 5090 AIC Onboarding — Progress

Goal: onboard `rtx_5090` as an aiconfigurator system and collect `encoder_attention`
(ViT) perf data, feeding the thesis's heterogeneous disaggregated VLM simulation:
**encoder pool = rtx_5090 (own silicon, own data) · decoder pool = h100_sxm + vllm 0.22.0
(shipped data) · model = Qwen3-VL family (ViT identical across 8B/32B/235B)**.

Workflow: `aic-auto-collect` skill phases. Audit artifacts per phase under
`/home/gio/tese/collector_artifacts/<phase>/` (run.sh + result.txt each).

## Status

| Phase | State | Notes |
| --- | --- | --- |
| 0 — Node discovery | ✅ done | RTX 5090, 32607 MiB, 600 W (Gigabyte AIB), max SM 3105 MHz, CC 12.0, driver 595.71.05, CUDA 13.2 |
| 1 — Repo prep | ✅ done | branch `data/rtx_5090-vllm-0.19.0` @ 5b3c7cf2 (rename to `-0.22.0` pending); draft PR deferred until first data |
| 2 — System metadata | ✅ done | `systems/rtx_5090.yaml` (419 TF bf16 @ 2407 MHz boost, same-die scaling from rtx_pro_6000_server); registered in `SupportedSystems`; data dir created; 29/29 unit tests pass |
| 3 — Preflight | ✅ done | vllm 0.22.0 in container; **SM 120 selects FLASH_ATTN for ViT** (vllm's FA covers consumer Blackwell in 0.22 — Triton-fallback assumption outdated) |
| 4 — Smoke (`--smoke`) | ✅ done | 4 cases, 0 errors, `kernel_source=vllm_vit_flash_attn`; pyarrow missing in vanilla image → installed at run time |
| 5 — Limited (`--limit 20`) | ✅ done | 20 rows, parquet finalized end-to-end |
| 6 — Full collection (`--resume`) | ✅ done | **7,679/7,679 rows, 0 errors, ~9 min** (not 1–2 h — kernels tiny); all `vllm_vit_flash_attn`; installed at `systems/data/rtx_5090/vllm/0.22.0/encoder_attention_perf.parquet` |
| 7 — Validate consumption | ✅ core done | `get_database('rtx_5090','vllm','0.22.0')` loads; `query_encoder_attention(b=8, n=16, head_size=72, bf16)`: seq 784→0.173ms, 1764→0.746ms, 3136→2.137ms, 6400→8.761ms (clean quadratic). Pending: sanity charts, full-model query (needs gemm) |
| 6b — ViT gemm collection (bf16) | ✅ done | 35,742/35,742 cases → 33,516 unique rows. Gaps recorded: 2,228 giant-shape OOM (32GB limit) + 105 pre-skipped (>4GB footprint cutoff). Incident: CUDA-graph state corruption after OOM churn segfaulted two runs → fixed by pre-skip cutoff + `empty_cache` + chunked container restarts; 106 small-shape false-OOMs requeued, all clean (0 errors) |
| 7b — Full ViT costing | ✅ done | SDK `_run_encoder_phase` for Qwen3-VL-8B @448×448: **6.66 ms total**, GEMMs dominate (ffn1 1.50 / ffn2 1.24 / qkv 1.14 / attn 1.13 ms), sources silicon/mixed/empirical as designed |
| 8 — Handoff | 🔄 partial | Two DCO commits on `data/rtx_5090-vllm-0.22.0`: system+encoder parquet, gemm parquet. Pending: DoD summary, upstream PR decision, fallback trace |
| A — Route A validation | ✅ **SUCCEEDED** (final) | **AIC matched the empirical test.** Locked clocks (SM 2407/mem 14001), 5×50 iters, 95% CI. Wall: 11.360±0.006 / 36.421±0.010 / 103.824±0.022 ms vs predicted 7.822 / 31.973 / 89.347 ms. Profiler reconciliation @448²: attention matches within 3%; kernel time minus unmodeled ops (patch_embed 0.459, deepstack glue 0.248) = 8.92 vs 7.82 ms (~12%, attributed to HF-vs-vLLM kernel variants + unfused elementwise); dispatch gaps 1.736 ms (15.3%). No unexplained residual — AIC simply does not model all physical effects at this phase (dispatch, conv, glue); those move to the Mocker/DynoSim phase. Full ledger: `collector_artifacts/phaseA_validation/result.txt` |

## Key findings / decisions

- **vllm version**: encoder collector `__compat__ = "vllm>=0.21.0"`; manifest pin
  (0.19.0) is stale; local qwen3-vl-embed image (0.20.0) rejected.
  → **Collect under vllm 0.22.0** (matches decoder-side h100_sxm tuple — one backend
  version end to end). Image `vllm/vllm-openai:v0.22.0` pulling in background.
- **Kernel fidelity**: collector delegates to vLLM's own `get_vit_attn_backend()` —
  measured kernel == production kernel on SM 120 by construction. bf16 only.
- **ViT identity**: Qwen3-VL 8B/32B/235B share one vision tower (depth 27, hidden 1152,
  16 heads, inter 4304, patch 16); 8B projector out (4096) == 235B. Standalone extracted
  model: `/home/gio/tese/models/Qwen3-VL-8B-ViT/` (1.15 GB, 576M params, verified fwd
  pass on 5090).
- **rtx_pro_6000_server precedent**: SM 120 bring-up already done upstream (full
  registry incl. MoE) but has NO encoder_attention parquet → our collection also
  quantifies the SDK's encoder-timing fallback error (baseline TBD via
  `_build_op_sources` trace).
- **MIG**: not available on 5090 (GeForce) — live encoder-pool validation is 1 worker
  per card or MPS process-packing.
- **Deepstack mergers ARE modeled** (runtime-confirmed): `projector_n_instances=4`
  in the built model; forcing 1→4 scales projector cost exactly 4.00×.
- **Validation verdict (final)**: AIC matched the empirical test. Attention op
  (the collected quantity) within 3% of silicon; full kernel-time ledger closes
  with no unexplained residual. AIC does not model all physical effects at this
  phase (dispatch gaps 15.3%, patch_embed conv 4.8%, deepstack glue 2.6%,
  kernel-variant deltas ~12% of comparable work) — these are serving-stack
  effects to be exercised in the Mocker/DynoSim phase.

## Next actions

1. Phase 8: Definition-of-Done handoff summary; decide upstream PR
   (encoder parquet is a genuine gap-fill; yaml + gemm make it complete)
2. ~~Fallback trace~~ ✅ done — **no fallback exists**: SILICON/HYBRID/EMPIRICAL
   all hard-error without encoder parquet; only SOL answers and it underestimates
   ~5.9× (0.0061 vs 0.0358 ms measured). Qwen3-VL support-matrix "PASS" on such
   systems = text-only costing (no image dims → encoder phase skipped).
   Artifact: `collector_artifacts/phaseB_fallback_trace/result.txt`
3. ~~Route A validation~~ ✅ done (see status table; scripts in
   `collector_artifacts/phaseA_validation/`)
4. ~~Sanity charts~~ ✅ done — gemm chart healthy (math SOL ~45–55% plateau,
   clean roofline transition, no anomalies; minor >1.0 mem-SOL artifact at M≤2).
   Tool has no chart type for encoder_attention (data verified via SDK instead).
   CLI smoke skipped: context/generation attention parquets absent by design
   (decoder ops out of encoder-pool scope). Artifacts:
   `collector_artifacts/phase7_sanity_charts/{gemm_rtx_5090_vllm_0.22.0.png,summary.md}`
5. ~~vLLM-serve follow-up~~ ✅ superseded — the torch.profiler reconciliation
   ledger answered its question directly (residual fully decomposed: dispatch
   1.736 ms, unmodeled ops 0.71 ms, kernel variants ~12%; attention within 3%).
   A vLLM wall-clock number remains a nice-to-have narrative datapoint only;
   serving behavior itself is the Mocker/DynoSim phase's subject.
6. Two-pool composition — **minimal test PASSED** (2026-07-06):
   `collector_artifacts/phase9_two_pool/{encoder_pool_sim.py,run.sh,two_pool_report.json}`.
   Stage 1: FIFO encoder-pool sim (service = AIC ViT 7.82 ms on rtx_5090 silicon)
   → mooncake trace with timestamp-shifted handoff (PyPI dynamo wheel lacks
   agentic_mooncake/tool_wait_ms). Stage 2: dynamo.replay offline kv_router
   2 workers → AIPerf report (TTFT 32.4 ms avg, 27.6 req/s, 50 reqs).
   Next fidelity steps: h100_sxm AIC engine timing for the LLM pool; per-request
   image counts/sizes; load sweeps; then Planner simulation for autoscaling.

## Artifacts

- `collector_artifacts/phase0_node_discovery/{run.sh,result.txt}`
- `collector_artifacts/phase1_prepare_repo/result.txt`
- `collector_artifacts/phase2_system_metadata/{rtx_5090.yaml,result.txt}`
- `collector_artifacts/phase3_preflight/compat_notes.md` (incl. container results:
  FLASH_ATTN on SM 120)
- `collector_artifacts/phase4_smoke/{smoke_rows.csv,collection_summary_vllm.json}`
- `collector_artifacts/phase5_limited/limit20.parquet`
- `collector_artifacts/phase6_full/` (encoder checkpoint files)
- `collector_artifacts/phase6b_gemm/run_gemm_bf16.py` (bf16 driver, OOM pre-skip,
  resume checkpoint)
- aiconfigurator `collector_logs/vllm/0.22.0/gemm_bf16_errors.jsonl` (documented gaps)
- aiconfigurator branch: `data/rtx_5090-vllm-0.22.0`, two DCO commits:
  1. system yaml + SupportedSystems + encoder_attention_perf.parquet (7,679 rows)
  2. gemm_perf.parquet bf16 (33,516 rows)
- installed data: `src/aiconfigurator/systems/data/rtx_5090/vllm/0.22.0/
  {encoder_attention_perf,gemm_perf}.parquet`
