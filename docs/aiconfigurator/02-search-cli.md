# Search Layer & CLI (`sdk/sweep.py`, `picking.py`, `pareto_analysis.py`, `cli/`)

**Two stacks coexist**: new (`Task → sweep → picking`, used by CLI/api) and legacy
(`pareto_analysis.agg_pareto/disagg_pareto → InferenceSession.find_best_*`, still used by the
webapp). Parity locked by `tests/unit/sdk/sweep/`. Sweep returns the **SLA-feasible candidate
set, NOT a Pareto frontier** — frontier is a downstream plotting view; best-config selection is
sort+group-by on candidates.

## CLI modes (`cli/main.py`; dispatch in `main()` ~L2298)

Common experiment flags: `--save-dir`, `--top-n` (5), `--systems-paths`,
`--deployment-target {dynamo-j2|dynamo-python|llm-d-helm|llm-d-kustomize}`,
`--engine-step-backend {python|rust}`, generator overrides (`--generator-set`,
`--generator-config`, `--generator-dynamo-version`, `--generated-config-version`).

- **default** — full agg-vs-disagg sweep+compare. `--model-path`, `--total-gpus`, `--system`
  (+ `--decode-system` for hetero disagg), `--backend {trtllm|vllm|sglang|auto}` (auto = sweep
  all three, merge), `--backend-version`, `--database-mode`, `--transfer-policy`; workload/SLA:
  `--isl 4000 --osl 1000 --ttft 2000 --tpot 30`, `--request-latency` (switches optimization
  mode), `--strict-sla`, `--prefix`, `--inclusive-tpot` (display-only); spec-dec/MoE: `--nextn`,
  `--nextn-accept-rates`, `--enable-wideep`, `--moe-backend`; `--thorough-sweep` /
  `--thorough-config` → spica (see 06).
- **exp** — experiments from YAML (`--yaml-path`).
- **generate** — naive config, no sweep (smallest TP with `TP×VRAM > 1.5×weights`); prints
  "NAIVE — may not fit" warning.
- **support** — support-matrix check (`--system all`/`--backend all` → consolidated matrix).
- **estimate** — single-point TTFT/TPOT/power, explicit parallelism
  (`--estimate-mode {agg|disagg|afd|static|static_ctx|static_gen}`, `--batch-size`, `--tp/--pp/
  --dp/--moe-ep...`); detail report via `estimate_detail_report.py`
  (`--detail summary|memory|time|energy|source|all`, ASCII bars).

## sweep.py (the optimizer)

Constants: rate-match degradations **prefill 0.9 / decode 0.92**, autoscale TTFT correction
**1.8** (duplicated in picking.py, parity-locked). Caps: 32 prefill workers, 16 decode workers
per parallel category. Batch schedules: decode 1..512 graduated; agg 1..1024 graduated.

- **`sweep_agg`**: enumerates `Task.iter_parallel("agg")` tuples `(tp,pp,dp,moe_tp,moe_ep,cp)` ×
  tpot values (or `(ttft,tpot)` pairs from `enumerate_ttft_tpot_constraints` when
  request-latency mode) × batch × ctx_tokens (`_agg_ctx_tokens_list`, snaps to isl multiples
  when chunked-prefill off). Backend+model built once per parallel (cache survives tpot loop,
  ~80x). Per point → `predict_agg_worker`; OOM breaks the monotonic ctx loop. **SLA filter:
  keep iff `tpot ≤ target AND ttft ≤ target`**. Output `ColumnsAgg` DataFrame sorted
  `tokens/s/gpu` desc. Distinguishes errors: `InsufficientMemoryError` / `KVCacheCapacityError`
  / `NoFeasibleConfigError`.
