# RAPIDS — Agent Usage & Troubleshooting Docs

Practical reference for **using**, **navigating the source of**, and **debugging** the core
RAPIDS GPU libraries in `/home/gio/tese/rapids/`. Written 2026-07-05 from whole-tree source
exploration. Goal: ground answers about implementation and troubleshooting in the *actual code*,
not just API docs. Complements the repo markdown docs already indexed in the `rapids` RAG
collection — search that collection (`raggae` skill) for the upstream user guides; read these for
source-level navigation and failure diagnosis.

Repo commits explored: cudf `3652e80833`, cugraph `783e58c9`, cuml `857cc5aa4`, rmm `5d50a37b`,
cupy `468349ed5`.

## Documents

| Doc | Library | Focus |
| --- | --- | --- |
| [01-rmm.md](01-rmm.md) | RMM (memory manager) | pool/adaptor wiring, the process-global current resource, OOM/leak/fragmentation debugging |
| [02-cudf.md](02-cudf.md) | cuDF (DataFrame) | pandas-like usage, cudf.pandas accelerator, spilling, pandas-compat gotchas, IO |
| [03-cuml.md](03-cuml.md) | cuML (ML) | sklearn-compatible estimators, cuml.accel, output_type, OOM/dtype/parity debugging |
| [04-cugraph.md](04-cugraph.md) | cuGraph (graph) | graph build, renumbering, algorithms, dtype contract, multi-GPU |
| [05-cupy.md](05-cupy.md) | CuPy (ndarray) | numpy-drop-in, custom kernels, memory pool, compile/sync/device debugging |

## The stack (bottom → top)

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  cuDF (DataFrame) · cuML (ML) · cuGraph (graph)   ← domain libraries │
  │         all consume cuDF columns / CuPy arrays; cuML+cuGraph on RAFT │
  └───────────────┬───────────────────────────────┬─────────────────────┘
                  │  __cuda_array_interface__ / DLPack (zero-copy)        │
  ┌───────────────▼──────────────┐   ┌────────────▼──────────────────────┐
  │  CuPy (GPU ndarray)          │   │  RAFT / cuVS (primitives — cloned  │
  │  numpy/scipy drop-in         │   │  at rapids/raft, rapids/cuvs)      │
  └───────────────┬──────────────┘   └────────────────────────────────────┘
  ┌───────────────▼─────────────────────────────────────────────────────┐
  │  RMM (RAPIDS Memory Manager) — the allocator EVERYTHING allocates    │
  │  through via the process-global per-device "current device resource" │
  └─────────────────────────────────────────────────────────────────────┘
```

**The single most important cross-cutting fact:** every library allocates GPU memory through
RMM's **process-global per-device current resource** *at allocation time*, without taking a
memory-resource argument. So one `rmm.reinitialize(pool_allocator=True)` (and wiring CuPy/torch
to RMM) reconfigures allocation for the whole stack — and must be done *before* the libraries
allocate. This is why OOM/fragmentation debugging always starts at RMM (doc 01). See
[[rapids-rmm]] equivalents in [01-rmm.md](01-rmm.md).

## "Which layer owns my symptom?" — cross-library triage

Every domain library has the same shape: **Python API → thin Cython binding → C++/CUDA core**
(cuDF: `cudf.core` → `pylibcudf` → `libcudf`; cuML: `cuml.<family>.*pyx` → `libcuml++`; cuGraph:
`cugraph` → `pylibcugraph` → C API → `libcugraph`). Route a symptom to the right layer first:

| Symptom | Owning layer | Where to look |
| --- | --- | --- |
| OOM / `cudaErrorMemoryAllocation` / `rmm::out_of_memory` | **RMM** (allocation site is in the C++ core, but the *policy* is RMM) | doc 01 — pool/limiting/statistics adaptors; then the library's spill/batch options |
| "pandas/sklearn/networkx does X, RAPIDS does Y" (semantics, defaults, null/NaN, order) | **Python API layer** | doc 02 §pandas-compat, doc 03 §sklearn-caveats, doc 04 §troubleshooting |
| Wrong numeric result / crash inside a kernel / overflow | **C++/CUDA core** | `cpp/src/<algo>/` of the relevant lib |
| "unsupported dtype" / type errors | **Cython/C-API boundary** (dispatch) | cuDF `type_dispatcher.hpp`; cuGraph int32/64 edgelist contract; cuML float32/64 per-estimator |
| Slow after a "zero-code-change" import | **accelerator fallback to CPU** | cudf.pandas `profiler.py`; cuml.accel `CUML_ACCEL_LOG_LEVEL=debug` |
| Async/timing looks wrong, non-deterministic | **stream/execution** | CuPy `Stream`/`Event`; atomic reductions in cuML |
| Result IDs don't match input | **renumbering** (cuGraph-specific) | doc 04 — `G.unrenumber(...)` |

## Shared debug knobs (memorize these)

| Env / call | Effect |
| --- | --- |
| `rmm.reinitialize(pool_allocator=True, initial_pool_size="2GiB")` | one pool for the whole stack |
| `rmm.statistics` / `StatisticsResourceAdaptor` / `TrackingResourceAdaptor` | peak-bytes + leak hunting with stack traces |
| `RMM_LOG_FILE` / `rmm.reinitialize(logging=True)` | CSV trace of every alloc/free |
| `CUDF_SPILL=on`, `CUDF_SPILL_STATS=2` | GPU↔host spilling + spill tracebacks (cuDF) |
| `python -m cudf.pandas script.py` / `%load_ext cudf.pandas` | zero-code-change pandas → GPU |
| `python -m cuml.accel script.py` / `CUML_ACCEL_LOG_LEVEL=debug` | zero-code-change sklearn → GPU + fallback tracing |
| `cp.get_default_memory_pool().free_all_blocks()` | release CuPy's cached pool blocks |
| `CUPY_DUMP_CUDA_SOURCE_ON_ERROR=1`, `CUPY_CACHE_DIR` | CuPy kernel-compile debugging |
| `set output_type` — `cuml.using_output_type("numpy")` | control cuML return array type |
| `G.unrenumber(df, col)` / `renumber=False` | map cuGraph internal vertex IDs back |

## Interop (zero-copy) — the glue

- **`__cuda_array_interface__` (CAI)** and **DLPack** move GPU buffers between CuPy ↔ cuDF ↔ cuML
  ↔ numba with no copy. `cudf.Series.values` → `cupy.ndarray`; `cp.from_dlpack(df.to_dlpack())`;
  cuML estimators accept any CAI-exposing array. cuGraph takes cuDF edgelists.
- **One RMM pool for all**: wire CuPy (`cp.cuda.set_allocator(rmm.allocators.cupy.rmm_cupy_allocator)`),
  torch (`rmm.allocators.torch.rmm_torch_allocator`), numba (`RMMNumbaManager`) so every library
  draws from the same pool — avoids double-reservation OOMs. Details in doc 01 §6 and doc 05 §5.

## Version-matching (a frequent source of "it won't import / it crashes")

RAPIDS libs are released together on a `YY.MM` cadence and pin each other tightly (cuDF ↔ RMM ↔
cuML ↔ cuGraph must share a release; cuML/cuGraph also pin RAFT/cuVS). CuPy is wheel-tied to the
CUDA major (`cupy-cuda12x` vs `cupy-cuda13x`) and must match the installed driver/toolkit.
"cupy not importable" and RAFT/cuVS runtime errors are usually version-skew, not logic bugs.
