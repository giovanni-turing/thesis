# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This directory (`/home/gio/tese`) is a **thesis research workspace**, not a single project. It
holds many independently-cloned upstream repos side by side, in two clusters. There is **no
top-level git repo or build** — each leaf directory is its own git checkout tracking `main`:

- **`ai-dynamo/`** — the NVIDIA ai-dynamo stack: `dynamo`, `nixl`, `grove`, `aiconfigurator`,
  `aiperf` — the disaggregated LLM inference stack (see "How the pieces relate" below).
- **`rapids/`** — 14 cloned `github.com/rapidsai/*` repos: the RAPIDS GPU data-science stack
  (`rmm`, `kvikio`, `cudf`, `cuml`, `cugraph`, `cuspatial`, `cucim`, `cusignal`, `dask-cuda`,
  `cuxfilter`, `jupyterlab-nvdashboard`, `notebooks`, plus `raft` + `cuvs` — the primitive layer
  under cuML/cuGraph). Layering: RMM (memory) + KvikIO (storage IO) → cuDF (dataframe) →
  cuML/cuGraph/cuSpatial/cuCIM (domain libs) on RAFT/cuVS, with dask-cuda for multi-GPU.
  `cusignal` and `notebooks` are archived; `notebooks` submodules are uninitialized here.
  Also present (non-rapidsai): `rapids/cupy` (cupy/cupy) and `rapids/cccl` (NVIDIA Thrust/CUB/
  libcudacxx). Closed CUDA libs (cuBLAS/cuSOLVER/cuSPARSE/cuFFT/cuDNN/cuRAND/NCCL) have no local
  source — reachable only via CuPy wrappers.

Work happens *inside* one subproject at a time. Before doing anything in a subproject, read its own
`CLAUDE.md` / `AGENTS.md` (and any `.claude/`, `.agents/`, `.ai/` rules it points to) — those are
authoritative and take precedence over this file, which only orients across the tree.

## How the pieces relate

Together these form NVIDIA's disaggregated LLM inference stack:

- **dynamo** — the datacenter-scale inference **orchestration layer** above engines (vLLM, SGLang,
  TensorRT-LLM). Disaggregated prefill/decode, KV-aware routing, tiered KV cache (KVBM), SLA
  autoscaling. The other four plug into or serve it.
- **nixl** — point-to-point transfer library abstracting CPU/GPU memory and storage behind a
  plugin architecture; the data-movement substrate Dynamo uses for KV transfer.
- **grove** — Kubernetes API/operator for orchestrating multi-node disaggregated inference
  deployments as a single Custom Resource (gang scheduling, topology-aware placement).
- **aiconfigurator** — offline tool that searches the deployment config space (worker counts,
  parallelism) under TTFT/TPOT SLAs and emits Dynamo/llm-d config files.
- **aiperf** — benchmarking tool measuring performance of served generative AI models.

## Per-subproject stack & entry points

Each has its own toolchain — do not assume a shared one.

| Subproject       | Languages                     | Build / test entry                                                        |
| ---------------- | ----------------------------- | ------------------------------------------------------------------------- |
| `dynamo`         | Rust core + Python (PyO3)     | `cargo` workspace + `maturin develop --uv`; pytest via venv. See its CLAUDE.md |
| `nixl`           | C++/CUDA + Rust + Python      | `meson` (`meson.build`, `meson_options.txt`)                              |
| `grove`          | Go (Kubernetes operator)      | `Makefile` in `operator/` (`make kind-up`, `make deploy`); `.golangci.yaml` |
| `aiconfigurator` | Python + Rust (`aiconfigurator-core`) | `pyproject.toml` + `uv.lock`; pytest (`pytest.ini`)                |
| `aiperf`         | Python                        | `pyproject.toml`; pytest                                                   |

## Working here

- Run build/lint/test commands from *within* the relevant subproject directory, never from this root.
- Each subproject carries its own agent guidance files; several (`dynamo`, `aiconfigurator`,
  `aiperf`) have `.claude/` rules and skills that gate edits to specific paths — read the guard in
  the subproject's `CLAUDE.md`/`AGENTS.md` before touching generator, collector, or binding code.
- These are upstream mirrors on `main`. Treat changes as thesis experiments; there is no shared
  CI or release process at this level.

## Local navigation docs (`docs/`)

- `docs/dynamo/` — deep agent-navigation reference for `ai-dynamo/dynamo` (subsystem-by-subsystem:
  runtime, llm, kv-routing, kvbm, python layer, dev workflow), written from whole-tree exploration.
  Read `docs/dynamo/README.md` first when working inside dynamo.
- `docs/aiconfigurator/` — same treatment for `ai-dynamo/aiconfigurator` (sdk perf model,
  search/CLI, generator, collector, rust core, spica/systems/dev). Read its README.md first when
  working inside aiconfigurator.
- `docs/rapids/` — usage + source-navigation + troubleshooting for the core RAPIDS libs (rmm,
  cudf, cuml, cugraph, cupy): "which layer owns my symptom" triage, debug knobs, symptom→source
  tables. Also ingested into the `rapids` Qdrant collection (`doc_type: agent-nav`) — retrievable
  via the raggae RAG skill. Read `docs/rapids/README.md` first when working in rapids/.

## Project skills (`.claude/skills/`)

Project-authored (maintain these here):
- `rapids-answers` — quick, assertive, read-only, docs+code-grounded answers about the RAPIDS libs
  (cudf/cuml/cugraph/cupy/rmm). Retrieves from `docs/rapids/`, the `rapids` RAG collection (raggae),
  and live source; answers with citations. Triggers on how/why/debug questions about those libs.

Vendored (static snapshots copied from the subprojects' own `.agents/skills/` and cuDF's `skills/`
so they're invocable from this root). **Detached from their source repos** (mirrors on `main`) —
re-copy from source to update; several assume you're running inside their home repo / a live cluster.

| Skill | Copied from |
| ----- | ----------- |
| `dynamo-recipe-runner`, `dynamo-router-starter`, `dynamo-interconnect-check`, `dynamo-troubleshoot`, `dynamo-frontend-benchmark`, `dynamo-docs` | `ai-dynamo/dynamo/.agents/skills/` |
| `aic-auto-collect` | `ai-dynamo/aiconfigurator/.agents/skills/` |
| `grove-user-guide` | `ai-dynamo/grove/.agents/skills/` |
| `nixl-python-api` | `ai-dynamo/nixl/.agents/skills/` |
| `accelerated-computing-cudf` | `rapids/cudf/skills/` |