- **`sweep_disagg`**: per-role candidate DataFrames (`_get_disagg_worker_candidates`,
  memory-fitting `ColumnsStatic`) → per (ttft,tpot) constraint: prefill filtered
  `ttft×1.8 < target` (top 32 by seq/s/gpu), decode filtered `tpot < target` (top 16 per
  parallel group) → **worker matching** via shared `@lru_cache _match_workers`: enumerate
  (p_num, d_num) under GPU budget, effective throughput
  `min(p_thr·p_num·0.9, d_thr·d_num·0.92)`, maximize throughput-per-GPU →
  `_rate_match_dict` composes a `ColumnsDisagg` row (`request_latency = ttft + tpot·(osl−1)`).
  `autoscale=True` bypasses rate matching → `picking.pick_autoscale` (1P/1D independent).
  `require_same_tp` for SGLang non-WideEP.

## picking.py / pareto_analysis.py

- `get_pareto_front(df, x_col, y_col, maximize_x, maximize_y)` — O(n²) dominance scan,
  plotting only.
- **`pick_default`** — the default-mode selector: computes `tokens/s/gpu_cluster`
  (accounts GPU-budget quantization: `·(total_gpus // num_total_gpus)·num_total_gpus/total_gpus`);
  `--strict-sla` filters frontier pre-Pareto; axes `tokens/s/user` (or request_latency) vs
  `tokens/s/gpu_cluster`; best via `get_best_configs_under_tpot_constraint` (group-by parallel,
  sort cluster-throughput desc). Fallback flags `_sla_exceeded` + closest config when nothing
  meets SLA.
- **`pick_load_match`** — minimize GPUs for `target_request_rate` xor `target_concurrency`
  (`replicas_needed = ceil(target/per-replica)`); `max_total_gpus` cap → `load_served_pct`.
- **`pick_autoscale`** — independent P/D pick, no rate matching, workers=1.
- **`pick_optimization_type`** — throughput vs latency objective without explicit SLA.
- The core tradeoff axis pair: **x = tokens/s/user (≈1000/tpot, interactivity), y =
  tokens/s/gpu (cost efficiency)**.

## exp YAML (V2 flat schema; canonical `cli/example.yaml`)

Top-level keys = experiment names; fields map 1:1 to `Task`. Optional `exps:` ordering. Covers:
serving_mode, model/system/backend(+version), isl/osl/prefix/ttft/tpot, database_mode,
quant overrides (5 modes), agg search-space candidate lists, per-role `prefill_*`/`decode_*`
worker+search blocks, orchestration knobs (worker caps, degradation factors, corrections).
V1 nested schema deprecated (auto-converted). Real examples in `cli/exps/`
(qwen3_32b_disagg, deepseek_wideep_trtllm, hetero_disagg, database_mode_comparison).

## cli/api.py (programmatic)

- `cli_default(**kwargs mirroring flags)` → **`CLIResult`**: `chosen_exp`, `best_configs:
  dict[str,DataFrame]`, `pareto_fronts`, `best_throughputs` (tokens/s/gpu_cluster), `tasks`,
  `best_latencies`, `raw_results`.
- `cli_exp(yaml_path | config dict)` → CLIResult. `cli_support(...)` → `(agg_ok, disagg_ok)`.
  `cli_estimate(...)` → `EstimateResult` (ttft/tpot/power/throughput properties).
- Bridge: `cli/utils.py::process_experiment_result` (Task + pareto_df → pick_default/
  pick_load_match); `merge_experiment_results_by_mode` merges backend=auto results.

## Reports (`cli/report_and_save.py`)

- `log_final_summary` — ASCII "AIConfigurator Final Results" box: inputs/SLA, agg-vs-disagg
  winner, per-experiment worker-setup tables.
- `save_results` → `save_dir/<model>_<system>_<backend>_isl<>_osl<>_ttft<>_tpot<>_<rand>/`:
  `pareto_frontier.png`; per-exp `best_config_topn.csv`, `pareto.csv`, `exp_config.yaml`
  (Task.to_yaml for reproduction); per top-i config: `generator_config.yaml`,
  `per_ops_source.json` (data provenance), + **full deployment artifacts** via
  `generate_from_request` honoring `--deployment-target`. Loud warnings distinguish the
  search/perf-DB version from the deployed config version.

## webapp note

The Gradio webapp still drives the **legacy** `agg_pareto`/`disagg_pareto` path
(`webapp/events/event_fn.py`), sharing frontier plotting + column schemas with the new stack.
