#!/bin/bash
# Two-pool minimal test: encoder pool (rtx_5090, AIC silicon) -> LLM pool (dynamo.replay offline).
# Stage 1 runs in the aiconfigurator uv env; stage 2 needs a python env with `ai-dynamo`
# (set DYNAMO_PYTHON to its interpreter; default: the scratch venv provisioned next to this script).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
AIC=/home/gio/tese/ai-dynamo/aiconfigurator
TRACE=${TRACE:-/tmp/two_pool_trace.jsonl}
DYNAMO_PYTHON=${DYNAMO_PYTHON:-$HERE/dynamo-venv/bin/python}

echo "=== stage 1: encoder pool sim (aiconfigurator env) ==="
cd "$AIC"
uv run --frozen python "$HERE/encoder_pool_sim.py" --out "$TRACE" "$@"

echo
echo "=== stage 2: LLM pool sim (dynamo.replay offline) ==="
"$DYNAMO_PYTHON" -m dynamo.replay "$TRACE" \
    --trace-format mooncake \
    --trace-block-size 512 \
    --replay-mode offline \
    --router-mode kv_router \
    --num-workers 2 \
    --extra-engine-args '{"block_size":64}' \
    --report-json "$HERE/two_pool_report.json"

echo
echo "report: $HERE/two_pool_report.json"
