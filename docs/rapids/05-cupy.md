# CuPy — GPU ndarray (usage · navigation · troubleshooting)

Repo `/home/gio/tese/rapids/cupy`. NumPy/SciPy-compatible GPU array library. `cupy` = numpy
drop-in; `cupyx` = scipy-compatible extras + advanced tooling. Performance core is Cython
(`.pyx`/`.pxd`). **Not** a RAPIDS repo but the shared array substrate the RAPIDS stack interops with.

## Layers — where things live

- **ndarray core**: `cupy/_core/core.pyx` (`cupy.ndarray`), `_core/_dtype.pyx`, `_core/_scalar.pyx`,
  `_core/_carray.pyx` (kernel descriptor).
- **ufunc / elementwise / reduction**: `_core/_kernel.pyx` (`ElementwiseKernel`, ufuncs),
  `_core/_reduction.pyx` (`ReductionKernel`), `_core/_cub_reduction.pyx`.
- **Kernel fusion** (`cp.fuse`): `_core/fusion.pyx` (`fuse` @888), `_core/new_fusion.pyx`.
- **Raw CUDA compile path**: `_core/raw.pyx` (`RawKernel`, `RawModule`) → `cupy/cuda/compiler.py`
  (NVRTC/nvcc; note it's `.py`), `cupy/cuda/jitify.pyx`, launch in `cupy/cuda/function.pyx`.
- **CUDA runtime**: `cupy/cuda/` — `memory.pyx` (pools/allocators), `device.pyx` (`Device`),
  `stream.pyx` (`Stream`, `Event`), `runtime.py`, `graph.pyx`, `pinned_memory.pyx`, `nccl.py`.
  C shims: `cupy_backends/`.
- **numpy-API namespace** (`cp.*`): dispatched from `cupy/__init__.py` into `cupy/_math/`,
  `_sorting/`, `_statistics/`, `_logic/`, `_manipulation/`, `_indexing/`, `_creation/`, `linalg/`,
  `fft/`, `random/`. Kernels in `_core/_routines_*.pyx`.
- **cupyx**: `cupyx/scipy/*` (sparse, ndimage, signal, fft, linalg, special, stats), JIT
  `cupyx/jit/`, `cupyx/time.py` (`repeat` benchmark).
- Note: `cupyx.fallback_mode` is **not present** in this checkout (removed) — don't reference it.

## Usage — canonical snippets

```python
import cupy as cp
a = cp.asarray(np_arr)          # host->device
h = cp.asnumpy(a)               # or a.get()  -> device->host (SYNCS)

with cp.cuda.Device(1):         # device.pyx
    x = cp.arange(10)

s = cp.cuda.Stream(non_blocking=True)   # stream.pyx
with s: y = x * 2
s.synchronize()
e1, e2 = cp.cuda.Event(), cp.cuda.Event()
e1.record(); ...; e2.record(); e2.synchronize()
ms = cp.cuda.get_elapsed_time(e1, e2)   # correct GPU timing

mp = cp.get_default_memory_pool()       # memory.pyx
mp.free_all_blocks()                    # return cached blocks to driver
cp.cuda.set_allocator(cp.cuda.MemoryPool(cp.cuda.malloc_managed).malloc)   # unified memory
import rmm; from rmm.allocators.cupy import rmm_cupy_allocator
cp.cuda.set_allocator(rmm_cupy_allocator)   # share ONE pool with cuDF/cuML

# custom kernels
k  = cp.ElementwiseKernel('T x, T y', 'T z', 'z = x + y', 'add')         # _core/_kernel.pyx
r  = cp.ReductionKernel('T x','T y','x','a+b','y=a','0','sum')           # _core/_reduction.pyx
rk = cp.RawKernel(r'extern "C" __global__ void my(const float* a){}', 'my')  # _core/raw.pyx
rk((grid,), (block,), (arg,))
from cupyx import jit
@jit.rawkernel()                          # cupyx/jit/_interface.py
def elem(x, y, size): ...

# interop
import cupy; arr = cupy.from_dlpack(df.to_dlpack())   # _core/dlpack.pyx
```

## Navigation for troubleshooting

- ndarray methods/behavior → `_core/core.pyx`.
- kernel launch / arg packing → `_core/_kernel.pyx`, `cupy/cuda/function.pyx`.
- allocation/OOM → `cupy/cuda/memory.pyx` (`OutOfMemoryError` @55, `MemoryPool` @1566,
  `free_all_blocks` @1400, `set_allocator` @907, `malloc_managed` @803).
- compile errors → `cupy/cuda/compiler.py`, `cupy/cuda/jitify.pyx`.
- a missing `cp.foo` → grep `cupy/_math`, `cupy/_sorting`, ... then `_core/_routines_*.pyx`.

## Troubleshooting

| Symptom | Cause | Fix / source |
| --- | --- | --- |
| "arrays are on different devices" | operands under different `Device()` contexts | move with `cp.asarray(x)` inside the target `with Device(n):`; keep ops in one device scope |
| `OutOfMemoryError` | pool holds freed-but-cached blocks | `cp.get_default_memory_pool().free_all_blocks()`; `mempool.set_limit(size=...)` / env `CUPY_GPU_MEMORY_LIMIT`; unified memory; or wire RMM (`memory.pyx:1479+`) |
| Timing looks instant / wrong | kernels are async — wall clock measures launch only | `Stream.synchronize()` or `Event`+`get_elapsed_time`, or `cupyx.time.repeat` |
| Kernel won't compile | NVRTC error, header/signature mismatch | `CUPY_DUMP_CUDA_SOURCE_ON_ERROR=1` prints generated source; `CUPY_CUDA_COMPILE_WITH_DEBUG=1` (`-G`); RawKernel args must match C types exactly (`float*`→`float32`); pass `options=('-I...',)`; cache `CUPY_CACHE_DIR` |
| `.get()`/`asnumpy` slow in a loop | implicit full sync + PCIe copy | keep data on device; batch transfers |
| `cudaErrorInsufficientDriver` / import fails | wheel CUDA toolkit newer than driver, or wrong wheel | match `cupy-cuda12x` vs `cupy-cuda13x` to driver/toolkit; `cupy/_environment.py` locates CUDA/cuDNN/NCCL and raises actionable errors |
| dtype surprises / slow matmul | silent upcast / TF32 off | check `_core/_dtype.pyx`; `CUPY_TF32=1` enables tensor-core matmul |

**Env knobs**: `CUPY_CACHE_DIR`, `CUPY_ACCELERATORS` (default `cub`; e.g. `cub,cutensor`),
`CUPY_DUMP_CUDA_SOURCE_ON_ERROR`, `CUPY_CUDA_COMPILE_WITH_DEBUG`, `CUPY_TF32`, `CUPY_GPU_MEMORY_LIMIT`.

## RAPIDS interop

- **Zero-copy**: cuDF/cuML columns ↔ CuPy via `__cuda_array_interface__` (`cudf.Series.values` →
  `cupy.ndarray`, no copy) and DLPack (`cp.from_dlpack`, `_core/dlpack.pyx`). CuPy arrays feed
  cuML estimators directly through CAI.
- **Shared RMM pool**: `cp.cuda.set_allocator(rmm.allocators.cupy.rmm_cupy_allocator)` so CuPy and
  cuDF/cuML draw from one RMM pool — one reservation, fewer OOMs. CuPy only exposes the
  `set_allocator` hook (`cupy/cuda/memory.pyx`); RMM is external.
