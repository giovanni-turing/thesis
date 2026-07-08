#!/bin/bash
# Phase 3.2: LLM reactive baseline — Dynamo planner-in-the-loop on all 7
# windows x 2 variants (local; planner needs the source venv, not the fleet).
#   A shipped-default: optimization_target=throughput => Easy mode forces
#     load-scaling-only, native 500/50 ms window-mean control law.
#   B full planner:    optimization_target=sla, both loops, ARIMA predictor.
# Bursts run the binding TP2 shape (TP1 is prefill-floor-infeasible — shape,
# not control); steady24h runs TP1. Traces = composed (C*-shifted) grid traces.
set -u
OUT=/home/gio/tese/simulation/results/reactive32
mkdir -p "$OUT"
declare -A TRC=( [burst1]=grid_burst1_C6 [burst2]=grid_burst2_C8 [burst3]=grid_burst3_C7 \
                 [burst4]=grid_burst4_C7 [burst5]=grid_burst5_C16 [burst6]=grid_burst6_C6 \
                 [steady24h]=grid_steady24h_C2 )
declare -A TP=( [burst1]=2 [burst2]=2 [burst3]=2 [burst4]=2 [burst5]=2 [burst6]=2 [steady24h]=1 )

cat > "$OUT/planner_A.json" <<'EOF'
{"mode":"agg","environment":"virtual","namespace":"r32a","backend":"vllm",
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1,
 "load_adjustment_interval_seconds":60}
EOF
cat > "$OUT/planner_B.json" <<'EOF'
{"mode":"agg","environment":"virtual","namespace":"r32b","backend":"vllm",
 "optimization_target":"sla","ttft_ms":500.0,"itl_ms":50.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,
 "load_predictor":"arima","throughput_adjustment_interval_seconds":60,
 "load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF

for w in burst1 burst2 burst3 burst4 burst5 burst6 steady24h; do
  for v in A B; do
    tag="r32${v}_${w}"
    [ -f "$OUT/$tag.report.json" ] && { echo "skip $tag"; continue; }
    (
      RUST_LOG=warn AIC_TP="${TP[$w]}" REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python AIC_VER=0.19.0 \
      bash /home/gio/tese/simulation/run_replay.sh \
        "/home/gio/tese/simulation/results/grid/traces/${TRC[$w]}.jsonl" aic \
        "$OUT/$tag.report.json" 2 \
        --planner-config "$OUT/planner_${v}.json" \
        > "$OUT/$tag.log" 2>&1 \
      && echo "done $tag" || echo "FAIL $tag"
    ) &
    while [ "$(jobs -r | wc -l)" -ge 14 ]; do wait -n; done
  done
done
wait
echo "3.2 reactive runs complete"
