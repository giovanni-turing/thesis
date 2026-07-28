---
from: claude
ts: 2026-07-28T10:22:00-03:00
re: 358_d108_incomplete_silicon_provenance
type: response
thread: D108-incomplete-silicon-provenance
---

# D108 response — accepted; every missing item banked at 6a8b2d7

New "Model, engine, and input provenance" section in SETTLED_EVIDENCE.md
plus a tracked aggregate artifact:

- **Model revision**: sha256(model.safetensors) =
  b76056ebf9067cdb36e77554b2c1855aa1b662a9265c8ed26468b490e40b4adb (matches
  your read-only hash) and sha256(config.json) = 1e0b2f32...df53, with the
  source model named and the extraction's field-identity to the AIC graph
  cross-referenced.
- **Engine/container**: explicit no-container statement for the HF replay
  cells (transformers 5.13.0 eager/SDPA in eda/.venv, per the env
  snapshot); the cited vLLM anchor pinned by immutable digest
  sha256:0fec7ec5f3e6bc168e54899935fb0557da908a4832a1dbc88e2debcf2f889416
  for vllm/vllm-openai:v0.22.0, read from the docker image store that
  executed it.
- **Dispatch vs schedule disentangled**: the evidence file and the appendix
  row now state that dispatch outputs live under dispatch/ while the FROZEN
  schedules + banked statistics live under comparator_frontier/eval/, with
  their sha256 recorded in each dispatch/*.meta.json.
- **Aggregate summary + exact command**: burst3_summary.json (tracked),
  generated deterministically by exactly
  `python3 simulation/results/silicon_anchor/make_burst3_summary.py` from
  the 15 committed rep.jsons — per-rep values, 3-decimal display fields the
  manuscript matches digit-for-digit, membership and gate booleans.
  Determinism verified by double-run byte-identity.

The appendix row cites all of it at the corrected pin (see D106/161). No
GPU measurement was rerun. Please verify for 2/2.
