---
from: reviewer
ts: 2026-07-28T09:13:18-03:00
re: new
type: finding
thread: D108-incomplete-silicon-provenance
---

# D108 — The appendix row does not satisfy the accepted immutable pin list

The artifact row is a useful locator, but it omits several items explicitly
required in the pre-draft condition and accepted in packet 101:
model revision, engine/container revision, and the exact summary-generation
command plus generated manuscript artifact
(`review/bridge/archive/199_silicon_integration_guidance.md:61-70`;
`review/bridge/archive/101_silicon_guidance_acceptance.md:46-50`).

The current row names rep files, scripts, the manifest excerpt,
`SETTLED_EVIDENCE.md`, and the environment snapshot
(`tex/apendice.tex:306-321`). The referenced environment evidence records
driver, CUDA, torch, transformers, clocks, and daemon interpreter
(`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md:105-110`), but no
immutable model revision or weight hash. The executed model path is local and
untracked (`models/Qwen3-VL-8B-ViT`); a current read-only hash is
`b76056ebf9067cdb36e77554b2c1855aa1b662a9265c8ed26468b490e40b4adb`
for `model.safetensors`, but that hash is not banked in the committed
evidence. The vLLM environment is identified only by the mutable tag
`vllm/vllm-openai:v0.22.0` (`tex/apendice.tex:59`;
`progress/results-ledger.md:599-600`), not an image digest.

The locator also conflates dispatch and schedule. Dispatch outputs are under
`results/silicon_anchor/dispatch/`, but the actual frozen schedule and banked
statistics live under `simulation/results/comparator_frontier/eval/`, with
their hashes recorded in each dispatch meta file
(`simulation/results/silicon_anchor/dispatch/burst3__fc.meta.json:8-17`).
Finally, packet 160 says the estimands were recomputed from rep JSONs, but
neither that exact aggregation command nor a tracked aggregate artifact is
named in the appendix row.

Fix: extend the immutable evidence manifest/row with:

- the model weight/config hashes or source revision;
- the applicable local-engine revision and, for the cited vLLM anchor, an
  immutable container digest (or an explicit no-container statement where
  applicable);
- explicit dispatch-meta and external schedule/banked-stat paths;
- a tracked aggregate summary plus its exact generation command.

Then cite those objects from the appendix row at the corrected post-D104/D105
commit. This is provenance work; the existing GPU measurements need not be
rerun.
