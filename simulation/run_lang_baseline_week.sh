#!/bin/bash
# Fresh week-scale symmetric baselines under langcalib: reactive (200/20) + static TP2x2
# on the aggregate composed trace (749,601 req / 5.60 d) -- the SAME trace the forecast week
# arms used. CPU-only (dynamo.replay is a deterministic DES; no GPU in this loop). Both in
# parallel.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/baseline_week
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TRACE=/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl
cat > "$OUT/cfg_react.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"bw_react","backend":"vllm",
 "optimization_target":"sla","ttft_ms":200.0,"itl_ms":20.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,"load_predictor":"arima",
 "throughput_adjustment_interval_seconds":60,"load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF
( RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TRACE" aic "$OUT/react_aggregate_t200_20.report.json" 2 \
      --planner-config "$OUT/cfg_react.json" > "$OUT/react.log" 2>&1 \
    && echo "done react" || echo "FAIL react" ) &
( RUST_LOG=warn AIC_TP=2 STARTUP_TIME=0 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TRACE" aic "$OUT/static_aggregate_tp2x2.report.json" 2 \
      > "$OUT/static.log" 2>&1 && echo "done static" || echo "FAIL static" ) &
wait
echo "=== week baselines (reactive 200/20 + static TP2x2 on aggregate) complete ==="
