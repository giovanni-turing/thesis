# RMM — Memory Manager (usage · navigation · troubleshooting)

Repo `/home/gio/tese/rapids/rmm`. Canonical usage docs: `README.md`,
`docs/user_guide/guide.md`. RMM is the allocator the **whole** RAPIDS stack draws from, so most
GPU-memory debugging starts here.

## Layers

- **C++ librmm** — `cpp/include/rmm/` (mostly header-only templates + small compiled lib).
  Public MR umbrella `cpp/include/rmm/mr/`; internals `cpp/include/rmm/mr/detail/`.
- **Cython** — `python/rmm/rmm/librmm/*.pxd` (raw `cdef extern` of the C++ API) +
  `python/rmm/rmm/pylibrmm/` (impl: `memory_resource/_memory_resource.pyx` has ALL MR classes,
  `device_buffer.pyx`, `stream.pyx`, `logger.pyx`).
- **Python** — `python/rmm/rmm/`: `__init__.py`, `rmm.py` (`reinitialize` + hooks),
  `mr/__init__.py` (re-exports MR classes), `allocators/`, `statistics.py`.
- Wheel-only native loader: `python/librmm/librmm/load.py`.

## Usage

**Quick pool (most common):**
```python
import rmm
rmm.reinitialize(pool_allocator=True, initial_pool_size="2GiB", maximum_pool_size="16GiB")
```
`reinitialize(...)` is `python/rmm/rmm/rmm.py:20` → `_initialize` in
`pylibrmm/memory_resource/_memory_resource.pyx:1006` (builds Cuda/Managed upstream, optional
`PoolMemoryResource`, optional logging, then `set_per_device_resource` per device).
`parse_bytes` accepts `"2GiB"`.

**Manual wiring:**
```python
from rmm.mr import CudaMemoryResource, PoolMemoryResource, set_current_device_resource
set_current_device_resource(PoolMemoryResource(CudaMemoryResource(), initial_pool_size="1GiB"))
```

**MR classes** (all in `pylibrmm/memory_resource/_memory_resource.pyx`, re-exported via
`rmm/mr/__init__.py`):
- Leaf: `CudaMemoryResource` (cudaMalloc), `CudaAsyncMemoryResource` (cudaMallocAsync pool),
  `ManagedMemoryResource` (UVM), `SystemMemoryResource`, `PinnedHostMemoryResource`,
  `SamHeadroomMemoryResource`.
- Sub-allocators (take an upstream): `PoolMemoryResource` (`initial_pool_size`,
  `maximum_pool_size`, `.pool_size()`), `ArenaMemoryResource` (per-thread arenas, less
  fragmentation, `arena_size`), `FixedSizeMemoryResource`, `BinningMemoryResource` (`.add_bin()`).
- Adaptors (wrap an MR to instrument): `LoggingResourceAdaptor`, `StatisticsResourceAdaptor`
  (`.allocation_counts`, push/pop), `TrackingResourceAdaptor` (`.get_outstanding_allocations_str()`),
  `LimitingResourceAdaptor` (`.get_allocation_limit()`), `FailureCallbackResourceAdaptor`
  (OOM-retry callback), `CallbackMemoryResource`, `PrefetchResourceAdaptor`.

**Current-resource getters/setters** (same pyx): `set_current_device_resource` (:1118),
`get_current_device_resource` (:1131), `set_per_device_resource` (:1092),
`available_device_memory` (:1236).

**DeviceBuffer** — `pylibrmm/device_buffer.pyx`: owning device allocation, `.ptr`, `.size`,
`__cuda_array_interface__`, `copy_to_host`.

**Wire other frameworks to RMM** (`python/rmm/rmm/allocators/`):
```python
import cupy; from rmm.allocators.cupy import rmm_cupy_allocator
cupy.cuda.set_allocator(rmm_cupy_allocator)                 # cupy.py:14
from numba import cuda; from rmm.allocators.numba import RMMNumbaManager
cuda.set_memory_manager(RMMNumbaManager)                    # numba.py:48  (or env NUMBA_CUDA_MEMORY_MANAGER)
import torch; from rmm.allocators.torch import rmm_torch_allocator
torch.cuda.memory.change_current_allocator(rmm_torch_allocator)   # torch.py (None if no CUDA!)
```

