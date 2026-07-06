#!/bin/bash
# DynoSim LLM-pool replay driver — parameterized over trace and timing model.
#
# The combined env (aiconfigurator SDK + ai-dynamo wheel in one interpreter) is
# the aiconfigurator uv .venv, into which `ai-dynamo==1.2.1` was added
# (cp310-abi3 wheel, loads on the env's 3.13). This co-residence is what lets
# dynamo.replay's `dynamo._internal.aic.create_session` import the SDK and query
# h100_sxm/vllm/0.22.0 silicon for per-request prefill/decode timing.
#
# Usage:
#   run_replay.sh <trace.jsonl> <poly|aic> <report.json> [num_workers] [extra replay args...]
set -euo pipefail
AIC=/home/gio/tese/ai-dynamo/aiconfigurator
PY="$AIC/.venv/bin/python"

TRACE=${1:?trace jsonl}
MODEL=${2:?poly|aic}
REPORT=${3:?report json path}
WORKERS=${4:-2}
shift $(( $# < 4 ? $# : 4 ))

# Language-pool model config (locked decoder pool: h100_sxm + vLLM 0.22.0, Qwen3-VL).
AIC_MODEL=Qwen/Qwen3-VL-8B-Instruct
case "$MODEL" in
  poly) ENGINE_ARGS='{"block_size":64}' ;;                              # mocker default polynomial timing
  aic)  ENGINE_ARGS='{"aic_backend":"vllm","aic_system":"h100_sxm","aic_model_path":"'"$AIC_MODEL"'","aic_tp_size":1,"aic_backend_version":"0.22.0","block_size":64}' ;;
  *) echo "model must be poly|aic" >&2; exit 2 ;;
esac

cd "$AIC"
exec "$PY" -m dynamo.replay "$TRACE" \
  --trace-format mooncake --trace-block-size 512 \
  --replay-mode offline --router-mode kv_router \
  --num-workers "$WORKERS" \
  --extra-engine-args "$ENGINE_ARGS" \
  --report-json "$REPORT" "$@"
