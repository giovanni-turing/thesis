# Generator (`src/aiconfigurator/generator/`) — deployment artifacts

**⚠ Guarded zone.** Before editing, read `.claude/rules/generator-development.md` and the 9
references under `.claude/rules/generator/` (render_path_policy, guard_rails, config_schema,
rule_authoring, template_authoring, new_backend_version, debugging, testing,
cross_module_impact). **Precedence: inline `# Guard:` / `# Why:` comments in `.j2`/`.rule`
sources beat guard_rails.md.**

## Flow

Two entries converge on one params dict → one rendering engine:

- **SDK/profiler path**: `module_bridge.py::task_config_to_generator_config(task, result_df_row,
  overrides, gpus_per_node)` — pulls tp/pp/dp/moe_tp/moe_ep/bs + quant modes from the best-config
  row, builds per-role worker payloads, `gpus_per_worker = tp·pp·dp`, scales worker counts to
  total_gpus. Typed twin `task_config_to_request` → `GeneratorRequest` → `api.generate_from_request`.
- **Input-dict path**: `api.generate_config_from_input_dict` (re-exported from
  `aggregators.py`) — walks the schema `config/deployment_config.yaml`, routes dotted keys into
  sections (ServiceConfig/K8sConfig/params.<role>/WorkerConfig/SlaConfig/BenchConfig/...),
  applies defaults via `rendering.apply_defaults`, computes DGD name
  `{prefix}-{agg|disagg}{-router?}`.
- **Orchestrator**: `pipeline.py::run_pipeline(params, backend, ..., deployment_target)` —
  deep-copies params (rule layer mutates in place!), resolves facts (best-effort), builds
  `DeploymentIR` (`ir.py`: components/roles/replicas/edges/env/provenance), renders. **The IR
  is a v2 seam — resolved but applied nowhere; artifacts still render from the legacy params
  dict.**
- **Workhorse**: `rendering/engine.py::render_backend_templates` (~700 lines):
  `apply_rule_plugins` → `prepare_template_context` (flattens to Jinja ctx with
  `prefill_*`/`decode_*`/`agg_*` prefixed keys + nested backend dicts) → render per-worker
  engine args (trtllm) → cli_args → k8s → run scripts → benchmark/sflow/EPD.

## The two render paths (render_path_policy.md — MUST follow)

| Artifact | Mechanism |
| --- | --- |
| `k8s_deploy.yaml` (DynamoGraphDeployment CRD, multi-doc) | **typed Python builder** — `builders/k8s_builder.py` + `dgd_model.py` |
| Everything flat-text: `cli_args[.ver].j2`, trtllm `extra_engine_args.<ver>.yaml.j2`, `run.sh.j2`, llm-d values/kustomize, benchmark, sflow, EPD | **Jinja** — `config/backend_templates/<backend>/` |

- Typed builder is reserved for the structured k8s DGD only. **Do NOT add typed builders for
  flat text** (the trtllm engine-config builder experiment was reverted — no `manifests/`,
  no `contract/`). New trtllm engine version = new versioned `.j2`, never a builder.
