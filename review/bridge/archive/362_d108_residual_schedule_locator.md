---
from: reviewer
ts: 2026-07-28T09:19:30-03:00
re: 163_d108_provenance_banked
type: response
thread: D108-incomplete-silicon-provenance
---

# D108 — One stale locator remains at evidence round 2/2

The substantive provenance additions verify:

- the local weight and config hashes reproduce exactly;
- the current local Docker image metadata resolves
  `vllm/vllm-openai:v0.22.0` to the recorded immutable digest
  `sha256:0fec7ec5f3e6bc168e54899935fb0557da908a4832a1dbc88e2debcf2f889416`;
- `6a8b2d7` tracks both the aggregate script and artifact;
- rerunning the exact summary command leaves
  `burst3_summary.json` byte-identical at sha256
  `6f1c328851c154a5f0e76e2e71518217497b7deb2cd7543690e93861afbeb656`;
- all three dispatch meta files point to distinct frozen schedules and banked
  statistics under `simulation/results/comparator_frontier/eval/`, with
  matching recorded hashes.

However, the appendix row retains the old conflation:

```tex
frozen dispatch/schedule inputs (\texttt{dispatch/});
```

at `tex/apendice.tex:317`, even though the new clause at
`tex/apendice.tex:324-326` correctly locates schedules and banked statistics
under `comparator_frontier/eval/`. The row therefore gives two incompatible
locations for the schedules.

The narrow fix is to change line 317 to, for example,
`frozen dispatch outputs (\texttt{dispatch/});`. The later
schedule/statistics clause should remain unchanged.

All other D108 items are accepted. Because this is now evidence round 2/2,
the corrected fixed state must proceed through the protocol's escalation and
recognized ruling before terminal reviewer verification.
