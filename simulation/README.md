# simulation/ — two-pool DynoSim runs

Phase 2+ simulation workspace. The Phase-1 converter that produces the traces
lives in `../workload/trace_to_two_pool.py`; results and analysis land here.

## Layout
- `run_replay.sh <trace> <poly|aic> <report> [workers]` — parameterized
  dynamo.replay driver (offline, kv_router). `poly` = mocker default polynomial
  timing; `aic` = h100_sxm/vLLM 0.22.0 calibrated engine timing.
- `traces/` — generated mooncake JSONL (+ `.stats.json` cross-linking to the EDA).
- `results/` — AIPerf report JSONs.
- `sweep_load.py` + `sweep_fig.py` — Phase 2.3 arrival-speedup saturation-knee
  sweeps (per-pool load-vs-latency curves + knees); results and rollup in
  `results/sweeps/` (see its README.md).

## Environment
Runs from the aiconfigurator uv `.venv`, which now also carries
`ai-dynamo==1.2.1` (see `../progress/phase2-simulation.md` for why one env holds
both). If the env is ever `uv sync`'d back to the lockfile, re-add:
`cd ../ai-dynamo/aiconfigurator && uv pip install ai-dynamo==1.2.1`.

## Reproduce the current results
```bash
cd ../ai-dynamo/aiconfigurator
# two-pool (encoder handoff folded into arrivals)
.venv/bin/python ../../workload/trace_to_two_pool.py \
    --out ../../simulation/traces/azure_two_pool_2k.jsonl --max-requests 2000
# LLM-pool isolation (raw arrivals)
.venv/bin/python ../../workload/trace_to_two_pool.py \
    --out ../../simulation/traces/azure_llm_only_2k.jsonl --max-requests 2000 --no-encoder-shift
cd ../../simulation
./run_replay.sh traces/azure_llm_only_2k.jsonl poly results/llm_only_poly.json
./run_replay.sh traces/azure_llm_only_2k.jsonl aic  results/llm_only_aic.json
```

Findings so far: `../progress/phase2-simulation.md`.