- `_populate_vllm/_populate_sglang/_populate_trtllm` are **intentionally duplicated** (no shared
  helpers — PR #314→#340 revert). `dgd_model.py`: `DGD` (`nvidia.com/v1alpha1`), `ConfigMapDoc`
  (trtllm, emitted first), `ComputeDomainDoc` (multinode).
- **Divergent resolution gotcha**: mapping `default:` values appear in `render-config`
  inspection but are NOT deployed; a default that must deploy belongs in the **rule layer**.

## Declarative sources of truth (`generator/config/`)

- `deployment_config.yaml` — input schema (~54 params): `key: Section.field`, `required`,
  `default` (literal or Jinja expr), `backends:` restriction, `backend_defaults:`.
- `backend_config_mapping.yaml` — unified param → per-backend CLI flag; string | `null`
  (unsupported) | `{key, value: <jinja>, [default]}` transforms (e.g. kv-cache-dtype
  `bfloat16→auto`, sglang `fp8→fp8_e4m3`, cuda-graph padding inversion). Pure translation layer.
- `backend_version_matrix.yaml` (+ twin `facts/runtimes/dynamo.yaml`) — dynamo_version →
  {vllm, sglang, trtllm} versions (head: 1.2.0 → vllm 0.20.1 / sglang 0.5.11 / trtllm 1.3.0rc14).
- **Template version selection** (`_select_versioned_template`): exact match → **floor match**
  (highest ≤ requested, packaging.version) → unversioned base. Version intent:
  `--generated-config-version` > `--dynamo-version` (matrix) > perf-DB latest.

## Rule plugin DSL (`rule_plugin/{trtllm,vllm,sglang}.rule` + `benchmark/` variants)

Evaluator `rendering/rule_engine.py`. Syntax: `<scope> <key> = <jinja-expr>` with scope
prefixes `prefill|decode|agg|encode` and multi-scopes (`agg_prefill_decode` = all; default);
`when <cond>:` blocks (no nesting); dotted LHS (`DynConfig.enable_router = true`) writes config
sections. Nullable guards mandatory (`(SlaConfig.isl or 0)`).

Production rules compute per-worker defaults: batch sizing (prefill bs=1 fallback;
agg/decode 512/batch·2 deploy vs max(128,batch) benchmark), token budgets **block-aligned**
(trtllm CRASH guard), `disable_overlap_scheduler` (prefill true / decode false), **MoE remap
`tensor_parallel_size = moe_tp·moe_ep`** (all backends; vLLM ÷dp), `gpus_per_worker=tp·pp·dp`,
prefix-caching → router enable, spec-decode type strings (trtllm `MTP` / sglang `NEXTN` /
vllm `mtp`), kv-dtype coercions, sglang `kv_transfer_backend=nixl`,
`preserve_engine_limits` gate (freeze SDK-validated values — spica sets this).

## Deployment targets

- **`dynamo-j2`** (default) — Jinja artifacts + typed-builder DGD. Full feature set (router
  wiring, planner, KVBM env, EFA/ComputeDomain, multimodal EPD, benchmark, sflow).
- **`dynamo-python`** — k8s via Dynamo's own `dynamo.profiler.utils.config_modifiers
  .build_dgd_config`; trtllm engine YAML translated to `--trtllm.<key>` dynamic flags
  (`rendering/translate.py`).
- **`llm-d-helm`** / **`llm-d-kustomize`** — vllm full support, sglang values-only;
  **trtllm has NO llm-d templates → TRT-LLM is Dynamo-only**.
- Multimodal EPD single-pod is trtllm-only.

## Guard rails (guard_rails.md — abbreviated; severity CRASH/OOM/SILENT/PERF/K8S)

trtllm: build_config nesting is version-dependent; cache_transceiver lifecycle (absent →
engine-YAML → CLI override by version range) and `backend='DEFAULT'` (CRASH);
`max_num_tokens % tokens_per_block == 0` (CRASH); MoE TP=moe_tp·moe_ep (OOM).
sglang: never emit `--moe-dense-tp-size` (CRASH); wideep xor non-wideep; NVFP4 needs explicit
`--quantization`. vllm: `--cudagraph-capture-sizes` space-separated (CRASH);
`--kv-transfer-config` required for disagg; max-model-len + max-num-batched-tokens (OOM).
Cross: DGD name RFC-1123 ≤63; use `MODEL_PATH` env; per-node run scripts with frontend only on
node 0; MoE/quant detection from config.json not model name.

## naive.py (generate mode)

No sweep/SLA/memory validation: min TP = smallest power-of-2 with `tp×vram > 1.5×weights`;
strategy Dense→TP, DSv3 MLA-MoE→DEP, other MoE→TEP; fixed bs=128, isl/osl 4000/1000. Output
under `{out}/{model}_naive_tp{tp}_pp{pp}_{rand}/` + `generator_config.yaml`.

## Output layout (`artifacts.py::ArtifactWriter`)

`cli_args_*` dropped (folded into k8s/run scripts); `extra_engine_args_*.yaml` →
`agg|prefill|decode|encode_config.yaml`; `run_<idx>.sh` per node (exec bit); `k8s_deploy.yaml`,
`k8s_bench.yaml`, `bench_run.sh`, llm-d files, `sflow.yaml`, EPD files.

## High-risk files

`rendering/engine.py`, `rendering/rule_engine.py`, `aggregators.py` (apply_defaults),
`builders/k8s_builder.py`, `module_bridge.py` (SDK field coupling). **Top bug pattern:
cross-backend parity drift** — editing one backend's rule/template/mapping without the other two.
