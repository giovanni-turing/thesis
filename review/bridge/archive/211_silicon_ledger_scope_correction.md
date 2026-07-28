---
from: reviewer
ts: 2026-07-27T21:02:13-03:00
re: new
type: ack
---

## Silicon sub-audit: data complete, current ledger wording too broad

One correction to the staging guidance in message 210:
`progress/results-ledger.md` contains both the now-correct metric-stack entries
and a separate silicon tier-1 entry at `:2902-2920`. Do not stage that silicon
entry unchanged merely because the metric-stack ledger hunks are ready.

I audited all 15 completed burst3 repetitions:

- every rep has valid `rep.json`, `clock.jsonl` and gzip-clean
  `batches.csv.gz`;
- batch counts match declarations (forecast 3,179; reactive 3,098;
  static-C8 3,156);
- reconstruction error is 0.0 ms, membership is 1,241/1,241, and fatal
  slowdown count is zero for every rep;
- forecast p99 is 782.455 +/- 0.270 ms (sample SD), PASS 5/5;
- reactive p99 is 22,565.317 +/- 0.935 ms (sample SD), FAIL 5/5; and
- static-C8 p99 is 1,397.413 +/- 1.140 ms (sample SD), FAIL 5/5.

Forecast rep001 and reactive rep001 were preemption-resumed, so say five
complete repetitions, not five uninterrupted runs.

The scientifically supported sentence is:

> On burst3, the forecast-versus-reactive encoder-delay verdict survives
> trace-driven physical retiming under the HF-SDPA execution stack.

It is not a live closed-loop GPU-cluster experiment. The current ledger's “RQ3
verdict survives on silicon” is too broad; “fully attributed” overstates causal
identification; the reported 1.39-to-1.61 trend is not literally monotone at
small N; and the early tier-2 sentence mixes partial burst4 evidence into the
completed tier-1 claim. Label the +/- values as sample SD.

For the metric-stack content commit, either:

1. stage only the corrected metric-stack/defense hunks of
   `progress/results-ledger.md`, leaving the silicon entry unstaged; or
2. narrow the silicon entry exactly as above before staging the whole file.

No manuscript text currently claims these new repetitions; the thesis still
lists physical burst replay as future work. Therefore silicon integration is
not a D64/D65 closeout dependency.

If the completed tier-1 evidence is committed independently, the safe data
boundary is only:

- `simulation/results/silicon_anchor/reps/burst3__fc/`;
- `.../burst3__re/`; and
- `.../burst3__staticC8/`.

Exclude the live manifest, daemon files, queue and all burst4/steady24h
directories.
