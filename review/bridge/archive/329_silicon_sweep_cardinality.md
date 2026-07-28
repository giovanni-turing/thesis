---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D99-silicon-sweep-cardinality
---

# D99 — The defense puts all 69 silicon points inside the $N\le64$ regime

The new story spine says the 12.8% agreement holds “over 69 batch sizes,
$N\le64$” (`defense/defense-qa.tex:122-123`), and the cram card calls it a
“69-point dense sweep” while attaching $N\le64$
(`defense/defense-qa.tex:2471-2474`).

The artifact has 69 points total, but only 64 are in-cap: dense integer
$N=1,\ldots,64$, followed by five off-cap probes
$N=\{96,128,192,256,512\}$
(`simulation/results/silicon_anchor/reps/engine__vllm_serving/vllm_eager_dense_rerun.json:10-21`;
`simulation/results/silicon_anchor/reps/engine__vllm_serving/vllm_eager_dense_rerun.json:507-562`).
The manuscript states the design correctly as a dense 1--64 sweep plus five
off-cap probes (`tex/metodologia.tex:269-275`).

Please say either “all 64 in-cap points” or “the 69-point sweep, comprising 64
in-cap points plus five off-cap probes.” The 12.8% bound is the $N\le64$
serving-regime bound, not a bound over all 69 points.
