# cuML — GPU Machine Learning (usage · navigation · troubleshooting)

Repo `/home/gio/tese/rapids/cuml`. scikit-learn-compatible estimators on GPU. **Read
`wiki/python/ESTIMATOR_GUIDE.md` first** — it is the authoritative estimator contract.

## Layers

- **C++ core** — `cpp/src/<algo>/` (algorithms) + `cpp/src_prims/` (primitives: linalg, matrix,
  random, selection, sparse, distance, opg). Headers `cpp/include/cuml/`.
- **Cython estimators** — `python/cuml/cuml/<family>/*.pyx` bridge to `libcuml++`.
- **RAFT / cuVS** — GPU handle/stream is `raft::handle_t` (alias `device_resources`); in Python
  `pylibraft.common.handle.Handle` via `get_handle()` (`internals/base.py:23`). Neighbors/ANN
  increasingly delegate to **cuVS**. (RAFT/cuVS source is cloned at `rapids/raft`, `rapids/cuvs`;
  Thrust/CUB/libcudacxx at `rapids/cccl` — read them when a cuML trail bottoms out in a primitive.)

Family map (C++ `cpp/src/` → Python `python/cuml/cuml/`): glm/solver → `linear_model/`,`solvers/`;
kmeans/dbscan/hdbscan/hierarchy/spectral → `cluster/`; pca/tsvd → `decomposition/`; umap/tsne →
`manifold/`; knn → `neighbors/`; svm → `svm/`; randomforest/decisiontree → `ensemble/`;
arima/tsa/holtwinters/metrics/kde/explainer/genetic → `tsa/`,`metrics/`,`explainer/`, etc.
Multi-GPU `*_mg.pyx` pair with Dask wrappers in `python/cuml/cuml/dask/<family>/`.

## Usage — the estimator contract

- All estimators inherit `cuml.internals.base.Base` (`internals/base.py:54`), sklearn
  `fit`/`predict`/`transform`. Import `from cuml import KMeans` or `from cuml.cluster import KMeans`.
- **Inputs**: cuDF DataFrame/Series, cupy, numpy, numba arrays, anything with CAI; sparse where
  declared. Validation: `internals/validation.py` (`check_array`, `check_y`, `check_is_fitted`).
- **Output type** (precedence: global > estimator): `MyEst(output_type="numpy")`,
  `cuml.set_global_output_type("numpy")`, or `with cuml.using_output_type("numpy"):`. Machinery
  `internals/outputs.py`, `base.py:216 _set_output_type`. Values: `input`, `cupy`, `numpy`,
  `cudf`, `pandas`, `numba`, `dataframe`, `series`.
- **CumlArray** (`internals/array.py`) — internal GPU array; fitted attrs are
  `CumlArrayDescriptor` (`common/array_descriptor.py`) that lazily convert on read.
- `_get_param_names()` drives `get_params`/cloning (must call `super()._get_param_names()`).

```python
from cuml.cluster import KMeans
km = KMeans(n_clusters=8, random_state=0).fit(X)      # X: cudf/cupy/numpy/CAI
labels = km.predict(X)                                # array per output_type
import cuml
with cuml.using_output_type("numpy"):
    emb = cuml.manifold.UMAP(n_neighbors=15).fit_transform(X)
```

## cuml.accel — zero-code-change sklearn accelerator (`python/cuml/cuml/accel/`)

- **Enable**: `python -m cuml.accel myscript.py` (`accel/__main__.py`), `%load_ext cuml.accel`
  (`accel/magics.py`), or `from cuml.accel import install; install()`.
- **How**: `install()` (`accel/core.py:206`) sets `CUML_ACCEL_ENABLED=1`, configures managed
  memory (UVM via RMM `PrefetchResourceAdaptor(ManagedMemoryResource)` unless disabled/WSL2), and
  activates the import hook `Accelerator` (`accel/accelerator.py`) that swaps sklearn classes for
  GPU proxies. Overrides in `accel/_overrides/sklearn/{cluster,linear_model,neighbors,svm,...}.py`
  + top-level `umap.py`, `hdbscan.py`; patches `accel/_patches/sklearn/`.
