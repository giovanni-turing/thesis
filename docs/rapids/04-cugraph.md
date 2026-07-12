# cuGraph — GPU Graph Analytics (usage · navigation · troubleshooting)

Repo `/home/gio/tese/rapids/cugraph`. NetworkX-like API on GPU over cuDF edgelists.

## Layers — which owns a symptom

1. **libcugraph (C++/CUDA)** — `cpp/src/<family>/`. Each algo: `_impl.cuh` (logic) + explicit
   instantiations `*_sg_v32_e32.cu`, `*_mg_v64_e64.cu` (sg/mg = single/multi-GPU; v32/v64 =
   int32/int64 vertex, e32/e64 = edge id width). Headers `cpp/include/cugraph/`. **Owns:** wrong
   results, convergence, perf, OOM.
2. **libcugraph_c (stable C API)** — headers `cpp/include/cugraph_c/*.h`, impl `cpp/src/c_api/*.cpp`.
   **Owns:** dtype/handle errors as `cugraph_error_t`, arg validation.
3. **pylibcugraph (thin Cython)** — `python/pylibcugraph/pylibcugraph/*.pyx` + `_cugraph_c/*.pxd`.
   **Owns:** cudf/cupy→C array marshaling.
4. **cugraph (Python)** — `python/cugraph/cugraph/<family>/`. **Owns:** graph objects,
   renumbering, DataFrame in/out, symmetrization.
5. **cugraph.dask (multi-GPU)** — `python/cugraph/cugraph/dask/<family>/` → `*_mg_*` C++.

Split-out (not here): `nx-cugraph` (NetworkX backend, separate package), `cugraph-dgl`/`cugraph-pyg`
(GNN; only sampling primitives remain). READMEs: `readme_pages/{libcugraph,pylibcugraph,cugraph_python,data_types,gnn_support}.md`.

## Usage

Graph construction — `python/cugraph/cugraph/structure/graph_classes.py`: `Graph(directed=False)`,
`MultiGraph` (parallel edges), builders `from_cudf_edgelist(...)` (line 103), `from_pandas_edgelist`,
`from_dask_cudf_edgelist` (MG). Key kwargs: `source`, `destination`, `edge_attr` (weight),
`renumber=True`, `store_transposed`, `symmetrize`.

```python
import cudf, cugraph
df = cudf.read_csv("edges.csv")   # vertices int32/int64, weight float32/64
G = cugraph.Graph(directed=True)
G.from_cudf_edgelist(df, source="src", destination="dst", edge_attr="wgt", renumber=True)
pr    = cugraph.pagerank(G, alpha=0.85, tol=1e-5, max_iter=100)   # -> cudf DF[vertex, pagerank]
parts = cugraph.louvain(G)                                        # -> (DF[vertex,partition], modularity)
dist  = cugraph.sssp(G, source=0);  bfs = cugraph.bfs(G, start=0)
jac   = cugraph.jaccard(G)
from cugraph.sampling.homogeneous_neighbor_sample import homogeneous_neighbor_sample
samp  = homogeneous_neighbor_sample(G, start_list=seeds, fanout_vals=[10,5])
```

Family → Python module (`python/cugraph/cugraph/`): pagerank/hits → `link_analysis/`;
betweenness/katz/eigenvector/degree → `centrality/`; louvain/leiden/ecg/triangle/ktruss/egonet →
`community/`; WCC/SCC → `components/connectivity.py`; core_number/k_core → `cores/`; bfs/sssp →
`traversal/`; jaccard/overlap/sorensen/cosine → `link_prediction/`; neighbor-sample + random-walks
→ `sampling/`; force_atlas2 → `layout/`. **Note**: the old single `uniform_neighbor_sample` is
superseded by `homogeneous_neighbor_sample`/`heterogeneous_neighbor_sample` in this version.

## Key concepts for troubleshooting

- **Renumbering** — `structure/number_map.py` (`NumberMap`). `renumber=True` (default) remaps
  arbitrary/int64/string vertex IDs to dense `[0,V)`, so **results reference internal IDs**. Map
  back: `G.unrenumber(df, column_name)` (`graph_classes.py:546` → `NumberMap.unrenumber`). C++:
  `cpp/src/structure/renumber_edgelist_impl.cuh`.
