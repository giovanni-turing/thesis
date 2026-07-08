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
# REPLAY_PY selects the interpreter/runtime: default = pinned ai-dynamo==1.2.1
# wheel in the aiconfigurator venv (Phase 2 reproducibility); the dynamo 1.3.0
# source build lives in /home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
# (aiconfigurator co-installed editable — see progress docs, source-build note).
PY="${REPLAY_PY:-$AIC/.venv/bin/python}"

TRACE=${1:?trace jsonl}
MODEL=${2:?poly|aic}
REPORT=${3:?report json path}
WORKERS=${4:-2}
shift $(( $# < 4 ? $# : 4 ))

# Language-pool model config (locked decoder pool: h100_sxm + vLLM 0.22.0, Qwen3-VL).
# Env overrides (defaults = the 8B/TP1 baseline): AIC_MODEL, AIC_TP, and for MoE
# family members AIC_MOE_TP / AIC_MOE_EP (e.g. 235B-A22B at TP8: AIC_TP=8 AIC_MOE_TP=8).
AIC_MODEL=${AIC_MODEL:-Qwen/Qwen3-VL-8B-Instruct}
AIC_TP=${AIC_TP:-1}
# AIC_VER: perf-DB version. 0.22.0 is a shared-layer-reuse marker the PYTHON
# SDK resolves to 0.19.0 (verified identical predictions); the source build's
# Rust AIC path reads parquet directly and needs the resolved version.
AIC_VER=${AIC_VER:-0.22.0}
AIC_MOE_JSON=""
[ -n "${AIC_MOE_TP:-}" ] && AIC_MOE_JSON=',"aic_moe_tp_size":'"$AIC_MOE_TP"
[ -n "${AIC_MOE_EP:-}" ] && AIC_MOE_JSON="$AIC_MOE_JSON"',"aic_moe_ep_size":'"$AIC_MOE_EP"
case "$MODEL" in
  poly) ENGINE_ARGS='{"block_size":64}' ;;                              # mocker default polynomial timing
  aic)  ENGINE_ARGS='{"aic_backend":"vllm","aic_system":"h100_sxm","aic_model_path":"'"$AIC_MODEL"'","aic_tp_size":'"$AIC_TP$AIC_MOE_JSON"',"aic_backend_version":"'"$AIC_VER"'","block_size":64}' ;;
  *) echo "model must be poly|aic" >&2; exit 2 ;;
esac

# Offline replay only supports kv_router with >1 workers; with a single
# worker routing is trivial, so round_robin is behavior-identical there.
ROUTER=kv_router
[ "$WORKERS" -le 1 ] && ROUTER=round_robin

cd "$AIC"
# REPLAY_ENTRY: optional script path replacing `-m dynamo.replay` (e.g. the
# forecast_file predictor wrapper simulation/replay_with_forecast.py).
if [ -n "${REPLAY_ENTRY:-}" ]; then
  exec "$PY" "$REPLAY_ENTRY" "$TRACE" \
  --trace-format mooncake --trace-block-size 512 \
  --replay-mode offline --router-mode "$ROUTER" \
  --num-workers "$WORKERS" \
  --extra-engine-args "$ENGINE_ARGS" \
  --report-json "$REPORT" "$@"
fi
exec "$PY" -m dynamo.replay "$TRACE" \
  --trace-format mooncake --trace-block-size 512 \
  --replay-mode offline --router-mode "$ROUTER" \
  --num-workers "$WORKERS" \
  --extra-engine-args "$ENGINE_ARGS" \
  --report-json "$REPORT" "$@"
