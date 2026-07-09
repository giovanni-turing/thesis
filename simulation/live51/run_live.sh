#!/usr/bin/env bash
# Phase 5.1 live validation anchor — one policy run on the live Dynamo stack.
#
#   bash run_live.sh <fc|re> <trace.jsonl> <rundir> [SPAWN_DELAY] [INITIAL]
#
# Prereqs (already running): etcd :2379, NATS :4222 (dev/docker-compose.yml),
# Prometheus :9090 scraping localhost:8000/metrics (prom51 container).
#
# Topology per run (fresh namespace per policy to avoid stale etcd state):
#   frontend (:8000, in-process KV router)
#   worker_manager (VirtualConnector consumer; 1 process = 1 TP2 mocker replica)
#   planner (live SLA planner; fc = forecast_file predictor, re = variant-B reactive)
#   aiperf (fixed-schedule mooncake replay -> client-side TTFT/ITL)
set -euo pipefail

POLICY=${1:?fc|re}
TRACE=${2:?trace jsonl (relative-ms timestamps)}
RUNDIR=${3:?output dir}
SPAWN_DELAY=${4:-57}      # cold-start lead 60s minus measured spawn-to-ready
INITIAL=${5:-2}           # initial replicas (matches offline twin CLI N)

HERE=$(cd "$(dirname "$0")" && pwd)
DYN=/home/gio/tese/ai-dynamo/dynamo
PY=$DYN/.venv/bin/python
AIPERF=/home/gio/tese/ai-dynamo/aiperf/.venv/bin/aiperf
MODEL_DIR=/home/gio/tese/models/Qwen3-VL-8B
MODEL_NAME=Qwen/Qwen3-VL-8B-Instruct

case "$POLICY" in
  fc) NS=a51fc; PLANNER_CFG=$HERE/planner_fc_live.json
      export REGISTER_FORECAST=1
      PLANNER_CMD=("$PY" "$HERE/planner_live.py") ;;
  re) NS=a51re; PLANNER_CFG=$HERE/planner_re_live.json
      export REGISTER_FORECAST=0
      PLANNER_CMD=("$PY" "$HERE/planner_live.py") ;;
  *) echo "policy must be fc|re" >&2; exit 2 ;;
esac
# In-tree fix verification: override the planner config (e.g. a copy with
# fpm_observation_mode:"all") and set SKIP_PARITY_PATCH=1 to bypass the
# harness monkeypatch so the committed code path runs alone.
PLANNER_CFG=${PLANNER_CFG_OVERRIDE:-$PLANNER_CFG}

mkdir -p "$RUNDIR"
export ETCD_ENDPOINTS=http://localhost:2379
export NATS_SERVER=nats://localhost:4222
export DYN_DISCOVERY_BACKEND=etcd
export PROMETHEUS_ENDPOINT=http://localhost:9090
export HF_HUB_OFFLINE=1
export RUST_LOG=${RUST_LOG:-warn}

# Forecast predictor env (fc only; harmless otherwise)
export FORECAST_DIR=/home/gio/tese/predictors/results
export FORECAST_MODEL=${FORECAST_MODEL:-chronos}
export FORECAST_QUANTILE=${FORECAST_QUANTILE:-p50}
export FORECAST_RESOLUTION=${FORECAST_RESOLUTION:-15s}
export FORECAST_T0=${FORECAST_T0:?set window start, e.g. "2024-10-18 10:18:00"}
export FORECAST_REQ_SCALE=${FORECAST_REQ_SCALE:-8.0}

# Stamp this run's namespace onto the frontend scrape as dynamo_namespace —
# the planner's traffic filter requires it (k8s gets it from relabeling).
cat > "$HERE/prometheus.yml" <<EOF
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: 'dynamo-frontend'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          dynamo_namespace: '$NS'
EOF
docker restart prom51 >/dev/null
for i in $(seq 1 30); do
  curl -sf localhost:9090/-/ready >/dev/null && break; sleep 1
done

PIDS=()
cleanup() {
  set +e
  for pid in "${PIDS[@]}"; do kill -TERM "$pid" 2>/dev/null; done
  sleep 3
  for pid in "${PIDS[@]}"; do kill -KILL "$pid" 2>/dev/null; done
  pkill -f "dynamo.mocker.*--namespace $NS" 2>/dev/null
}
trap cleanup EXIT

echo "== frontend (ns=$NS)"
$PY -m dynamo.frontend --namespace "$NS" --router-mode kv \
    --http-port 8000 --kv-cache-block-size 64 \
    >"$RUNDIR/frontend.log" 2>&1 &
PIDS+=($!)

echo "== worker manager (initial=$INITIAL, spawn_delay=${SPAWN_DELAY}s)"
$PY "$HERE/worker_manager.py" --namespace "$NS" \
    --model-path "$MODEL_DIR" --model-name "$MODEL_NAME" \
    --engine-args "$HERE/engine_args.json" \
    --initial-workers "$INITIAL" --min-workers 1 \
    --spawn-delay "$SPAWN_DELAY" \
    --log "$RUNDIR/manager.jsonl" --rundir "$RUNDIR" \
    >"$RUNDIR/manager.log" 2>&1 &
PIDS+=($!)

echo "== waiting for model registration"
for i in $(seq 1 60); do
  if curl -sf localhost:8000/v1/models | grep -q "$MODEL_NAME"; then
    echo "   model ready after ${i}s"; break
  fi
  [ "$i" = 60 ] && { echo "model never registered" >&2; exit 1; }
  sleep 1
done

echo "== planner ($POLICY)"
"${PLANNER_CMD[@]}" --config "$PLANNER_CFG" \
    >"$RUNDIR/planner.log" 2>&1 &
PIDS+=($!)
sleep 5

echo "== aiperf fixed-schedule replay: $TRACE"
"$AIPERF" profile \
  --model "$MODEL_NAME" --tokenizer "$MODEL_NAME" \
  --endpoint-type completions --streaming \
  --url localhost:8000 \
  --input-file "$TRACE" \
  --custom-dataset-type mooncake_trace \
  --fixed-schedule --fixed-schedule-auto-offset \
  --output-artifact-dir "$RUNDIR/aiperf" \
  >"$RUNDIR/aiperf.log" 2>&1

echo "== done; artifacts in $RUNDIR"