## The process-global current resource (why it matters)

A **process-global map: device id → memory_resource** (C++ `cpp/include/rmm/mr/per_device_resource.hpp`;
Python `_per_device_mrs` = `defaultdict(CudaMemoryResource)` at `_memory_resource.pyx:1003`).
cuDF/cuML/cuGraph and all RMM containers call `get_current_device_resource()` **at allocation
time** with no MR argument. Consequences:
1. Set the resource **before** any library allocates (else early allocations use plain cudaMalloc).
2. It's **per-device** — set each GPU in a multi-GPU process.
3. The resource object must **outlive** all allocations (dangling-resource crash at shutdown —
   `cpp/include/rmm/process_is_exiting.hpp`).

## C++ concepts (for reading errors / source)

- `device_async_resource_ref` (`cpp/include/rmm/resource_ref.hpp`) — non-owning type-erased
  handle passed everywhere; what per_device_resource stores.
- Containers: `device_buffer.hpp` (untyped), `device_uvector.hpp` (typed, stream-ordered),
  `device_scalar.hpp`.
- `cpp/include/rmm/mr/detail/stream_ordered_memory_resource.hpp` — CRTP base for
  pool/arena/fixed-size (enforces stream-ordered alloc/free). Internals: `detail/arena.hpp`,
  `coalescing_free_list.hpp`, `fixed_size_free_list.hpp`.
- Public MR headers `cpp/include/rmm/mr/*.hpp` (one per Python class).
- Errors: `cpp/include/rmm/error.hpp` (`rmm::out_of_memory`, `rmm::bad_alloc`),
  `cpp/include/rmm/detail/error.hpp`.

## Troubleshooting

| Symptom | Cause | Diagnose / fix (source) |
| --- | --- | --- |
| OOM / `cudaErrorMemoryAllocation` / `rmm::out_of_memory` | pool exhaustion or leaf alloc fail | Wrap MR in `StatisticsResourceAdaptor` (peak bytes via `.allocation_counts`) or `LimitingResourceAdaptor` to fail early. Thrown from `mr/cuda_memory_resource.hpp` / `pool_memory_resource.hpp` |
| Fragmentation (free bytes exist, no contiguous block) | pool free-list fragmented | Switch `PoolMemoryResource` → `ArenaMemoryResource`; read `detail/arena.hpp`, `coalescing_free_list.hpp` |
| Corruption / use-after-free across streams | freeing on wrong stream (UB — allocations are stream-ordered) | Ensure `Stream` passed to `DeviceBuffer` (`pylibrmm/stream.pyx`) matches the compute stream; see `detail/stream_ordered_memory_resource.hpp` |
| Some ptrs can't be freed by the pool | mixing RMM with default `cudaMalloc` | Wire *every* framework to RMM (cupy/torch/numba allocators above) |
| `rmm_torch_allocator is None` | `_torch_allocator.so` missing or torch has no CUDA | check torch CUDA build; source `python/rmm/rmm/librmm/_torch_allocator.cpp` |
| Memory leak | unfreed allocations | `TrackingResourceAdaptor.get_outstanding_allocations_str()` / `.log_outstanding_allocations()` prints stack traces (`_memory_resource.pyx:872`; `cpp/include/rmm/detail/stack_trace.hpp`). Scope with `StatisticsResourceAdaptor` push/pop + `statistics.py` `ProfilerContext` |
| Need to trace every alloc/free | — | `LoggingResourceAdaptor` (CSV). Enable: `rmm.reinitialize(logging=True, log_file_name=...)`, `rmm.enable_logging()`, or env `RMM_LOG_FILE` (Python) / `RMM_DEBUG_LOG_FILE` (C++). Names via `rmm.get_log_filenames()` |

## Interop touchpoints

cudf/cuml/cugraph allocate implicitly through the current resource (nothing to wire beyond
setting it) and register **reinitialize hooks** (`rmm.py:93`, `register_reinitialize_hook`) to
drop cached memory before teardown. CuPy/torch/numba plug in via the allocators above.
`DeviceBuffer.__cuda_array_interface__` + the stream protocol (`pylibrmm/stream.pyx`) are the
zero-copy data-exchange contracts.
