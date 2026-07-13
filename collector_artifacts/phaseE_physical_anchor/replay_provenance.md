# Queue-replay provenance (encoder cost repriced at the measured vLLM f(N))

Four week-scale two-pool replays validate that the 0.62x economic headline
holds when the encoder is priced at the directly-measured vLLM forward cost
instead of the AIC composition. The harness `tier2_vllm_replay.py`
monkeypatches `EncoderCostModel.latency_ms` to scale AIC by the measured
vLLM/AIC ratio (interpolated per dispatched batch from `vllm_eager_dense.json`);
`VLLM_RATIO=0` disables the patch (pure AIC control), `VLLM_RATIO=1` applies it.

- AIC/aiconfigurator commit: b55dd0b7096f3f98db4b495380d95e5b6be95dc8
- vLLM cost curve: collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.json (69 batch sizes)
- worker schedule (winning policy): simulation/results/aggregate44/fc_p90_L30_issuetime.sched.json
- run from the workspace root (/home/gio/tese)

| run (stats file) | p99 encoder_delay (ms) | divergent | queue@arrival-end | provisioned worker-s |
|---|---|---|---|---|
| winsched_ctrl_aic (forecast p90/rho15 schedule, AIC) | 589.301 | false | 0 | 2410754.7 |
| winsched_treatment_vllm (same schedule, measured vLLM) | 605.612 | false | 0 | 2410754.7 |
| static_c8_ctrl_aic (static C=8 denominator, AIC) | 646.943 | false | 0 | 3869278.8 |
| static_c8_treatment_vllm (static C=8, measured vLLM) | 692.008 | false | 0 | 3869278.8 |

## Exact commands

```bash
AIC=ai-dynamo/aiconfigurator/.venv/bin/python
H=collector_artifacts/phaseE_physical_anchor/tier2_vllm_replay.py
SCHED=simulation/results/aggregate44/fc_p90_L30_issuetime.sched.json
PE=collector_artifacts/phaseE_physical_anchor

# 1. winning schedule, AIC control
VLLM_RATIO=0 $AIC $H --offset 250399 --max-requests 749601 --encoder-workers 2 \
  --worker-schedule $SCHED --out $PE/winsched_ctrl_aic.jsonl --stats $PE/winsched_ctrl_aic.stats.json

# 2. winning schedule, measured-vLLM repricing
VLLM_RATIO=1 $AIC $H --offset 250399 --max-requests 749601 --encoder-workers 2 \
  --worker-schedule $SCHED --out $PE/winsched_treatment_vllm.jsonl --stats $PE/winsched_treatment_vllm.stats.json

# 3. static C=8 denominator, AIC control (constant 8 workers, no schedule)
VLLM_RATIO=0 $AIC $H --offset 250399 --max-requests 749601 --encoder-workers 8 \
  --out $PE/static_c8_ctrl_aic.jsonl --stats $PE/static_c8_ctrl_aic.stats.json

# 4. static C=8 denominator, measured-vLLM repricing
VLLM_RATIO=1 $AIC $H --offset 250399 --max-requests 749601 --encoder-workers 8 \
  --out $PE/static_c8_treatment_vllm.jsonl --stats $PE/static_c8_treatment_vllm.stats.json
```

Reading: repricing the encoder at the measured vLLM cost moves the winning
schedule's p99 encoder-delay 589 -> 606 ms and the static C=8 denominator
647 -> 692 ms, both non-divergent and far under the 1000 ms SLA, with the
provisioned worker-seconds (the cost-ratio numerator and denominator)
unchanged. The 0.62x headline therefore holds on the measured standalone
vLLM vision-tower forward cost, not only the AIC model. (This reprices the
encoder forward compute; it is not a full-serving-path measurement.)
