# cuDF — GPU DataFrame (usage · navigation · troubleshooting)

Repo `/home/gio/tese/rapids/cudf`. Pandas-like API on GPU.

## Layers — which owns a symptom

| Layer | Location | Owns |
| --- | --- | --- |
| **libcudf** (C++/CUDA) | `cpp/include/cudf/` (headers), `cpp/src/<algo>/` (kernels) | algorithms, dtype dispatch, OOM at alloc site, overflow, string 2GB limit |
| **pylibcudf** (thin Cython) | `python/pylibcudf/pylibcudf/*.pyx` | 1:1 binding; error-code→exception (`exception_handler.pxd`) |
| **cudf Python** (pandas-like) | `python/cudf/cudf/core/` | DataFrame/Series/Index semantics, index alignment, nullability, dtype promotion, groupby order |
| **cudf.pandas** | `python/cudf/cudf/pandas/` | import hook + fast/slow proxy; CPU fallbacks |
| **dask-cudf** | `python/dask_cudf/dask_cudf/` | partitioned / multi-GPU / out-of-core |
| **cudf-polars** | `python/cudf_polars/cudf_polars/` | Polars LazyFrame GPU engine |

Note: `python/cudf/cudf/_lib/` is now nearly empty (only `strings_udf.pyx`) — the old `_lib`
Cython was migrated into **pylibcudf**. Routing today: `cudf.core.*` → `pylibcudf.*` → libcudf.

Heuristic: wrong numeric result/crash → **libcudf** (`cpp/src/`); "pandas does X, cudf does Y"
→ **cudf Python** (`core/`); slow after `import cudf.pandas` → **fallback** (`pandas/profiler.py`);
OOM → RMM alloc inside libcudf, mitigated by spill (`core/buffer/`).

## Usage — key files

- Core objects: `core/dataframe.py`, `series.py`, `index.py`, `multiindex.py`,
  `indexed_frame.py`, `frame.py`.
- IO entry points: `io/parquet.py`, `csv.py`, `orc.py`, `json.py`, `avro.py`, `text.py`,
  `dlpack.py` (dispatched from `cudf.read_parquet` etc.).
- groupby/agg: `core/groupby/groupby.py`; join/merge: `core/join/{join,_join_helpers}.py`;
  strings `.str`: `core/column/string.py` + `core/accessors/`; rolling/window: `core/window/`;
  UDFs (numba `apply`/`applymap`/`apply_chunks`): `core/udf/` (+ device string UDFs
  `_lib/strings_udf.pyx`); categorical/dtypes: `core/column/categorical.py`, `core/dtypes.py`.
- Interop `.to_pandas()`/`from_pandas`/`.to_cupy()`, CAI, DLPack: `pylibcudf/interop.pyx`,
  `io/dlpack.py`, column buffers in `core/buffer/`.

```python
import cudf
df = cudf.read_parquet("f.parquet")            # -> io/parquet.py -> pylibcudf/io -> cpp/src/io/parquet
g  = df.groupby("k", sort=True).agg({"v":"sum"})
m  = df.merge(other, on="id", how="inner")     # -> core/join/join.py -> pylibcudf/join.pyx -> cpp/src/join
s  = df["name"].str.upper()
cp = df["v"].to_cupy()                          # zero-copy via __cuda_array_interface__
```

## cudf.pandas (zero-code-change) — `python/cudf/cudf/pandas/`

- **How**: `module_accelerator.py` (`ModuleAccelerator`, a `MetaPathFinder`) installed by
  `install()` in `__init__.py:33` → intercepts `import pandas`. `fast_slow_proxy.py`
  (`_FastSlowProxy`, `_FastSlowProxyMeta`, `_fast_arg`/`_slow_arg`) runs on GPU ("fast") and on a
  GPU exception **retries on CPU** ("slow").
- **Enable**: `python -m cudf.pandas script.py` (`__main__.py`), `%load_ext cudf.pandas`
  (`magics.py`), or `import cudf.pandas; cudf.pandas.install()`.
- **Debug fallbacks**: `profiler.py` (`Profiler`, `per_function_stats`,
  `format_cpu_functions_used`) via `%%cudf.pandas.profile`; `_logger.py`, `annotation.py` (NVTX).
  Docs: `docs/cudf/source/cudf_pandas/{how-it-works,usage,faq}.md`.

## Navigation for troubleshooting (C++)

Algorithm groups `cpp/src/`: `join/`, `groupby/`, `strings/`, `io/`, `copying/`, `reductions/`,
`sort/`, `merge/`, `stream_compaction/`, `binaryop/`, `rolling/`, `search/`, `unary/`,
`transform/`, `hash/`, `structs/`, `lists/`, `text/`, `datetime/`, `dictionary/`.

- **type_dispatcher** — `cpp/include/cudf/utilities/type_dispatcher.hpp`: `type_to_id<T>()`, the
  `CUDF_TYPE_MAPPING` macro table, and `type_dispatcher(data_type, functor)` fanning a runtime
  `type_id` to a compile-time functor. Central to "unsupported dtype" errors.
- **IO parsers** — `cpp/src/io/{csv,json,orc,parquet,avro,text,comp,fst}/`; public C++ API
  `cpp/src/io/functions.cpp`.

## Troubleshooting

| Symptom | Cause | Fix / source |
| --- | --- | --- |
| OOM on large join/groupby | libcudf alloc via RMM | Enable **spilling**: `CUDF_SPILL=on` or `cudf.set_option("spill", True)` (`core/buffer/spill_manager.py`); use **chunked/low-memory readers** (`io.parquet(..., low_memory=...)`); see doc 01 |
| Silent wrong result on big ints | integer overflow wraps (no auto-upcast) | `cpp/src/reductions/`, `cpp/src/binaryop/` — cast dtype up first |
| String op fails on huge column | 32-bit offset 2GB limit (`size_type`) | `cpp/src/strings/strings_column_factories.cu`, `cpp/include/cudf/strings/detail/utilities.hpp`; use large_strings support / split |
| groupby order differs from pandas | hash groupby unordered | pass `sort=True` (`core/groupby/groupby.py`) |
| NaN vs null surprises | cuDF uses a validity bitmask separate from float NaN | `core/missing.py`, `cpp/include/cudf/null_mask.hpp`; set `cudf.set_option("mode.pandas_compatible", True)` |
| Index/alignment differs from pandas | cuDF realigns like pandas but with its own rules | `core/indexed_frame.py`, `core/index.py` |
| Slow after `import cudf.pandas` | ops falling back to CPU | `pandas/profiler.py` |

**Option/env knobs** (`python/cudf/cudf/options.py`): `CUDF_SPILL`, `CUDF_SPILL_ON_DEMAND`,
`CUDF_SPILL_DEVICE_LIMIT`, `CUDF_SPILL_STATS` (1=bytes/time, 2=tracebacks), `CUDF_MEMORY_PROFILING`,
and options `mode.pandas_compatible`, `default_float_bitwidth`, `default_integer_bitwidth`.
Spill stats print on OOM (`spill_manager.py` `SpillStatistics`). libcudf logger
`cpp/include/cudf/logger.hpp`.

## pandas-compat gotchas

- `mode.pandas_compatible` (`options.py:276`) tightens semantics toward pandas.
- **NaN vs null**: separate concepts; in non-compat mode NaN may be treated as null in
  reductions/groupby.
- **No auto-upcast on overflow** (unlike some pandas paths).
- **Output order** of groupby/join differs unless `sort=True`.
- Dtype promotion controlled by `default_float_bitwidth`/`default_integer_bitwidth`.
