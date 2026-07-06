# Dev Workflow — tests, local bring-up, deploy, CI, guidelines

## Build from source (CLAUDE.md)

```bash
uv venv dynamo && source dynamo/bin/activate
uv pip install pip 'maturin[patchelf]'
cd lib/bindings/python && maturin develop --uv && cd -   # rerun after ANY Rust change
uv pip install -e lib/gpu_memory_service && uv pip install -e .
```
Rust: `cargo build` / `cargo test -p <crate>` / `cargo clippy --all-targets` / `cargo fmt`
(toolchain pinned 1.93.1, edition 2024). etcd+NATS via `dev/docker-compose.yml`.

## Tests (`tests/`)

**Invocation — never bare `pytest`** (system pytest can't see the venv):
```bash
export HF_HUB_OFFLINE=1 HF_TOKEN="$(cat ~/.cache/huggingface/token)"
python3 -m pytest -xvv --basetemp=/tmp/pytest_temp tests/path/test_x.py::test_name
python3 -m pytest -m "vllm and gpu_1 and pre_merge" ...        # marker filtering
python3 -m pytest --max-vram-gib=24 --dry-run -m "gpu_1 and vllm" tests/serve/test_vllm.py
```
`--models-dir=/path` = read-only pre-populated HF cache (sets offline, skips predownload).

- Suite layout: `serve/` (backend E2E, config-dataclass pattern), `router/` (E2E with
  mockers/backends; own AGENTS.md), `fault_tolerance/` (cancellation, migration, etcd_ha,
  deploy scenarios), `kvbm_integration/`, `runtime/`, `frontend/` (+grpc), `basic/`, `deploy/`,
  `benchmarks/`, `utils/` (shared infra, NOT tests: `ManagedProcess`, `allocate_port`,
  `vram_utils`).
- conftest hierarchy: root `/conftest.py` only fixes `dynamo.vllm`-shadows-`vllm` collection;
  **`tests/conftest.py` (1314 lines) is the fixture hub**: `runtime_services` (etcd+NATS),
  `runtime_services_dynamic_ports` (xdist-safe), `predownload_models`, `discovery_backend`
  (parametrize `["file","etcd"]`), `request_plane` (`["nats","tcp"]`), VRAM-parallel scheduler
  (`--max-vram-gib` + `-n`), auto-skip framework-marked tests when lib not importable.
- **Markers** (strict; `pyproject.toml`): every test needs scheduling (`pre_merge`/`post_merge`/
  `nightly`/`weekly`/`release`) + GPU (`gpu_0..gpu_8`) + type (`unit`/`integration`/`e2e`) +
  (if framework-marked) exactly one bucket (`core`/`multimodal`/`router`/`kvbm`/
  `fault_tolerance`). Model/VRAM: `model("org/name")`, `profiled_vram_gib(N)`. Tests >30 s need
  `@pytest.mark.timeout(3×avg)`. `filterwarnings=error`.
- **Model-size guardrails** (`.ai/test-model-size-guardrails.md`): CI = 24 GB L4. Use
  `Qwen/Qwen3-0.6B` (text), `Qwen/Qwen3-VL-2B-Instruct` (MM), TinyLlama fallback.
  `profiled_vram_gib > 24` = hard NO-GO for pre/post/nightly.

## Local bring-up (`examples/`)

Minimal aggregated: `examples/backends/vllm/launch/agg.sh` — frontend + 1 worker (needs
etcd/NATS running). Disagg: `disagg.sh` — 2 GPU workers with
`--kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_both"}'`. Many variants:
`agg_router.sh`, `*_kvbm.sh`, `agg_multimodal*.sh`, `elastic_ep.sh`, `multi_node_tp.sh`.
**Launch-script rules** (`.ai/bash-launch-guidelines.md`): `set -e`, `trap 'kill 0' EXIT`, source
`examples/common/{gpu_utils,launch_utils}.sh`, use `build_<engine>_gpu_mem_args` (never manual
`_PROFILE_OVERRIDE_*`), background all + `wait_any_exit` last.

## Deploy (`deploy/`)

- **Operator** (`deploy/operator/`, Go/kubebuilder, group `nvidia.com`, v1alpha1+v1beta1).
  CRDs: **DynamoGraphDeployment (DGD)** (top-level; `spec.backendFramework`,
  `spec.services{componentType: frontend|worker, replicas, resources...}`),
  DynamoComponentDeployment, DynamoGraphDeploymentRequest (DGDR — profiler input),
  DynamoGraphDeploymentScalingAdapter, DynamoCheckpoint, PodSnapshot(Content), DynamoModel,
  DynamoWorkerMetadata. Controllers in `internal/controller/`; grove integration
  `internal/dynamo/grove.go` (PodCliqueSets, GROVE_* env-var hostname computation).
- **Inference gateway** (`deploy/inference-gateway/`): Go **EPP** (Gateway API Inference
  Extension endpoint picker; plugins disagg prefill/decode scorers, dynamo_kv_scorer) + Rust
  Envoy **ext-proc** filter.
- **Helm** (`deploy/helm/charts/platform/`): umbrella; grove via `global.grove.install/enabled`.

## Recipes (`recipes/`)

Per model: `model-cache/` (PVC + HF download Job) + `<framework>/<mode>/{deploy.yaml (DGD),
perf.yaml (aiperf Job), [gaie/]}`. Modes: agg, agg-kvbm, disagg, disagg-multi-node,
disagg-kv-router, WideEP. Flow: install platform → namespace + hf-token-secret → apply
model-cache → deploy → perf. Use the `dynamo-recipe-runner` skill.

## Container & benchmarks

`container/` — Jinja-templated Dockerfiles (`Dockerfile.template` + `templates/*.Dockerfile`),
driver `container/run.sh` + `render.py`; targets base/wheel_builder/runtime/dev/frontend/planner.
`benchmarks/` — `frontend/` (aiperf sweep runner: sweep_core/executors/k8s; the
`dynamo-frontend-benchmark` skill drives this), `mocker/` (AIC Rust-vs-Python A/B), `router/`
(prefix-ratio, real-data), loadgens (burstgpt, sin).

## `.ai/` guidelines (authoritative, CodeRabbit-enforced)

- **python-guidelines.md** — top-level imports; fail fast (no bare except / silent pass); no
  defensive getattr on known types; lazy `%s` logging; ruff format + check.
- **pytest-guidelines.md** — venv invocation, markers, no hardcoded ports (use `allocate_port`),
  fixtures/ManagedProcess not hand-rolled subprocess, monkeypatch not `os.environ[...]=`.
- **ci-guidelines.md** — pre-merge CI runs only `pre_merge`; to validate other tests, temporarily
  promote marker with a TODO-revert comment, then revert in the same PR before merge.
- **bash-launch-guidelines.md** — see local bring-up above.
- **test-model-size-guardrails.md** — see tests above.
- **linear-ticket-refs.md** — no `DIS-`/`DYN-XXXX` Linear IDs in code on `main`; use GH-NNNN.

## CI (`.github/workflows/`)

`pr.yaml` (docker-build-test per changed area) / `pre-merge.yml` (pre_merge tests, all PRs) /
`dynamo-pipeline.yml` (reusable: image build + rust checks + mypy + pytest) /
`post-merge-ci.yml` / `nightly-ci.yml` (cron 00:00 PST, no-cache full build + release staging).
Commits need DCO (`git commit -s`); PR titles Conventional Commits; bodies need
Summary + Validation.

## Docs

Published via **Fern** (`fern/docs.yml`; nav in `docs/index.yml`) to docs.nvidia.com/dynamo.
Architecture home: **`docs/design-docs/`** (architecture, disagg-serving, distributed-runtime,
discovery-plane, request-plane, event-plane, router-design, kvbm-design, planner-design).
Use the `dynamo-docs` skill for any docs/recipes/examples content change.
Repo skills (`.claude/skills` → `.agents/skills`): DEP create/status/update, recipe-runner,
router-starter, troubleshoot, interconnect-check, frontend-benchmark, clone-hotpath-audit,
graham-code-review, gh-issue-bug.