- **Directed vs undirected** — `Graph(directed=)`; undirected symmetrizes the edgelist (stores
  both directions). Passing `symmetrize=True` to a directed graph errors. C++:
  `cpp/src/structure/symmetrize_*`.
- **Weighted vs unweighted** — presence of `edge_attr`. No weights → sssp is BFS-equivalent.
- **cudf edgelist contract** — vertices int32/int64, weights float32/64. Mismatched width routes
  to the wrong `v32/v64` instantiation → C API dtype error. See `readme_pages/data_types.md`.

## Navigation — routing a call (pagerank example)

`link_analysis/pagerank.py:69` → `pylibcugraph/pagerank.pyx` (calls `cugraph_pagerank`) → C API
decl `cpp/include/cugraph_c/centrality_algorithms.h`, impl `cpp/src/c_api/pagerank.cpp` → core
`cpp/src/link_analysis/pagerank_impl.cuh` (+ `pagerank_sg/mg_v32/v64` instantiations).

C++ family dirs: `centrality/`, `link_analysis/` (pagerank/hits), `community/`, `components/`,
`cores/`, `traversal/`, `link_prediction/`, `sampling/`, `structure/` (build/renumber/symmetrize/
transpose), `layout/`, `mtmg/` (multi-GPU). C API surface: `cpp/include/cugraph_c/*.h`, impl
`cpp/src/c_api/`. Deps: RAFT/pylibraft, RMM, cuDF/cupy, Thrust/CUB; Dask for MG. `cugraph-ops`
(closed) historically needed for some GNN sampling.

## Troubleshooting

| Symptom | Cause | Fix / source |
| --- | --- | --- |
| Result vertex IDs don't match input | renumbering to `[0,V)` | `G.unrenumber(df, col)` (`graph_classes.py:546`); or `renumber=False` if IDs already dense |
| C API dtype / "unsupported type" | vertices not int32/64, or weights not float | cast before `from_cudf_edgelist`; `readme_pages/data_types.md` |
| Directed/undirected wrong, or symmetrize error | `directed=`/`symmetrize=` mismatch | `graph_classes.py` docstrings; `cpp/src/structure/symmetrize_*` |
| OOM on large graph | single-GPU memory | switch to `cugraph.dask.*` + `from_dask_cudf_edgelist`; C++ `*_mg_*.cu` |
| Extra/odd components | disconnected / undirected assumption | `strongly_` vs `weakly_connected_components` (`components/connectivity.py`) |
| Self-loops/multi-edges skew results | not removed | use `Graph` (dedups) not `MultiGraph`; `cpp/src/structure/remove_{self_loops,multi_edges}_impl.cuh` |
| Empty results / KeyError on vertices | vertex absent after renumber, or wrong start id | check `NumberMap.to_internal_vertex_id` |
| PageRank non-convergence | `tol`/`max_iter` tight, dangling nodes | `link_analysis/pagerank.py:69`; raises `FailedToConvergeError` (`cugraph/exceptions.py`) |
| Differs from NetworkX | symmetrization, tie-breaking, renumber ordering, normalization | check directed flag + weights; nx-cugraph is a separate package |
| GNN sampling import/op fails | missing `cugraph-ops` / split GNN pkg | `readme_pages/gnn_support.md`; use `cugraph-dgl`/`cugraph-pyg` |

**Debug knobs**: `renumber=False` to bypass mapping; run single-GPU before scaling to dask;
inspect `G.edgelist.edgelist_df` / `G.renumber_map`; typed errors in `cugraph/exceptions.py`.

## GNN note

Framework integrations (`cugraph-dgl`, `cugraph-pyg`) are split into separate packages. What
remains here: sampling primitives `sampling/{homogeneous,heterogeneous}_neighbor_sample.py`,
pylibcugraph `*_neighbor_sample.pyx`, C++ `cpp/src/sampling/` (`neighbor_sampling_impl.cuh`),
C API `cpp/include/cugraph_c/sampling_algorithms.h`.