- **Dispatch + fallback**: `accel/estimator_proxy.py` `ProxyBase` holds `_cpu` (real sklearn) and
  `_gpu` (cuML); tries GPU, on `UnsupportedOnGPU` (`internals/interop.py:39`) **falls back to CPU**.
- **See what accelerated vs fell back**: `install(log_level="debug")` or
  `CUML_ACCEL_LOG_LEVEL=debug` (`core.py:229`), or `-vv` on the CLI — prints `[cuml.accel] ...`
  dispatch + sync lines.

## Navigation for troubleshooting

- Estimator base + output resolution: `internals/base.py`, `internals/outputs.py`; array
  `internals/array.py`; sklearn interop `internals/interop.py`; tags/mixins `internals/mixins.py`.
- **Cython → C++ crossing** (e.g. `cluster/kmeans.pyx`): `cimport cuml.cluster.cpp.kmeans`; `fit()`
  gets the handle (`base.py:585 get_handle()`), casts to `handle_t*`, calls `lib._kmeans_fit(...)`
  into `libcuml++`. C++ prototypes under each family's `cpp/` subdir mirroring `cpp/include/cuml/`.
- **FIL** (forest inference): `python/cuml/cuml/fil/` is now a **compat shim** (`fil/compat.py`)
  delegating to the external `nvforest` package (marked for removal 26.10). `ForestInference`
  re-exported from `fil/__init__.py`.
- **Multi-GPU**: `python/cuml/cuml/dask/<family>/` wrap `*_mg.pyx`; shared `dask/common/`,
  comms `python/cuml/cuml/comm/`.

## Troubleshooting

| Symptom | Cause | Fix / source |
| --- | --- | --- |
| Results differ from sklearn | different default solver/init/tol; GPU float32; non-deterministic reductions | check constructor defaults (`random_state`, `tol`, `max_iter`, `init`, `solver`) in the family `.pyx`; cuML isn't bit-identical — use `cuml.accel` for parity |
| Got cupy when you wanted numpy | output_type precedence (global > estimator) | pass `output_type="numpy"` or `with cuml.using_output_type("numpy")` (`base.py:226`) |
| OOM | O(n²) memory in pairwise / UMAP / TSNE / HDBSCAN | lower `n_neighbors`, batch (`DBSCAN max_mbytes_per_batch`), enable UVM (cuml.accel does via RMM managed mem; **not on WSL2**) |
| dtype error | estimator is float32-first; float64 support varies | `check_inputs(..., convert_dtype=...)` in `fit`; grep the `.pyx` for `dtype=` |
| Non-determinism | atomic reductions, multi-stream | `random_state` fixes init not all reductions |
| RAFT/cuVS runtime error | version skew | verify pylibraft/cuvs match cuml (`accel/core.py CheckConstraint` warns) |
| cuml.accel ran on CPU silently | method hit `UnsupportedOnGPU` | `CUML_ACCEL_LOG_LEVEL=debug` shows the fallback (`estimator_proxy.py:305`) |
| FIL model load fails | treelite/nvforest version or unsupported objective | `fil/compat.py`, `docs/source/FIL.rst` |
| Sparse input rejected | only `SparseInputTagMixin` estimators accept sparse | `internals/array_sparse.py`, `common/sparse.py` |

**Debug knobs**: estimator `verbose=int` → `internals/logger.pyx`; `cuml.internals.logger.set_level(...)`;
`CUML_ACCEL_ENABLED`, `CUML_ACCEL_LOG_LEVEL`; `NVTX_BENCHMARK` env (`base.py:124`).

## sklearn-compat caveats

Not exact API parity (cuML omits unusable params, may differ in defaults — use `cuml.accel` for
drop-in). GPU float32 defaults + different solvers → close-but-not-identical numerics. Attributes
are CumlArray-backed and convert per `output_type`. Don't mutate constructor params in `__init__`
(breaks cloning). Convert with `InteropMixin.as_sklearn()`/`from_sklearn()` (`internals/interop.py`).

Open-first when debugging: `internals/base.py`, `internals/outputs.py`, `internals/validation.py`,
`internals/interop.py`, the family `.pyx`, and for accel `accel/core.py` + `accel/estimator_proxy.py`.
